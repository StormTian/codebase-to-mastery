#!/usr/bin/env python3
"""Run one reviewed local lab milestone and save observed evidence, never mastery."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from learning_kit import evidence_signature, inside, json_text, load_kit, validate_kit
from learning_updates import lab_hashes

LIMIT = 65536


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('kit_dir', type=Path)
    p.add_argument('--milestone', required=True)
    p.add_argument('--variant', choices=('starter', 'reference', 'learner'), required=True)
    p.add_argument('--source-root', type=Path)
    a = p.parse_args(argv)
    root = a.kit_dir.expanduser().resolve()
    config = json.loads((root / 'course.json').read_text(encoding='utf-8'))
    _, kit = load_kit(root, config)
    if not kit:
        p.error('Course has no declared learning kit')
    source = (a.source_root or Path(config['source']['root'])).expanduser().resolve()
    problems = validate_kit(root, config, kit, source)
    if problems:
        raise SystemExit('\n'.join(problems))
    milestone = next((m for m in kit['milestones'] if m['id'] == a.milestone), None)
    if milestone is None:
        p.error('Unknown milestone')
    cwd = inside(root, 'playground/' + a.variant)
    if not cwd.is_dir():
        p.error('Selected variant does not exist; create learner work from starter first')
    results = []
    for raw in milestone['commands']:
        command = [sys.executable if arg == '{python}' else arg for arg in raw]
        env = os.environ.copy()
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        timed_out = False
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            try:
                completed = subprocess.run(command, cwd=cwd, env=env, stdout=out, stderr=err,
                                           timeout=milestone.get('timeoutSeconds', 30), check=False)
                code = completed.returncode
            except subprocess.TimeoutExpired:
                timed_out, code = True, None
            except OSError as exc:
                code = None
                err.write(str(exc).encode())
            out_size, err_size = out.tell(), err.tell()
            out.seek(0); err.seek(0)
            stdout = out.read(LIMIT).decode('utf-8', errors='replace')
            stderr = err.read(LIMIT).decode('utf-8', errors='replace')
        results.append({'command': raw, 'cwd': str(cwd), 'exitCode': code, 'timedOut': timed_out,
                        'stdout': stdout, 'stderr': stderr,
                        'truncated': out_size > LIMIT or err_size > LIMIT})
        if timed_out or code is None:
            break
    incomplete = a.variant == 'starter' and milestone['starterExpectation'] == 'incomplete'
    passed = bool(results) and all(r['exitCode'] == 0 and not r['timedOut'] for r in results)
    expected_failure = False
    if incomplete and not passed:
        failing = [r for r in results if r['exitCode'] != 0]
        expected_failure = bool(failing) and all(
            r['exitCode'] is not None and not r['timedOut'] and not r['truncated']
            and 'NotImplementedError' in (r['stdout'] + r['stderr'])
            and not any(t in (r['stdout'] + r['stderr']) for t in ('SyntaxError', 'ImportError', 'ModuleNotFoundError', 'AssertionError'))
            for r in failing
        )
    outcome = 'EXPECTED_INCOMPLETE' if expected_failure else ('PASS' if passed and not incomplete else 'FAIL')
    signatures = {c['id']: evidence_signature(c, config, source) for c in kit['concepts'] if c['id'] in milestone['concepts']}
    record = {'schemaVersion': 1, 'kitId': kit['kitId'], 'recordedAt': datetime.now(timezone.utc).isoformat(),
              'milestone': milestone['id'], 'variant': a.variant, 'outcome': outcome,
              'evidenceSignatures': signatures, 'labHashes': lab_hashes(root), 'results': results,
              'scope': 'Local teaching reconstruction; does not validate upstream integrations or learner mastery.'}
    name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + a.milestone + '-' + a.variant + '-' + uuid.uuid4().hex[:8] + '.json'
    target = root / 'lab-runs' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json_text(record), encoding='utf-8')
    print(f'{outcome}: {milestone["id"]} ({a.variant})')
    print(f'Evidence: {target}')
    return 0 if outcome in ('PASS', 'EXPECTED_INCOMPLETE') else 1


if __name__ == '__main__':
    raise SystemExit(main())
