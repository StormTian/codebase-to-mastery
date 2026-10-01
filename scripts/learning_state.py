#!/usr/bin/env python3
"""Record actual assessed learner answers; read status without mutating history."""
from __future__ import annotations
import argparse
import json
from datetime import date, timedelta
from pathlib import Path
from learning_kit import digest, evidence_signature, inside, json_text, load_kit, validate_kit, write_changed
from learning_updates import lab_hashes

KINDS = ('predict', 'trace', 'debug', 'rebuild', 'extend', 'teach-back', 'recall')
TRANSFER = {'debug', 'rebuild', 'extend', 'teach-back'}


def derived(attempts: list[dict], signature: str) -> tuple[str, bool, int]:
    if not attempts:
        return 'new', False, 0
    if attempts[-1]['evidenceSignature'] != signature:
        return 'reviewing', True, 0
    latest = attempts[-1]
    if latest['score'] == 0:
        return 'confused', False, 0
    if latest['score'] == 1:
        return 'reviewing', False, 0
    good = []
    for a in reversed(attempts):
        if a['evidenceSignature'] != signature or a['score'] < 2:
            break
        good.append(a)
    mastered = len(good) >= 2 and any(a['kind'] in TRANSFER for a in good)
    return ('mastered' if mastered else 'reviewing'), False, len(good)


def status(kit: dict, config: dict, source: Path, state: dict, today: date) -> dict:
    from update_course import fingerprint_inventory
    inventory, _ = fingerprint_inventory(source, source / '__no_course__')
    rows = []
    for c in kit['concepts']:
        attempts = [a for a in state['attempts'] if a['conceptId'] == c['id']]
        effective, stale, _ = derived(attempts, evidence_signature(c, config, source, inventory))
        latest = attempts[-1] if attempts else {}
        due = latest.get('nextReview')
        rows.append({'id': c['id'], 'name': c['name'], 'state': effective,
                     'historicalState': latest.get('statusAfter', 'new'), 'needsReview': stale,
                     'reviewDue': bool(due and due <= today.isoformat()), 'nextReview': due,
                     'attemptCount': len(attempts), 'requires': c.get('requires', [])})
    mastered = {r['id'] for r in rows if r['state'] == 'mastered'}
    for row in rows:
        row['prerequisiteGaps'] = [c for c in row['requires'] if c not in mastered]
    return {'kitId': kit['kitId'], 'today': today.isoformat(), 'concepts': rows,
            'assessmentBoundary': 'Scores are recorded rubric judgments, not automatic correctness proofs.'}


def journal(root: Path, state: dict) -> None:
    lines = ['# Learning journal', '', 'Actual answers and assessments; source changes preserve this history.', '']
    for a in state['attempts']:
        lines += [f'## {a["date"]} · {a["conceptId"]} · {a["kind"]}', '',
                  f'Score: {a["score"]}/3; status after assessment: {a["statusAfter"]}; next review: {a["nextReview"]}', '',
                  '### Learner response', '', a['response'], '', '### Assessment', '', a['feedback'], '',
                  f'Evidence fingerprint: `{a["evidenceSignature"]}`', '']
    write_changed(root / 'LEARNING_JOURNAL.md', '\n'.join(lines) + '\n')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('kit_dir', type=Path)
    p.add_argument('action', choices=('status', 'record'))
    p.add_argument('--attempt-file', type=Path)
    p.add_argument('--source-root', type=Path)
    p.add_argument('--today', help='Explicit learner-local YYYY-MM-DD')
    a = p.parse_args(argv)
    root = a.kit_dir.expanduser().resolve()
    config = json.loads((root / 'course.json').read_text(encoding='utf-8'))
    _, kit = load_kit(root, config)
    if not kit:
        p.error('Course has no declared learning kit')
    source = (a.source_root or Path(config['source']['root'])).expanduser().resolve()
    today = date.fromisoformat(a.today) if a.today else date.today()
    path = root / 'learner-state.json'
    state = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'schemaVersion': 1, 'kitId': kit['kitId'], 'attempts': []}
    if state.get('schemaVersion') != 1 or state.get('kitId') != kit['kitId']:
        p.error('Learner state belongs to another kit or unsupported schema; preserve it')
    if a.action == 'status':
        print(json_text(status(kit, config, source, state, today)))
        return 0
    if a.attempt_file is None:
        p.error('record needs --attempt-file with the learner response and rubric judgment')
    problems = validate_kit(root, config, kit, source)
    if problems:
        p.error('Refresh invalid teaching evidence before recording: ' + '; '.join(problems))
    attempt = json.loads(a.attempt_file.read_text(encoding='utf-8'))
    concept = next((c for c in kit['concepts'] if c['id'] == attempt.get('conceptId')), None)
    if not concept:
        p.error('Unknown concept')
    if attempt.get('kind') not in KINDS:
        p.error('Unknown assessment kind')
    if type(attempt.get('score')) is not int or not 0 <= attempt['score'] <= 3:
        p.error('score must be an integer from 0 to 3')
    for key in ('response', 'feedback'):
        if not isinstance(attempt.get(key), str) or not attempt[key].strip():
            p.error(f'Actual {key} is required; material generation is not learner evidence')
    if not isinstance(attempt.get('assessor'), str) or not attempt['assessor'].strip():
        p.error('assessor must identify the actual agent or human reviewer')
    attempt['assessor'] = attempt['assessor'].strip()
    when = date.fromisoformat(attempt.get('date', today.isoformat()))
    previous = [x for x in state['attempts'] if x['conceptId'] == concept['id']]
    if previous and when.isoformat() < previous[-1]['date']:
        p.error('Do not append an assessment before the latest assessment date')
    signature = evidence_signature(concept, config, source)
    ident = digest({'concept': concept['id'], 'kind': attempt['kind'],
                    'response': ' '.join(attempt['response'].split()), 'signature': signature})
    if any(x['attemptId'] == ident for x in state['attempts']):
        p.error('Duplicate answer on this evidence; repetition cannot manufacture mastery')
    lab_relative = attempt.get('labRun')
    if attempt['kind'] in ('rebuild', 'extend'):
        if not lab_relative:
            p.error('Rebuild/extend assessment needs an observed learner labRun')
        try:
            lab_path = inside(root, lab_relative)
            if not lab_path.is_relative_to((root / 'lab-runs').resolve()):
                p.error('labRun must be inside lab-runs/')
            run = json.loads(lab_path.read_text(encoding='utf-8'))
        except (ValueError, OSError) as exc:
            p.error(str(exc))
        milestone = next((m for m in kit['milestones'] if m['id'] == run.get('milestone')), None)
        if (run.get('kitId') != kit['kitId'] or run.get('variant') != 'learner' or run.get('outcome') != 'PASS'
                or not milestone or concept['id'] not in milestone['concepts']
                or run.get('evidenceSignatures', {}).get(concept['id']) != signature
                or run.get('labHashes') != lab_hashes(root)):
            p.error('labRun must be a current passing learner run covering this concept; reference runs do not count')
    record = {k: attempt[k] for k in ('conceptId', 'kind', 'response', 'score', 'feedback', 'assessor')}
    record.update(date=when.isoformat(), attemptId=ident, evidenceSignature=signature)
    if lab_relative:
        record['labRun'] = lab_relative
    effective, _, streak = derived(previous + [record], signature)
    interval = (1, 3, 7, 14)[min(max(streak-1, 0), 3)]
    record.update(statusAfter=effective, nextReview=(when + timedelta(days=interval)).isoformat())
    state['attempts'].append(record)
    # Atomic replacement of the record; the journal is a derived, editable-readable view.
    temporary = path.with_name('.learner-state.json.tmp')
    temporary.write_text(json_text(state), encoding='utf-8')
    temporary.replace(path)
    journal(root, state)
    print(f'Recorded actual assessment: {concept["id"]} → {effective}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
