#!/usr/bin/env python3
"""Shared learning-manifest validation, rendering and evidence helpers (stdlib)."""
from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path

STAGES = ('orient', 'trace', 'reason', 'rebuild', 'extend', 'teach-back')
NOTE_TITLES = {
    'overview': '00-overview', 'architecture': '01-architecture',
    'execution': '02-execution', 'abstractions': '03-core-abstractions',
    'reading': '04-reading-order', 'decisions': '05-design-decisions',
    'extension': '08-extension',
}


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def inside(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError(f'Expected a relative path: {relative!r}')
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f'Path escapes its root: {relative!r}')
    return path


def write_changed(path: Path, value: str) -> None:
    if path.exists() and path.read_text(encoding='utf-8') == value:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding='utf-8')


def json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def load_kit(root: Path, config: dict) -> tuple[Path | None, dict | None]:
    name = config.get('learningKit')
    if not name:
        return None, None
    path = inside(root, name)
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('learning manifest must be an object')
    return path, value


def dag_errors(items: list[dict], label: str, key: str = 'requires') -> list[str]:
    errors = []
    ids = [item.get('id') for item in items]
    if len(set(ids)) != len(ids):
        errors.append(f'{label}: duplicate IDs')
    known = set(ids)
    graph = {}
    for item in items:
        deps = item.get(key, [])
        if not isinstance(deps, list) or any(not isinstance(dep, str) for dep in deps):
            errors.append(f'{label} {item.get("id")}: {key} must be a list of IDs')
            deps = []
        graph[item.get('id')] = deps
        for dep in deps:
            if dep not in known:
                errors.append(f'{label} {item.get("id")}: unknown prerequisite {dep}')
    active, done = set(), set()

    def visit(item_id: str) -> None:
        if item_id in active:
            errors.append(f'{label}: prerequisite cycle at {item_id}')
            return
        if item_id in done or item_id not in graph:
            return
        active.add(item_id)
        for dep in graph[item_id]:
            visit(dep)
        active.remove(item_id)
        done.add(item_id)

    for item_id in graph:
        visit(item_id)
    return errors


def validate_kit(root: Path, config: dict, kit: dict, source_root: Path) -> list[str]:
    # Imported at call time to avoid the course validator's optional-kit cycle.
    from validate_course import CodeCitation, dependency_problems, verify_citation
    errors = []
    if kit.get('schemaVersion') != 2:
        errors.append('learning manifest schemaVersion must be 2')
    for field in ('kitId', 'scope', 'rebuildScope'):
        if not isinstance(kit.get(field), str) or not kit[field].strip():
            errors.append(f'learning manifest needs {field}')
    if kit.get('mode') not in ('read-through', 'rebuild'):
        errors.append('learning mode must be read-through or rebuild')
    if kit.get('profile') not in ('beginner', 'intermediate', 'advanced'):
        errors.append('learning profile must be beginner, intermediate or advanced')
    for field in ('unverified', 'runtimeEvidence'):
        if not isinstance(kit.get(field), list):
            errors.append(f'{field} must be a list')
    if 'AUTHOR:' in json.dumps(kit, ensure_ascii=False):
        errors.append('learning manifest contains unfinished AUTHOR: markers')
    modules = {m['id'] for m in config.get('modules', [])}
    stages = kit.get('stages', [])
    if not isinstance(stages, list) or not stages or any(not isinstance(s, dict) for s in stages):
        return errors + ['learning stages must be a nonempty list of objects']
    stage_ids = [s.get('id') for s in stages]
    if any(s not in STAGES for s in stage_ids) or len(set(stage_ids)) != len(stage_ids):
        errors.append('stage IDs must be distinct capability levels')
    elif stage_ids != sorted(stage_ids, key=STAGES.index):
        errors.append('stages must progress from shallow to deep')
    needed = {'orient', 'trace', 'reason', 'teach-back'}
    if kit.get('mode') == 'rebuild':
        needed.update(('rebuild', 'extend'))
    if not needed.issubset(stage_ids):
        errors.append(f'learning mode needs stages: {sorted(needed)}')
    for stage in stages:
        for field in ('title', 'outcome', 'gate'):
            if not isinstance(stage.get(field), str) or not stage[field].strip():
                errors.append(f'stage {stage.get("id")}: missing {field}')
        refs = stage.get('modules')
        if not isinstance(refs, list) or not refs or any(m not in modules for m in refs):
            errors.append(f'stage {stage.get("id")}: needs existing course modules')

    concepts = kit.get('concepts', [])
    if not isinstance(concepts, list) or not concepts or any(not isinstance(c, dict) for c in concepts):
        return errors + ['concepts must be a nonempty list of objects']
    for c in concepts:
        if not isinstance(c.get('id'), str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*', c['id']):
            errors.append('concept IDs must be lowercase slugs')
            return errors
    errors.extend(dag_errors(concepts, 'concept'))
    by_id = {c['id']: c for c in concepts}
    for c in concepts:
        label = f'concept {c["id"]}'
        for field in ('name', 'outcome', 'explanation'):
            if not isinstance(c.get(field), str) or not c[field].strip():
                errors.append(f'{label}: missing {field}')
        if c.get('stage') not in stage_ids or c.get('module') not in modules:
            errors.append(f'{label}: unknown stage or module')
        for dep in c.get('requires', []) if isinstance(c.get('requires'), list) else []:
            if dep in by_id and c.get('stage') in STAGES and by_id[dep].get('stage') in STAGES:
                if STAGES.index(by_id[dep]['stage']) > STAGES.index(c['stage']):
                    errors.append(f'{label}: prerequisite {dep} belongs to a later stage')
        errors.extend(dependency_problems(c.get('dependsOn', []), label + ' dependsOn'))
        anchors = c.get('anchors')
        if not isinstance(anchors, list) or not anchors:
            errors.append(f'{label}: needs exact source anchors')
            anchors = []
        for anchor in anchors:
            if not isinstance(anchor, dict):
                errors.append(f'{label}: anchor must be an object')
                continue
            if anchor.get('kind') not in ('source-observation', 'documentation', 'inference'):
                errors.append(f'{label}: anchor needs an evidence kind')
            if not anchor.get('claim'):
                errors.append(f'{label}: anchor needs the claim it supports')
            citation = CodeCitation(str(anchor.get('path', '')), str(anchor.get('lines', '')))
            citation.chunks = [str(anchor.get('text', ''))]
            problem = verify_citation(citation, source_root)
            if problem:
                errors.append(f'{label}: {problem}')
        questions = c.get('checkpoints')
        if not isinstance(questions, list) or not questions:
            errors.append(f'{label}: needs an active-recall checkpoint')
            questions = []
        for q in questions:
            if not isinstance(q, dict) or not q.get('prompt') or not q.get('answer'):
                errors.append(f'{label}: checkpoint needs prompt and answer')
                continue
            if not isinstance(q.get('rubric'), list) or not q['rubric'] or any(not isinstance(r, str) or not r for r in q['rubric']):
                errors.append(f'{label}: checkpoint needs an assessable rubric')
    for stage_id in stage_ids:
        if not any(c.get('stage') == stage_id for c in concepts):
            errors.append(f'stage {stage_id}: no concept teaches this level')
    notes = kit.get('notes', {})
    for name in NOTE_TITLES:
        if not isinstance(notes, dict) or not isinstance(notes.get(name), str) or not notes[name].strip():
            errors.append(f'notes: missing {name}')

    milestones = kit.get('milestones', [])
    if not isinstance(milestones, list) or any(not isinstance(m, dict) for m in milestones):
        return errors + ['milestones must be a list of objects']
    for m in milestones:
        if not isinstance(m.get('id'), str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*', m['id']):
            return errors + ['milestone IDs must be lowercase slugs']
    errors.extend(dag_errors(milestones, 'milestone'))
    if kit.get('mode') == 'rebuild' and not milestones:
        errors.append('rebuild mode needs behavioral milestones')
    for m in milestones:
        label = f'milestone {m["id"]}'
        for field in ('title', 'goal', 'invariant'):
            if not isinstance(m.get(field), str) or not m[field].strip():
                errors.append(f'{label}: missing {field}')
        if not isinstance(m.get('concepts'), list) or not m['concepts'] or any(c not in by_id for c in m['concepts']):
            errors.append(f'{label}: needs existing concept IDs')
        try:
            if not inside(root, m.get('exercise', '')).is_file():
                errors.append(f'{label}: missing exercise file')
        except ValueError as exc:
            errors.append(f'{label}: {exc}')
        commands = m.get('commands')
        if not isinstance(commands, list) or not commands or any(
            not isinstance(cmd, list) or not cmd or any(not isinstance(arg, str) or not arg for arg in cmd)
            for cmd in commands
        ):
            errors.append(f'{label}: commands must be nonempty argument arrays')
        timeout = m.get('timeoutSeconds', 30)
        if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 120:
            errors.append(f'{label}: timeoutSeconds must be 1-120')
        if m.get('starterExpectation') not in ('incomplete', 'pass'):
            errors.append(f'{label}: starterExpectation must be incomplete or pass')
    if kit.get('mode') == 'rebuild':
        for stage in ('rebuild', 'extend'):
            taught = {c['id'] for c in concepts if c.get('stage') == stage}
            if not any(taught.intersection(m.get('concepts', [])) for m in milestones):
                errors.append(f'{stage} stage needs a covering behavioral milestone')
        for variant in ('starter', 'reference'):
            try:
                if not inside(root, 'playground/' + variant).is_dir():
                    errors.append(f'missing playground/{variant}')
            except ValueError as exc:
                errors.append(str(exc))
    return errors


def fenced(text: str) -> str:
    n = max([len(m.group()) + 1 for m in re.finditer(r'`+', text)] + [3])
    fence = '`' * n
    return f'{fence}\n{text}\n{fence}\n'


def render_documents(root: Path, config: dict, kit: dict, *, write: bool = True) -> dict[str, str]:
    rendered = {}

    def put(relative: str, text: str) -> None:
        rendered[relative] = text
        if write:
            write_changed(inside(root, relative), text)

    concepts = kit.get('concepts', [])
    path = [f'# {config["title"]} · Learning path', '', kit.get('scope', ''), '',
            f'- Mode: {kit.get("mode")}; learner: {kit.get("profile")}',
            f'- Source: {config.get("source", {}).get("revision", "unknown")}',
            f'- Rebuild scope / deferral: {kit.get("rebuildScope", "")}',
            '- Gates are practice targets; reading is not evidence of mastery.', '']
    for stage in kit.get('stages', []):
        path += [f'## {stage["title"]}', '', stage.get('outcome', ''), '',
                 f'Exit check: {stage.get("gate", "")}', '']
        path += [f'- [Module {mid}](index.html#{mid})' for mid in stage.get('modules', [])]
        path += [f'- {c["name"]}: {c["outcome"]}' for c in concepts if c.get('stage') == stage['id']]
        path += ['']
    path += ['## Materials', '', '[Source map](study/06-source-map.md) · [Recall checkpoints](study/07-active-recall.md)', '',
             '## Milestones', '']
    for m in kit.get('milestones', []):
        path += [f'- [{m["title"]}]({m["exercise"]}): {m["goal"]}']
    path += ['', '## Unverified / excluded', ''] + ['- ' + str(x) for x in kit.get('unverified', [])]
    path += ['', '## Runtime evidence (authored scope)', ''] + ['- ' + str(x) for x in kit.get('runtimeEvidence', [])]
    put('LEARNING_PATH.md', '\n'.join(path) + '\n')
    for name, filename in NOTE_TITLES.items():
        put('study/' + filename + '.md', '# ' + filename + '\n\n' + kit.get('notes', {}).get(name, '') + '\n')
    source_map, recall = ['# Source map', ''], ['# Active recall', '', 'Try before opening the answers; explain with evidence and a counterexample.', '']
    for c in concepts:
        source_map += [f'## {c["id"]} · {c["name"]}', '', c.get('explanation', ''), '',
                       f'Stage: {c.get("stage")}; requires: {", ".join(c.get("requires", [])) or "none"}', '',
                       f'Outcome: {c.get("outcome")}', '']
        for a in c.get('anchors', []):
            source_map += [f'`{a["path"]}:{a["lines"]}` ({a.get("kind")}) — {a.get("claim")}', '', fenced(a.get('text', ''))]
        recall += [f'## {c["name"]}', '']
        for q in c.get('checkpoints', []):
            recall += [q.get('prompt', ''), '', '<details><summary>Hints, answer and rubric</summary>', '']
            recall += ['- Hint: ' + h for h in q.get('hints', [])]
            recall += ['', q.get('answer', ''), ''] + ['- ' + r for r in q.get('rubric', [])]
            recall += ['', '</details>', '']
    put('study/06-source-map.md', '\n'.join(source_map) + '\n')
    put('study/07-active-recall.md', '\n'.join(recall) + '\n')
    put('source-map.json', json_text({'schemaVersion': 2, 'concepts': concepts}))
    return rendered


def learning_panel(config: dict, kit: dict) -> str:
    esc = lambda value: html.escape(str(value), quote=True)
    zh = str(config.get('lang', '')).startswith('zh')
    title = '由浅入深的学习路径' if zh else 'A path from recognition to transfer'
    cards = []
    for stage in kit.get('stages', []):
        labels = {m['id']: m['title'] for m in config['modules']}
        links = ' '.join(f'<a href="#{esc(mid)}">{("进入课程" if zh else "Open lesson") if len(stage.get("modules", [])) == 1 else esc(labels.get(mid, mid))}</a>' for mid in stage.get('modules', []))
        cards.append(f'<article class="learning-stage"><h3>{esc(stage["title"])}</h3><p>{esc(stage["outcome"])}</p><p class="gate">{esc(stage["gate"])}</p>{links}</article>')
    concepts = []
    for c in kit.get('concepts', []):
        anchors = ''.join(f'<p class="path-chip">{esc(a["path"])}:{esc(a["lines"])}</p><p>{esc(a["claim"])}</p><pre><code>{esc(a["text"])}</code></pre>' for a in c.get('anchors', []))
        questions = []
        for i, q in enumerate(c.get('checkpoints', [])):
            key = c['id'] + '-' + str(i)
            hints = ''.join('<li>' + esc(h) + '</li>' for h in q.get('hints', []))
            rubric = ''.join('<li>' + esc(r) + '</li>' for r in q.get('rubric', []))
            questions.append(f'<div class="recall" data-recall-id="{esc(key)}"><label for="recall-{esc(key)}">{esc(q["prompt"])}</label><textarea id="recall-{esc(key)}" rows="3" placeholder="{"先写下你的预测" if zh else "Write your prediction first"}"></textarea><details class="recall-answer"><summary>{"查看提示、答案与评价标准" if zh else "Hints, answer and rubric"}</summary><ul>{hints}</ul><p>{esc(q["answer"])}</p><ul>{rubric}</ul></details></div>')
        concepts.append(f'<details class="concept-card" id="concept-{esc(c["id"])}"><summary>{esc(c["name"])}</summary><p>{esc(c["explanation"])}</p><p>{"前置概念" if zh else "Prerequisites"}: {esc(", ".join(c.get("requires", [])) or "—")}</p><a href="#{esc(c["module"])}">{esc(c["outcome"])}</a>{"".join(questions)}<details><summary>{"精确源码锚点" if zh else "Exact source anchors"}</summary>{anchors}</details></details>')
    exports = f'<details class="export-preview" hidden><summary>{"可复制的导出记录" if zh else "Copyable export"}</summary><label for="export-data">{"尚未评价的回忆记录（JSON）" if zh else "Unassessed recall records (JSON)"}</label><textarea id="export-data" readonly rows="6"></textarea><a class="export-download" download="code-learning-recall.json">{"下载 JSON" if zh else "Download JSON"}</a></details>'
    return f'<section id="learning-path" class="learning-panel" data-kit-id="{esc(kit["kitId"])}"><p class="eyebrow">Code learning</p><h2>{title}</h2><p>{esc(kit["scope"])}</p><p>{esc(kit["rebuildScope"])}</p><div class="learning-stages">{"".join(cards)}</div><h3>{"概念地图与主动回忆" if zh else "Concept map and active recall"}</h3><p>{"回答保存在本机浏览器；阅读和自评不代表已掌握。" if zh else "Answers stay in this browser; reading and self-ratings do not establish mastery."}</p>{"".join(concepts)}<button type="button" class="export-learning-notes">{"导出回忆记录" if zh else "Export recall notes"}</button><p class="notes-feedback" aria-live="polite"></p>{exports}</section>'


def concept_dependencies(c: dict, config: dict) -> list[str]:
    module = next((m for m in config['modules'] if m['id'] == c['module']), {})
    return list(dict.fromkeys(c.get('dependsOn', []) + module.get('dependsOn', []) + config.get('globalDependsOn', [])))


def evidence_signature(c: dict, config: dict, source_root: Path, inventory: dict | None = None) -> str:
    from update_course import fingerprint_inventory, path_matches
    if inventory is None:
        inventory, _ = fingerprint_inventory(source_root, source_root / '__no_course__')
    paths = {a['path'] for a in c.get('anchors', [])}
    deps = concept_dependencies(c, config)
    files = {p: h for p, h in inventory.items() if p in paths or any(path_matches(p, d) for d in deps)}
    semantic = dict(c)
    semantic['anchors'] = [{k: v for k, v in a.items() if k != 'lines'} for a in c.get('anchors', [])]
    return digest({'concept': semantic, 'files': files})


def snapshot_kit(root: Path, config: dict, kit: dict) -> dict:
    records = {}
    for c in kit['concepts']:
        records[c['id']] = {
            'id': c['id'], 'title': c['name'], 'module': c['module'],
            'requires': c.get('requires', []), 'conceptHash': digest(c),
            'dependsOn': concept_dependencies(c, config),
            'citations': [{'source': a['path'], 'lines': a['lines'], 'text': a['text']} for a in c['anchors']],
        }
    return {'manifestHash': digest(kit), 'concepts': records,
            'milestones': {m['id']: digest(m) for m in kit.get('milestones', [])}}
