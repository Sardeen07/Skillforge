#!/usr/bin/env python3
"""Validate exported rules, metadata, provenance, licenses and local safety signals.

Offline by default. `--verify-links` checks each unique rule reference with bounded HTTPS
requests; external source repositories themselves remain pinned by the build manifest.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugin/skills/skillforge/scripts'))
from retrieval import load_rules, parse_pack, read_safe, strip_frontmatter  # noqa: E402
from scan import ALLOWED, containment, normalize_license, risk_flags, shingles  # noqa: E402

SHA = re.compile(r'^[0-9a-f]{40}$')
ALLOWED_EVIDENCE = {'untested', 'measured', 'expert-reviewed', 'source-verified'}


def validate(index, root, curation, domains_path, verify_links=False):
    errors, warnings = [], []
    root = Path(root)
    domain_data = json.loads(Path(domains_path).read_text(encoding='utf-8'))
    domains = set(domain_data.get('domains', []))
    modules = {m['name']: m for m in index.get('modules', [])}
    if len(modules) != len(index.get('modules', [])):
        errors.append('duplicate module name in index')
    curated = json.loads(Path(curation).read_text(encoding='utf-8'))
    specs = {m['name']: m for m in curated.get('modules', [])}
    exported_names = {m['name'] for m in index.get('modules', []) if m.get('kind') == 'module'}
    eligible_names = {n for n, s in specs.items() if s.get('status') in ('provisional', 'preferred')}
    if exported_names != eligible_names:
        errors.append(f'curation/export eligibility mismatch: {len(exported_names ^ eligible_names)} names')

    all_rules = load_rules(index, root, 'coding')
    ids = [r['id'] for r in all_rules]
    for rule_id, count in Counter(ids).items():
        if count > 1:
            errors.append(f'duplicate rule ID: {rule_id} ({count} copies)')
    exact = {}
    refs = set()
    for module in index.get('modules', []):
        name = module['name']
        spec = specs.get(name, {})
        source = spec.get('source', {})
        if source.get('kind') == 'authored':
            try:
                source = json.loads((root / Path(module['path']).parent / 'SOURCE.json').read_text(encoding='utf-8'))
            except (OSError, ValueError):
                errors.append(f'{name}: authored pack is missing generated SOURCE.json provenance')
                source = {}
        if module.get('kind') == 'core':
            continue
        license_name = normalize_license(source.get('license', ''))
        if license_name not in ALLOWED:
            errors.append(f'{name}: missing or disallowed license {source.get("license")!r}')
        if source.get('kind') == 'authored':
            if not source.get('authorship') or not source.get('repo') or not source.get('checked_against'):
                errors.append(f'{name}: authored source needs authorship, repository path and checked-against version')
        else:
            if not source.get('repo') or not SHA.fullmatch(source.get('commit', '')):
                errors.append(f'{name}: imported source needs repository and full 40-hex pinned commit')
        if not (module.get('technologies') or module.get('applies')):
            errors.append(f'{name}: module has no technology applicability metadata')
        path = module.get('path', '')
        try:
            source_text = read_safe(root, path)
        except (OSError, ValueError) as exc:
            errors.append(f'{name}: cannot safely read source {path!r}: {exc}')
            continue
        if path.endswith('RULES.md'):
            header, entries = parse_pack(source_text)
            if len(entries) < 1:
                errors.append(f'{name}: authored rule pack is empty')
            for entry in entries:
                if not entry.get('versions') and not header.get('checked_against'):
                    warnings.append(f'{name}/{entry["name"]}: no pinned technology/document version')
                if entry.get('evidence', 'untested') not in ALLOWED_EVIDENCE:
                    errors.append(f'{name}/{entry["name"]}: invalid evidence status')
        for flag in risk_flags(source_text):
            if flag['severity'] == 'reject':
                errors.append(f'{name}: safety scan rejected source ({flag["id"]})')
            else:
                warnings.append(f'{name}: safety scan review ({flag["id"]})')

    for rule in all_rules:
        if not rule.get('title', '').strip() or len(rule.get('title', '')) > 180:
            errors.append(f'{rule["id"]}: missing or oversized title')
        if len(set(re.findall(r'[a-z0-9]+', rule.get('tags', '').lower()))) < 2:
            errors.append(f'{rule["id"]}: needs at least two distinct technology/concept tags')
        if len(rule.get('body', '').strip()) < 100:
            errors.append(f'{rule["id"]}: guidance is too short to be independently useful')
        if rule.get('evidence', 'untested') not in ALLOWED_EVIDENCE:
            errors.append(f'{rule["id"]}: invalid evidence status {rule.get("evidence")!r}')
        if not rule.get('technologies') and not rule.get('tags'):
            errors.append(f'{rule["id"]}: no applicability technology metadata')
        fields = rule.get('refs', [])
        module = modules.get(rule['module'], {})
        spec = specs.get(rule['module'], {})
        if not fields and spec.get('source', {}).get('kind') != 'authored':
            # For imported reference files, module SOURCE.json pins the source repository,
            # commit, license and upstream path; per-file refs are supplementary.
            if not module.get('source', {}).get('commit'):
                errors.append(f'{rule["id"]}: missing source attribution')
        elif not fields:
            errors.append(f'{rule["id"]}: missing source attribution/reference')
        for ref in fields:
            url = ref.strip()
            parsed = urlparse(url)
            if parsed.scheme != 'https' or not parsed.hostname:
                errors.append(f'{rule["id"]}: reference must use HTTPS: {url!r}')
                continue
            refs.add(url)
            if parsed.hostname not in domains:
                errors.append(f'{rule["id"]}: reference host not in reviewed allowlist: {parsed.hostname}')
        normalized = ' '.join(re.findall(r'[a-z0-9]+', rule.get('body', '').lower()))
        if normalized in exact:
            errors.append(f'{rule["id"]}: exact duplicate content of {exact[normalized]}')
        exact[normalized] = rule['id']

    if verify_links:
        def check_link(url):
            req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'SkillForge-library-validator/1'})
            try:
                with urllib.request.urlopen(req, timeout=8) as response:
                    return None if response.status < 400 else f'link returned HTTP {response.status}: {url}'
            except (urllib.error.URLError, TimeoutError, ValueError) as exc:
                return f'link could not be verified ({exc}): {url}'
        with ThreadPoolExecutor(max_workers=12) as pool:
            warnings.extend(item for item in pool.map(check_link, sorted(refs)) if item)
    return len(all_rules), refs, errors, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-links', action='store_true', help='HEAD-check unique HTTPS rule references')
    args = parser.parse_args()
    index_path = ROOT / 'plugin/library/index.json'
    index = json.loads(index_path.read_text(encoding='utf-8'))
    count, refs, errors, warnings = validate(index, ROOT / 'plugin/library', ROOT / 'forge/curation/coding.json',
                                             ROOT / 'forge/curation/reference-domains.json', args.verify_links)
    print(f'Rules: {count}; modules: {len(index["modules"])}; unique references: {len(refs)}')
    for item in warnings:
        print('WARN', item)
    for item in errors:
        print('ERROR', item)
    print(f'Validation: {"FAILED" if errors else "passed with warnings" if warnings else "passed"} '
          f'({len(errors)} errors, {len(warnings)} warnings)')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
