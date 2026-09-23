#!/usr/bin/env python3
"""Isolated A/B runner. Saves every attempt, including harness errors.

skillforge: reference routing + inline rules
sf-modules: reference routing + full modules / rule pointers (delivery ablation)
sf-keywords: keyword routing + inline rules (routing ablation)
none/native: no skills / the same eligible modules installed as ordinary skills

This is process/config isolation, not a hostile-agent security sandbox. --keep
retains project output and transcripts, never copied credential directories.
"""
import argparse
import hashlib
import json
import os
import random
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = ROOT / 'plugin/library/modules'
CREDS = Path.home() / '.claude/.credentials.json'
SCORE = re.compile(r'SCORE:\s*(\d+)\s*/\s*(\d+)')
ARMS = {'none': None, 'native': None, 'skillforge': ('rules', 'references'),
        'sf-modules': ('modules', 'references'), 'sf-keywords': ('rules', 'keywords')}


def digest_tree(root):
    h = hashlib.sha256()
    for p in sorted(root.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            h.update(p.relative_to(root).as_posix().encode() + b'\0' + p.read_bytes() + b'\0')
    return h.hexdigest()


def native_plugin(support):
    root = support / 'native-plugin'
    (root / '.claude-plugin').mkdir(parents=True)
    (root / '.claude-plugin/plugin.json').write_text(json.dumps(
        {'name': 'native-skills', 'version': '0.1.0', 'description': 'Eligible library modules as skills.'}), encoding='utf-8')
    index = json.loads((ROOT / 'plugin/library/index.json').read_text(encoding='utf-8'))
    for m in index['modules']:
        if m['kind'] != 'module' or m['status'] not in ('provisional', 'preferred'):
            continue
        source = ROOT / 'plugin/library' / m['path']
        out = root / 'skills' / m['name']
        shutil.copytree(source.parent, out)
        (out / source.name).rename(out / 'SKILL.md')
    return root


def setup(arm, task_dir, dest, support):
    if arm not in ARMS:
        raise ValueError(f'unknown arm: {arm}')
    for f in task_dir.iterdir():
        if f.name in ('test.py', '__pycache__'):
            continue
        if f.is_dir(): shutil.copytree(f, dest / f.name)
        else: shutil.copy2(f, dest)
    if arm == 'native': return ['--plugin-dir', str(native_plugin(support))]
    if ARMS[arm]: return ['--plugin-dir', str(ROOT / 'plugin')]
    return []


def activation_events(stdout):
    """Count only actual tool calls and their successful tool results, not prose."""
    calls = {}
    delivered = set()
    result = None
    for line in stdout.splitlines():
        try: event = json.loads(line)
        except json.JSONDecodeError: continue
        if event.get('type') == 'result': result = event
        content = event.get('message', {}).get('content', [])
        if not isinstance(content, list): continue
        for block in content:
            if not isinstance(block, dict): continue
            if block.get('type') == 'tool_use': calls[block.get('id')] = block
            if block.get('type') != 'tool_result' or block.get('is_error'): continue
            call = calls.get(block.get('tool_use_id'), {})
            command = call.get('input', {}).get('command', '')
            if call.get('name') != 'Bash' or 'compose.py' not in command: continue
            value = block.get('content', '')
            text = value if isinstance(value, str) else '\n'.join(
                b.get('text', '') for b in value if isinstance(b, dict))
            if re.search(r'^# SkillForge brief:', text, re.M):
                delivered.add(block.get('tool_use_id'))
    activated = any(c.get('name') == 'Skill' or
                    (c.get('name') == 'Bash' and 'compose.py' in c.get('input', {}).get('command', ''))
                    for c in calls.values())
    return activated, bool(delivered), result


def run_one(arm, task_dir, task, tools, timeout, dry, keep, model=None):
    dest = Path(tempfile.mkdtemp(prefix=f'sf-{arm}-'))
    support = Path(tempfile.mkdtemp(prefix=f'sfsup-{arm}-'))
    started = time.monotonic()
    row = dict(arm=arm, status='harness_error', error=None, score=None, passed=None,
               cost=None, turns=None, input_tokens=None, output_tokens=None,
               cache_read=None, cache_write=None, activated=False, brief=False,
               dir=str(dest) if keep else None)
    try:
        extra = setup(arm, task_dir, dest, support)
        cfg = support / 'cfg'; cfg.mkdir()
        if CREDS.exists(): shutil.copy2(CREDS, cfg)
        tmp = support / 'tmp'; tmp.mkdir()
        env = {**os.environ, 'CLAUDE_CONFIG_DIR': str(cfg), 'TMPDIR': str(tmp),
               'TEMP': str(tmp), 'TMP': str(tmp), 'SKILLFORGE_LOG': str(dest / 'compose.jsonl')}
        # Parent experiment switches must not contaminate the assigned arm.
        env.pop('SKILLFORGE_DELIVERY', None); env.pop('SKILLFORGE_ROUTING', None)
        if ARMS[arm]: env['SKILLFORGE_DELIVERY'], env['SKILLFORGE_ROUTING'] = ARMS[arm]
        cmd = ['claude', '-p', task, '--output-format', 'stream-json', '--verbose',
               '--tools', tools, '--allowedTools', tools, *extra]
        if model: cmd += ['--model', model]
        if dry:
            print(f'[{arm}] isolated config; model={model}; settings={ARMS[arm]}; fixture={task_dir.name}')
            return None
        proc = subprocess.run(cmd, cwd=dest, capture_output=True, text=True,
                              encoding='utf-8', timeout=timeout, env=env)
        (dest / 'transcript.jsonl').write_text(proc.stdout, encoding='utf-8')
        (dest / 'stderr.txt').write_text(proc.stderr, encoding='utf-8')
        row['activated'], row['brief'], result = activation_events(proc.stdout)
        if result:
            usage = result.get('usage', {})
            row.update(cost=result.get('total_cost_usd'), turns=result.get('num_turns'),
                       input_tokens=usage.get('input_tokens'), output_tokens=usage.get('output_tokens'),
                       cache_read=usage.get('cache_read_input_tokens'),
                       cache_write=usage.get('cache_creation_input_tokens'),
                       model_usage=result.get('modelUsage'))
        if proc.returncode != 0 or not result or result.get('is_error'):
            row['error'] = f'Claude failed or missing result; exit={proc.returncode}'
            return row
        shutil.copy2(task_dir / 'test.py', dest / 'test.py')
        try:
            test = subprocess.run([sys.executable, 'test.py'], cwd=dest, capture_output=True,
                                  text=True, encoding='utf-8', timeout=30)
        except subprocess.TimeoutExpired:
            row.update(status='grader_timeout', passed=False, error='grader timed out; no fabricated score')
            return row
        (dest / 'grade.txt').write_text(test.stdout + test.stderr, encoding='utf-8')
        match = SCORE.search(test.stdout)
        if match:
            n, d = map(int, match.groups())
            if not 0 <= n <= d or d <= 0 or ((n == d) != (test.returncode == 0)):
                row['error'] = 'invalid or inconsistent SCORE'; return row
            row['score'] = f'{n}/{d}'
        elif 'SCORE:' in (task_dir / 'test.py').read_text(encoding='utf-8'):
            row['error'] = 'grader emitted no SCORE'; return row
        elif test.returncode not in (0, 1):
            row['error'] = f'grader crashed; exit={test.returncode}'; return row
        # Some existing tasks use assert-based pass/fail and have no SCORE line.
        row.update(status='ok', passed=test.returncode == 0)
        return row
    except subprocess.TimeoutExpired:
        row['error'] = 'Claude timed out; cost unknown'
        return row
    except (OSError, ValueError) as exc:
        row['error'] = f'{type(exc).__name__}: {exc}'
        return row
    finally:
        row['elapsed_seconds'] = round(time.monotonic() - started, 3)
        shutil.rmtree(support, ignore_errors=True)  # includes credentials even with --keep
        if not keep: shutil.rmtree(dest, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--task', default=str(ROOT / 'benchmarks/tasks/react-waterfall'))
    ap.add_argument('--arms', default='none,native,skillforge')
    ap.add_argument('--repeats', type=int, default=1)
    ap.add_argument('--tools', default='Read,Edit,Write,Bash,Glob,Grep,Skill')
    ap.add_argument('--timeout', type=int, default=900)
    ap.add_argument('--model', help='explicit model ID; required for paid runs')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--output', default='data/ab-results.jsonl')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--keep', action='store_true')
    a = ap.parse_args()
    arms = [s.strip() for s in a.arms.split(',')]
    if not arms or len(set(arms)) != len(arms) or any(arm not in ARMS for arm in arms): ap.error('unknown or duplicate arms')
    if 'Skill' not in a.tools.split(','): ap.error('--tools must include Skill')
    if a.repeats < 1 or a.timeout < 1: ap.error('repeats and timeout must be positive')
    if not a.dry_run and not a.model: ap.error('--model is required to make paid comparisons reproducible')
    task_dir = Path(a.task).resolve()
    task = (task_dir / 'task.txt').read_text(encoding='utf-8').strip()
    metadata = dict(task=str(task_dir), task_sha256=digest_tree(task_dir),
                    scorer_sha256=hashlib.sha256((task_dir / 'test.py').read_bytes()).hexdigest(),
                    plugin_sha256=digest_tree(ROOT / 'plugin'), seed=a.seed,
                    model=a.model, tools=a.tools,
                    runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    rows = []; rng = random.Random(a.seed)
    path = Path(a.output)
    if not a.dry_run: path.parent.mkdir(parents=True, exist_ok=True)
    for repeat in range(a.repeats):
        for arm in rng.sample(arms, len(arms)):
            row = run_one(arm, task_dir, task, a.tools, a.timeout, a.dry_run, a.keep, a.model)
            if row is None: continue
            row.update(metadata, repeat=repeat + 1, settings=ARMS[arm])
            rows.append(row)
            with path.open('a', encoding='utf-8') as f: f.write(json.dumps(row) + '\n')
            print(f"[{arm}] status={row['status']} score={row['score']} cost={row['cost']} brief={row['brief']}")
    for arm in arms:
        group = [r for r in rows if r['arm'] == arm]
        if not group: continue
        valid = [r for r in group if r['status'] == 'ok']
        costs = [r['cost'] for r in group if r['cost'] is not None]
        print(f"{arm}: valid={len(valid)}/{len(group)}, task passes={sum(r['passed'] for r in valid)}/{len(valid)}, "
              f"median known cost={statistics.median(costs) if costs else 'unknown'}, unknown cost={len(group)-len(costs)}")
        if ARMS[arm] and any(not r['brief'] for r in group):
            print('WARNING: missing tool-result brief(s); inspect transcripts. Keep these attempts in the report.')
    if any(r['status'] != 'ok' for r in rows): sys.exit(1)


if __name__ == '__main__': main()
