#!/usr/bin/env python3
"""Scaffold a progressive kit, or attach one without rewriting existing lessons."""
from __future__ import annotations
import argparse
import json
import uuid
from pathlib import Path
from learning_kit import STAGES, json_text
from scaffold_course import main as scaffold_course

TITLES = {
    'orient': '01 · 认识项目全貌', 'trace': '02 · 沿源码追踪执行',
    'reason': '03 · 解释契约与失败', 'rebuild': '04 · 重建一个核心机制',
    'extend': '05 · 扩展并验证', 'teach-back': '06 · 复述与迁移',
}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output_dir', type=Path, nargs='?')
    p.add_argument('--from-course', type=Path)
    p.add_argument('--title')
    p.add_argument('--subtitle')
    p.add_argument('--source-root', type=Path)
    p.add_argument('--mode', choices=('read-through', 'rebuild'), default='read-through')
    p.add_argument('--profile', choices=('beginner', 'intermediate', 'advanced'), default='beginner')
    p.add_argument('--lang', default='zh-CN')
    a = p.parse_args(argv)
    if bool(a.output_dir) == bool(a.from_course):
        p.error('Choose output_dir or --from-course, not both')
    root = (a.output_dir or a.from_course).expanduser().resolve()
    if (root / 'learning-kit.json').exists():
        p.error('Learning kit already exists; preserve it and edit in place')
    ids = [s for s in STAGES if a.mode == 'rebuild' or s not in ('rebuild', 'extend')]
    if a.from_course:
        config = json.loads((root / 'course.json').read_text(encoding='utf-8'))
        if config.get('learningKit'):
            p.error('Course already declares a learning kit')
    else:
        if not (a.title and a.subtitle and a.source_root):
            p.error('New kits require --title, --subtitle and --source-root')
        args = [str(root), '--title', a.title, '--subtitle', a.subtitle,
                '--source-root', str(a.source_root), '--lang', a.lang]
        for stage in ids:
            args += ['--module', TITLES[stage] if a.lang.startswith('zh') else stage.replace('-', ' ').title()]
        scaffold_course(args)
        config = json.loads((root / 'course.json').read_text(encoding='utf-8'))
    modules = config['modules']
    stages, concepts = [], []
    for i, stage in enumerate(ids):
        mids = [m['id'] for j, m in enumerate(modules) if min(len(ids)-1, j * len(ids) // len(modules)) == i]
        if not mids:
            mids = [modules[min(i, len(modules)-1)]['id']]
        stages.append({'id': stage, 'title': TITLES[stage] if a.lang.startswith('zh') else stage.title(),
                       'outcome': 'AUTHOR: observable capability', 'modules': mids, 'gate': 'AUTHOR: transfer task'})
        concepts.append({'id': stage + '-concept', 'name': 'AUTHOR: real concept name',
                         'stage': stage, 'module': mids[0], 'requires': [ids[i-1]+'-concept'] if i else [],
                         'outcome': 'AUTHOR: practical action', 'explanation': 'AUTHOR: source-grounded explanation',
                         'dependsOn': [], 'anchors': [{'path': 'AUTHOR: repository-relative file', 'lines': '1-1',
                                                     'text': 'AUTHOR: exact source excerpt', 'claim': 'AUTHOR: what it supports',
                                                     'kind': 'source-observation'}],
                         'checkpoints': [{'prompt': 'AUTHOR: predict or diagnose a case', 'answer': 'AUTHOR: reasoned answer',
                                          'rubric': ['AUTHOR: assessable point'], 'hints': []}]})
    kit = {'schemaVersion': 2, 'kitId': str(uuid.uuid4()), 'mode': a.mode, 'profile': a.profile,
           'scope': 'AUTHOR: chosen journey and exclusions',
           'rebuildScope': 'AUTHOR: bounded subsystem' if a.mode == 'rebuild' else 'AUTHOR: explicitly deferred rebuild and candidate subsystem',
           'runtimeEvidence': [], 'unverified': ['AUTHOR: runtime or external boundaries not exercised'],
           'stages': stages, 'concepts': concepts,
           'notes': {n: 'AUTHOR: repository-specific ' + n for n in ('overview','architecture','execution','abstractions','reading','decisions','extension')},
           'milestones': []}
    (root / 'learning-kit.json').write_text(json_text(kit), encoding='utf-8')
    config['learningKit'] = 'learning-kit.json'
    (root / 'course.json').write_text(json_text(config), encoding='utf-8')
    if a.mode == 'rebuild':
        for name in ('exercises', 'starter', 'reference', 'tests'):
            (root / 'playground' / name).mkdir(parents=True, exist_ok=True)
    print(f'Created progressive manifest: {root / "learning-kit.json"}')
    print('Author the manifest and lessons; scaffold markers intentionally fail validation.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
