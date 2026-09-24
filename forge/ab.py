#!/usr/bin/env python3
"""Isolated A/B runner. Saves every attempt, including harness errors.

none:        no skills (the floor)
native:      the same eligible modules installed as ordinary skills
skillforge:  the SkillForge skill only; Claude must choose to call compose.py
sf-modules:  as skillforge, but full modules plus rule paths (delivery ablation)
sf-hook:     a hook injects the brief on every prompt; no invocation needed
sf-catalog:  a hook injects the one-line-per-rule catalog; Claude fetches rules by ID
sf-expert:   the same hook injects rules a developer chose in advance for the task
             (benchmarks/expert/<task>.json): the ceiling for selection

--crowd DIR installs every skill folder in DIR (each with a SKILL.md) into every arm.
Repeat it to combine crowds, e.g. unrelated distractors plus similar, competing skills.
Results are summarized per task: checks within one task are not independent evidence.

Paid runs refuse to start when a comparison would not be interpretable: a task whose
grader needs Postgres but none is available (--allow-static-grader overrides), or an
sf-expert selection nobody has reviewed. --freeze FILE records the task, grader,
guidance inventory, expert lists, model and budget on first use and refuses to run
if any of them has changed since.

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
ARMS = {'none': None, 'native': None,
        'skillforge': {'SKILLFORGE_HOOK': 'off', 'SKILLFORGE_DELIVERY': 'rules'},
        'sf-modules': {'SKILLFORGE_HOOK': 'off', 'SKILLFORGE_DELIVERY': 'modules'},
        'sf-hook': {'SKILLFORGE_HOOK': 'brief', 'SKILLFORGE_DELIVERY': 'rules'},
        'sf-catalog': {'SKILLFORGE_HOOK': 'catalog', 'SKILLFORGE_DELIVERY': 'rules'},
        'sf-expert': {'SKILLFORGE_HOOK': 'fixed', 'SKILLFORGE_DELIVERY': 'rules'}}
SWITCHES = ('SKILLFORGE_HOOK', 'SKILLFORGE_DELIVERY', 'SKILLFORGE_STACK', 'SKILLFORGE_ROUTING',
            'SKILLFORGE_RULES', 'SKILLFORGE_HOOK_BUDGET')
EXPERT = ROOT / 'benchmarks/expert'
HOOK = ROOT / 'plugin/skills/skillforge/scripts/hook.py'


def expert_file(task_dir):
    path = EXPERT / f'{Path(task_dir).name}.json'
    if not path.exists():
        raise ValueError(f'sf-expert needs {path.relative_to(ROOT)}; no expert selection for this task')
    return json.loads(path.read_text(encoding='utf-8'))


def expert_rules(task_dir):
    """The rules a developer selected for this task before seeing any model output."""
    return expert_file(task_dir)['rules']


def expert_reviewed(task_dir):
    review = expert_file(task_dir).get('review') or {}
    return bool(str(review.get('reviewed_by') or '').strip())


def library_digests():
    """sha256 of every rule's text as the library holds it now."""
    sys.path.insert(0, str(ROOT / 'plugin/skills/skillforge/scripts'))
    import hashlib as _h
    from retrieval import load_rules
    index = json.loads((ROOT / 'plugin/library/index.json').read_text(encoding='utf-8'))
    return {r['id']: _h.sha256(r['text'].encode('utf-8')).hexdigest()
            for r in load_rules(index, ROOT / 'plugin/library')}


def delivered_rules(log_text):
    """[(rule id, sha256)] the hook actually put in context, from its own log."""
    out = []
    for line in log_text.splitlines():
        try: entry = json.loads(line)
        except json.JSONDecodeError: continue
        if entry.get('source') != 'hook': continue
        out += [(u['id'], u['sha256']) for u in entry.get('units', [])
                if u.get('result') == 'delivered' and u.get('module') != 'coding-core']
    return out


def check_delivery(delivered, digests, expected=None):
    """Did every delivered rule arrive intact, and (sf-expert) did every intended rule arrive?"""
    corrupt = [i for i, sha in delivered if digests.get(i) != sha]
    missing = [i for i in (expected or []) if i not in {d for d, _ in delivered}]
    if corrupt:
        return f'altered or unknown rule text: {", ".join(corrupt)}'
    if missing:
        return f'intended rules not delivered: {", ".join(missing)}'
    return 'ok'


def grader_version(task_dir):
    m = re.search(r'^GRADER_VERSION\s*=\s*(\d+)', (Path(task_dir) / 'test.py').read_text(encoding='utf-8'), re.M)
    return int(m[1]) if m else None


def needs_postgres(task_dir):
    return 'pgserver' in (Path(task_dir) / 'test.py').read_text(encoding='utf-8')


def postgres_available():
    r = subprocess.run([sys.executable, '-c', 'import pgserver, psycopg'], capture_output=True)
    return r.returncode == 0


def hook_budget():
    if os.environ.get('SKILLFORGE_HOOK_BUDGET'):
        return int(os.environ['SKILLFORGE_HOOK_BUDGET'])
    m = re.search(r'^DEFAULT_BUDGET\s*=\s*(\d+)', HOOK.read_text(encoding='utf-8'), re.M)
    return int(m[1]) if m else None


def manifest(task_dirs, model, tools, crowds):
    """Everything a rerun must hold fixed for its scores to be comparable."""
    return {
        'model': model, 'tools': tools, 'hook_budget_tokens': hook_budget(),
        'guidance_sha256': digest_tree(ROOT / 'plugin'),
        'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'crowd_sha256': [digest_tree(Path(c)) for c in crowds] if crowds else None,
        'tasks': {t.name: {'task_sha256': digest_tree(t), 'grader_version': grader_version(t),
                           'scorer_sha256': hashlib.sha256((t / 'test.py').read_bytes()).hexdigest(),
                           'expert_sha256': hashlib.sha256((EXPERT / f'{t.name}.json').read_bytes()).hexdigest()
                           if (EXPERT / f'{t.name}.json').exists() else None}
                  for t in task_dirs}}


def check_freeze(path, current):
    """Write the manifest on first use; afterwards refuse any change."""
    path = Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(current, indent=2) + '\n', encoding='utf-8')
        return []
    frozen = json.loads(path.read_text(encoding='utf-8'))
    changed = [k for k in sorted(set(frozen) | set(current)) if k != 'tasks' and frozen.get(k) != current.get(k)]
    for name, info in current['tasks'].items():
        if name in frozen.get('tasks', {}) and frozen['tasks'][name] != info:
            changed.append(f'task {name}')
    return changed


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


def crowd_plugin(support, crowds):
    """Extra skills installed alongside every arm, as one plugin outside the project."""
    root = support / 'crowd-plugin'
    (root / '.claude-plugin').mkdir(parents=True)
    (root / '.claude-plugin/plugin.json').write_text(json.dumps(
        {'name': 'crowd', 'version': '0.1.0', 'description': 'Extra skills for the crowded condition.'}), encoding='utf-8')
    for crowd in [crowds] if isinstance(crowds, (str, Path)) else crowds:
        skills = sorted(p.parent for p in Path(crowd).glob('*/SKILL.md'))
        if not skills:
            raise ValueError(f'no */SKILL.md folders in crowd directory: {crowd}')
        for skill in skills:
            if (root / 'skills' / skill.name).exists():
                raise ValueError(f'two crowd skills are both named {skill.name}')
            shutil.copytree(skill, root / 'skills' / skill.name)
    return root


def setup(arm, task_dir, dest, support, crowd=None):
    if arm not in ARMS:
        raise ValueError(f'unknown arm: {arm}')
    for f in task_dir.iterdir():
        if f.name in ('test.py', '__pycache__'):
            continue
        if f.is_dir(): shutil.copytree(f, dest / f.name)
        else: shutil.copy2(f, dest)
    extra = ['--plugin-dir', str(crowd_plugin(support, crowd))] if crowd else []
    if arm == 'native': return extra + ['--plugin-dir', str(native_plugin(support))]
    if ARMS[arm]: return extra + ['--plugin-dir', str(ROOT / 'plugin')]
    return extra


def hook_evidence(log_text):
    """What the SkillForge hook delivered, from its own log (never from model prose)."""
    briefs = catalogs = 0
    for line in log_text.splitlines():
        try: entry = json.loads(line)
        except json.JSONDecodeError: continue
        if entry.get('source') != 'hook': continue
        if any(u.get('result') == 'delivered' and u.get('module') != 'coding-core' for u in entry.get('units', [])):
            briefs += 1
        if entry.get('result') == 'catalog delivered':
            catalogs += 1
    return briefs, catalogs


def rule_fetches(stdout):
    """Bash calls that fetched rules by ID (compose.py --rule)."""
    n = 0
    for line in stdout.splitlines():
        try: event = json.loads(line)
        except json.JSONDecodeError: continue
        content = event.get('message', {}).get('content', [])
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get('type') == 'tool_use' and block.get('name') == 'Bash':
                command = block.get('input', {}).get('command', '')
                n += 'compose.py' in command and '--rule' in command
    return n


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


def run_one(arm, task_dir, task, tools, timeout, dry, keep, model=None, crowd=None):
    dest = Path(tempfile.mkdtemp(prefix=f'sf-{arm}-'))
    support = Path(tempfile.mkdtemp(prefix=f'sfsup-{arm}-'))
    started = time.monotonic()
    row = dict(arm=arm, status='harness_error', error=None, score=None, passed=None,
               cost=None, turns=None, input_tokens=None, output_tokens=None,
               cache_read=None, cache_write=None, activated=False, brief=False,
               hook_briefs=0, catalogs=0, rule_fetches=0, dir=str(dest) if keep else None)
    log = support / 'compose.jsonl'  # outside the project, so the agent under test cannot read it
    try:
        extra = setup(arm, task_dir, dest, support, crowd)
        cfg = support / 'cfg'; cfg.mkdir()
        if CREDS.exists(): shutil.copy2(CREDS, cfg)
        tmp = support / 'tmp'; tmp.mkdir()
        env = {**os.environ, 'CLAUDE_CONFIG_DIR': str(cfg), 'TMPDIR': str(tmp),
               'TEMP': str(tmp), 'TMP': str(tmp), 'SKILLFORGE_LOG': str(log)}
        # Parent experiment switches must not contaminate the assigned arm.
        for name in SWITCHES: env.pop(name, None)
        env.update(ARMS[arm] or {})
        if arm == 'sf-expert': env['SKILLFORGE_RULES'] = ','.join(expert_rules(task_dir))
        cmd = ['claude', '-p', task, '--output-format', 'stream-json', '--verbose',
               '--tools', tools, '--allowedTools', tools, *extra]
        if model: cmd += ['--model', model]
        if dry:
            print(f'[{arm}] isolated config; model={model}; settings={ARMS[arm]}; fixture={task_dir.name}; '
                  f'plugins={len(extra) // 2}')
            return None
        proc = subprocess.run(cmd, cwd=dest, capture_output=True, text=True,
                              encoding='utf-8', timeout=timeout, env=env)
        (dest / 'transcript.jsonl').write_text(proc.stdout, encoding='utf-8')
        (dest / 'stderr.txt').write_text(proc.stderr, encoding='utf-8')
        row['activated'], row['brief'], result = activation_events(proc.stdout)
        log_text = log.read_text(encoding='utf-8') if log.exists() else ''
        row['hook_briefs'], row['catalogs'] = hook_evidence(log_text)
        row['rule_fetches'] = rule_fetches(proc.stdout)
        row['brief'] = row['brief'] or bool(row['hook_briefs'] or row['catalogs'])
        delivered = delivered_rules(log_text)
        row['delivered_rules'] = [i for i, _ in delivered]
        if ARMS[arm] and ARMS[arm]['SKILLFORGE_HOOK'] in ('brief', 'fixed'):
            row['delivery_check'] = check_delivery(delivered, library_digests(),
                                                   expert_rules(task_dir) if arm == 'sf-expert' else None)
        if keep: (dest / 'compose.jsonl').write_text(log_text, encoding='utf-8')
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
                                  text=True, encoding='utf-8', timeout=300)
        except subprocess.TimeoutExpired:
            row.update(status='grader_timeout', passed=False, error='grader timed out; no fabricated score')
            return row
        (dest / 'grade.txt').write_text(test.stdout + test.stderr, encoding='utf-8')
        header = re.search(r'^GRADER: (.+)$', test.stdout, re.M)
        row['grader'] = header[1] if header else 'unversioned'
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
    ap.add_argument('--task', action='append', help='task directory; repeat for a suite')
    ap.add_argument('--arms', default='none,native,skillforge')
    ap.add_argument('--repeats', type=int, default=1)
    ap.add_argument('--tools', default='Read,Edit,Write,Bash,Glob,Grep,Skill')
    ap.add_argument('--timeout', type=int, default=900)
    ap.add_argument('--model', help='explicit model ID; required for paid runs')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--output', default='data/ab-results.jsonl')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--keep', action='store_true')
    ap.add_argument('--allow-static-grader', action='store_true',
                    help='grade without Postgres (static checks only); results are not comparable to behavioral runs')
    ap.add_argument('--crowd', action='append', help='directory of skill folders to install in every arm; repeatable')
    ap.add_argument('--freeze', help='manifest file: written on first use, then any change refuses the run')
    a = ap.parse_args()
    arms = [s.strip() for s in a.arms.split(',')]
    if not arms or len(set(arms)) != len(arms) or any(arm not in ARMS for arm in arms): ap.error('unknown or duplicate arms')
    if 'Skill' not in a.tools.split(','): ap.error('--tools must include Skill')
    if a.repeats < 1 or a.timeout < 1: ap.error('repeats and timeout must be positive')
    if not a.dry_run and not a.model: ap.error('--model is required to make paid comparisons reproducible')
    if a.crowd and not all(Path(c).is_dir() for c in a.crowd): ap.error('--crowd must be a directory')
    task_dirs = [Path(t).resolve() for t in (a.task or [str(ROOT / 'benchmarks/tasks/react-waterfall')])]
    if not a.dry_run:
        if not a.allow_static_grader and any(needs_postgres(t) for t in task_dirs) and not postgres_available():
            ap.error('a grader needs Postgres but none is available to this Python; run '
                     '`pip install -r requirements-dev.txt` (or pass --allow-static-grader and report it)')
        if 'sf-expert' in arms:
            unreviewed = [t.name for t in task_dirs if not expert_reviewed(t)]
            if unreviewed:
                ap.error(f"sf-expert selections not yet reviewed by a second developer: {', '.join(unreviewed)}. "
                         'Record the reviewer under "review" in benchmarks/expert/<task>.json.')
    if a.freeze:
        changed = check_freeze(a.freeze, manifest(task_dirs, a.model, a.tools, a.crowd))
        if changed:
            ap.error(f"frozen conditions changed since {a.freeze}: {', '.join(changed)}. "
                     'Start a new manifest (and a new output file) for a new experiment.')
    common = dict(plugin_sha256=digest_tree(ROOT / 'plugin'), seed=a.seed, model=a.model, tools=a.tools,
                  crowd=a.crowd, crowd_sha256=[digest_tree(Path(c)) for c in a.crowd] if a.crowd else None,
                  runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    rows = []; rng = random.Random(a.seed)
    path = Path(a.output)
    if not a.dry_run: path.parent.mkdir(parents=True, exist_ok=True)
    for task_dir in task_dirs:
        task = (task_dir / 'task.txt').read_text(encoding='utf-8').strip()
        metadata = dict(common, task=str(task_dir), task_sha256=digest_tree(task_dir),
                        scorer_sha256=hashlib.sha256((task_dir / 'test.py').read_bytes()).hexdigest())
        for repeat in range(a.repeats):
            for arm in rng.sample(arms, len(arms)):
                row = run_one(arm, task_dir, task, a.tools, a.timeout, a.dry_run, a.keep, a.model, a.crowd)
                if row is None: continue
                row.update(metadata, repeat=repeat + 1, settings=ARMS[arm])
                rows.append(row)
                if not a.dry_run:
                    with path.open('a', encoding='utf-8') as f: f.write(json.dumps(row) + '\n')
                print(f"[{task_dir.name}/{arm}] status={row['status']} score={row['score']} cost={row['cost']} "
                      f"brief={row['brief']} rule_fetches={row['rule_fetches']}")
    for task_dir in task_dirs:
        print(f'\n{task_dir.name}:')
        for arm in arms:
            group = [r for r in rows if r['arm'] == arm and r['task'] == str(task_dir)]
            if not group: continue
            valid = [r for r in group if r['status'] == 'ok']
            costs = [r['cost'] for r in group if r['cost'] is not None]
            scores = [r['score'] for r in valid if r['score']]
            seconds = [r['elapsed_seconds'] for r in group if r.get('elapsed_seconds') is not None]
            no_guidance = sum(not r['brief'] for r in group) if ARMS[arm] else None
            print(f"  {arm}: valid={len(valid)}/{len(group)}, full passes={sum(r['passed'] for r in valid)}/{len(valid)}, "
                  f"scores={scores}, no guidance={no_guidance if no_guidance is not None else 'n/a'}, "
                  f"median known cost={statistics.median(costs) if costs else 'unknown'} "
                  f"(unknown {len(group) - len(costs)}), median seconds={statistics.median(seconds) if seconds else 'unknown'}, "
                  f"graders={sorted({r.get('grader', '?') for r in valid})}")
            if ARMS[arm] and any(not r['brief'] for r in group):
                print('  WARNING: delivery not verified in some attempts; inspect transcripts and keep them in the report.')
            bad = [r['delivery_check'] for r in group if r.get('delivery_check', 'ok') != 'ok']
            if bad:
                print(f'  WARNING: {len(bad)} attempt(s) did not receive the intended rules intact ({bad[0]}); '
                      'their outcomes do not measure this arm.')
    if any(r['status'] != 'ok' for r in rows): sys.exit(1)


if __name__ == '__main__': main()
