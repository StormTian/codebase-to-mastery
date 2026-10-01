"""Targeted change reports for concepts and dependent lab contracts."""
from __future__ import annotations
import json
from pathlib import Path
from learning_kit import concept_dependencies, digest, json_text, load_kit


def lab_hashes(root: Path) -> dict:
    files = {}
    for name in ('exercises', 'starter', 'reference', 'tests'):
        for p in (root / 'playground' / name).rglob('*'):
            if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts:
                files[p.relative_to(root).as_posix()] = digest(p.read_bytes().hex())
    return files


def learning_changes(root: Path, source: Path, config: dict, state: dict,
                     changed_paths: list[str], apply_rebases: bool) -> tuple[dict | None, set[str]]:
    from update_course import locate_citation, path_matches
    kit_path, kit = load_kit(root, config)
    old = state.get('learningKit', {})
    if not kit:
        if old:
            return {'removed': True, 'concepts': [], 'milestones': [], 'needsReview': list(old.get('concepts', {}))}, set()
        return None, set()
    baseline = old.get('concepts', {})
    current = {c['id']: c for c in kit['concepts']}
    reports, mapped = [], set()
    modified = False
    for cid in dict.fromkeys(list(baseline) + list(current)):
        c, before = current.get(cid), baseline.get(cid)
        r = {'id': cid, 'status': 'unchanged', 'changedFiles': [], 'citations': [], 'reasons': []}
        reports.append(r)
        if not c:
            r.update(status='refresh', reasons=['concept removed from learning manifest'])
            continue
        deps = concept_dependencies(c, config)
        paths = {a['path'] for a in c['anchors']}
        hits = [p for p in changed_paths if p in paths or any(path_matches(p, dep) for dep in deps)]
        mapped.update(hits)
        r['changedFiles'] = hits
        if not before:
            r.update(status='new-concept', reasons=['no accepted learning baseline'])
            continue
        r['citations'] = [locate_citation(a, source) for a in before['citations']]
        statuses = {a['status'] for a in r['citations']}
        edited = digest(c) != before['conceptHash']
        explicit = [p for p in changed_paths if any(path_matches(p, dep) for dep in deps)]
        if statuses.intersection(('changed', 'missing', 'ambiguous')):
            r.update(status='refresh', reasons=['exact source evidence changed or is no longer unique'])
        elif 'moved' in statuses and not explicit and not edited:
            r.update(status='rebase-only', reasons=['identical excerpts moved uniquely'])
            if apply_rebases:
                for located in r['citations']:
                    if located['status'] == 'moved':
                        for anchor in c['anchors']:
                            if anchor['path'] == located['source'] and anchor['lines'] == located['oldLines']:
                                anchor['lines'] = located['newLines']
                                modified = True
                r['safeRebaseApplied'] = True
        elif hits or edited or 'moved' in statuses:
            r.update(status='review', reasons=['mapped source or teaching/rubric changed'])
    if modified:
        kit_path.write_text(json_text(kit), encoding='utf-8')
    direct = {r['id'] for r in reports if r['status'] in ('refresh', 'review', 'new-concept')}
    affected = set(direct)
    while True:
        more = {cid for cid, c in current.items() if set(c.get('requires', [])).intersection(affected)} - affected
        if not more:
            break
        affected.update(more)
    for r in reports:
        r['dependentReview'] = r['id'] in affected and r['id'] not in direct
    labs_changed = lab_hashes(root) != old.get('labFiles', {})
    milestones = []
    for m in kit.get('milestones', []):
        changed = digest(m) != old.get('milestones', {}).get(m['id'])
        needs = bool(set(m['concepts']).intersection(affected) or changed or labs_changed)
        milestones.append({'id': m['id'], 'status': 'review' if needs else 'unchanged',
                           'affectedConcepts': sorted(set(m['concepts']).intersection(affected)),
                           'contractEdited': changed, 'labFilesEdited': labs_changed})
    for mid in old.get('milestones', {}):
        if not any(m['id'] == mid for m in milestones):
            milestones.append({'id': mid, 'status': 'refresh', 'reason': 'milestone removed'})
    return {'concepts': reports, 'milestones': milestones, 'needsReview': sorted(affected),
            'notesChanged': digest(kit.get('notes', {})) != old.get('notesHash'),
            'learnerHistoryPreserved': True}, mapped
