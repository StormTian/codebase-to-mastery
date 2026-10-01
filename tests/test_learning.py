"""Behavioral v2 tests: real builds, negative evidence, local updates and learner state."""
from __future__ import annotations
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from create_demo import SOURCE, build
from test_tooling import run_script


class LearningTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        shutil.copytree(SOURCE, self.source)
        self.course = self.root / 'course'
        with contextlib.redirect_stdout(io.StringIO()):
            build(self.course, self.source)

    def tearDown(self):
        self.temp.cleanup()

    def kit(self):
        return json.loads((self.course / 'learning-kit.json').read_text())

    def save(self, kit):
        (self.course / 'learning-kit.json').write_text(json.dumps(kit, ensure_ascii=False, indent=2) + '\n')

    def accept(self):
        run_script('update_course.py', self.course, '--accept-baseline')

    def validate(self, success=True):
        run_script('build_course.py', self.course)
        result = run_script('validate_course.py', self.course, check=False)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def record(self, kind='predict', response='Fixtures only: a unique learner response', score=2,
               cid='state', lab=None, success=True, assessor='codex'):
        attempt = {'conceptId':cid,'kind':kind,'response':response,'score':score,
                   'feedback':'Fixture rubric assessment, not the human user.','assessor':assessor,'date':'2026-10-01'}
        if lab: attempt['labRun'] = lab
        p = self.root / 'attempt.json';p.write_text(json.dumps(attempt))
        result = run_script('learning_state.py', self.course, 'record', '--attempt-file', p, check=False)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def states(self):
        result = run_script('learning_state.py', self.course, 'status', '--today', '2026-10-02')
        return {c['id']:c for c in json.loads(result.stdout)['concepts']}

    def lab(self, milestone, variant, success=True):
        before = set((self.course / 'lab-runs').glob('*.json'))
        result = run_script('check_milestone.py', self.course, '--milestone', milestone, '--variant', variant, check=False)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        added = set((self.course / 'lab-runs').glob('*.json')) - before
        self.assertEqual(len(added),1)
        path = added.pop()
        return path, json.loads(path.read_text())

    def test_full_build_and_original_source_behavior(self):
        self.validate()
        self.assertTrue((self.course / 'study/06-source-map.md').exists())
        self.assertIn('learning-panel', (self.course / 'index.html').read_text())
        result = subprocess.run([sys.executable,str(self.course / 'playground/tests/test_runtime.py')],
                                cwd=self.source,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Ran 4 tests',result.stderr)

    def test_assessment_provenance_accepts_other_clients(self):
        for label in ('claude-code', 'opencode', 'agent', 'user'):
            self.record(response=f'Fixture response from {label}; not a human attempt.', assessor=label)
            state = json.loads((self.course / 'learner-state.json').read_text())
            self.assertEqual(state['attempts'][-1]['assessor'], label)
        before = (self.course / 'learner-state.json').read_bytes()
        self.record(response='Fixture with missing reviewer', assessor=' ', success=False)
        self.assertEqual((self.course / 'learner-state.json').read_bytes(), before)

    def test_scaffold_markers_are_not_deliverable(self):
        dest = self.root / 'unfinished'
        run_script('scaffold_learning.py',dest,'--title','Test','--subtitle','Test','--source-root',self.source)
        run_script('build_course.py',dest)
        result = run_script('validate_course.py',dest,check=False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('unfinished',result.stderr)

    def test_source_map_forgery_blocks_baseline(self):
        before = (self.course / 'course-state.json').read_bytes()
        kit = self.kit();kit['concepts'][0]['anchors'][0]['text'] += '\n# fabricated'
        self.save(kit)
        result = self.validate(False)
        self.assertIn('excerpt differs',result.stderr)
        refused = run_script('update_course.py',self.course,'--accept-baseline',check=False)
        self.assertNotEqual(refused.returncode,0)
        self.assertEqual((self.course / 'course-state.json').read_bytes(),before)

    def test_unknown_prerequisite_and_cycle_rejected(self):
        kit=self.kit();kit['concepts'][0]['requires']=['unknown'];self.save(kit)
        self.assertIn('unknown prerequisite',self.validate(False).stderr)
        kit['concepts'][0]['requires']=['commit'];self.save(kit)
        errors=self.validate(False).stderr
        self.assertIn('cycle',errors);self.assertIn('later stage',errors)

    def test_unsafe_source_and_symlink_rejected(self):
        kit=self.kit();a=kit['concepts'][0]['anchors'][0];a['path']='../outside.py';self.save(kit)
        self.assertIn('unsafe',self.validate(False).stderr)
        outside=self.root/'outside.py';outside.write_text(a['text'])
        (self.source/'escape.py').symlink_to(outside)
        a['path']='escape.py';self.save(kit)
        self.assertIn('unsafe',self.validate(False).stderr)

    def test_generated_material_tampering_rejected(self):
        (self.course/'source-map.json').write_text('{}\n')
        result=run_script('validate_course.py',self.course,check=False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('material missing or stale',result.stderr)
        self.validate()

    def test_starter_failure_and_reference_positive_controls(self):
        _,record=self.lab('contract','starter');self.assertEqual(record['outcome'],'PASS')
        for mid in ('core','budget'):
            _,record=self.lab(mid,'starter');self.assertEqual(record['outcome'],'EXPECTED_INCOMPLETE')
            _,record=self.lab(mid,'reference');self.assertEqual(record['outcome'],'PASS')

    def test_import_failure_is_a_broken_lab(self):
        p=self.course/'playground/starter/runtime.py';p.write_text('import definitely_missing_fixture_module\n')
        _,record=self.lab('core','starter',success=False)
        self.assertEqual(record['outcome'],'FAIL')
        self.assertIn('ModuleNotFoundError',record['results'][0]['stderr'])

    def test_wrong_reference_behavior_is_rejected(self):
        p=self.course/'playground/reference/runtime.py'
        p.write_text(p.read_text().replace('state.cursor = index + 1','state.cursor = index'))
        _,record=self.lab('core','reference',success=False)
        self.assertEqual(record['outcome'],'FAIL')

    def test_command_arrays_and_exercise_paths(self):
        kit=self.kit();kit['milestones'][0]['commands']='python unsafe.py';self.save(kit)
        self.assertIn('argument arrays',self.validate(False).stderr)
        kit['milestones'][0]['commands']=[['{python}','../tests/test_runtime.py']]
        kit['milestones'][0]['exercise']='../../outside.md';self.save(kit)
        self.assertIn('escapes',self.validate(False).stderr)

    def test_record_needs_answer_and_duplicate_cannot_master(self):
        self.record(response='',success=False)
        self.assertFalse((self.course/'learner-state.json').exists())
        self.record(response='One independently correct response.')
        self.record(response='One independently correct response.',success=False)
        self.assertEqual(self.states()['state']['state'],'reviewing')

    def test_mastery_needs_transfer_and_recovers_after_confusion(self):
        self.record(kind='predict',response='Prediction with an explanation.')
        self.record(kind='recall',response='Recall with an explanation.')
        self.assertEqual(self.states()['state']['state'],'reviewing')
        self.record(kind='debug',response='A different failure case with a counterexample.',score=3)
        self.assertEqual(self.states()['state']['state'],'mastered')
        self.record(kind='debug',response='A new confused answer.',score=0)
        self.assertEqual(self.states()['state']['state'],'confused')
        self.record(kind='debug',response='Corrected independently with a new case.')
        self.assertEqual(self.states()['state']['state'],'reviewing')

    def test_reference_run_does_not_count_as_learner_evidence(self):
        path,_=self.lab('core','reference')
        self.record(kind='rebuild',cid='reconstruct',lab=path.relative_to(self.course).as_posix(),success=False)
        shutil.copytree(self.course/'playground/reference',self.course/'playground/learner')
        path,_=self.lab('core','learner')
        self.record(kind='rebuild',cid='reconstruct',lab=path.relative_to(self.course).as_posix())

    def test_source_change_flags_history_without_writing(self):
        self.record(kind='predict',response='Original prediction.')
        self.record(kind='debug',response='Independent transfer on original source.')
        before=(self.course/'learner-state.json').read_bytes()
        p=self.source/'runtime.py';p.write_text('# An unrelated comment on mapped source.\n'+p.read_text())
        row=self.states()['state']
        self.assertTrue(row['needsReview']);self.assertEqual(row['historicalState'],'mastered')
        self.assertEqual(row['state'],'reviewing')
        self.assertEqual((self.course/'learner-state.json').read_bytes(),before)

    def test_local_dependency_change_flags_only_relevant_lab(self):
        p=self.source/'policy.json';p.write_text('{"budget":1}')
        kit=self.kit();kit['concepts'][4]['dependsOn']=['policy.json'];self.save(kit);self.accept()
        before={p.name:p.read_bytes() for p in (self.course/'modules').glob('*.html')}
        p.write_text('{"budget":2}')
        run_script('update_course.py',self.course)
        report=json.loads((self.course/'course-update-report.json').read_text())
        concepts={c['id']:c for c in report['learning']['concepts']}
        self.assertEqual(concepts['budget']['status'],'review')
        self.assertTrue(concepts['transfer']['dependentReview'])
        self.assertEqual(concepts['state']['status'],'unchanged')
        labs={m['id']:m['status'] for m in report['learning']['milestones']}
        self.assertEqual(labs,{'contract':'unchanged','core':'unchanged','budget':'review'})
        self.assertEqual(before,{p.name:p.read_bytes() for p in (self.course/'modules').glob('*.html')})

    def test_unique_line_move_rebases_both_formats(self):
        p=self.source/'runtime.py';p.write_text('# New heading.\n'+p.read_text())
        run_script('update_course.py',self.course,'--apply-safe-rebases')
        report=json.loads((self.course/'course-update-report.json').read_text())
        self.assertTrue(all(c['status']=='rebase-only' for c in report['learning']['concepts']))
        self.assertTrue(all(c.get('safeRebaseApplied') for c in report['learning']['concepts']))
        self.validate();self.accept()
        run_script('update_course.py',self.course)
        report=json.loads((self.course/'course-update-report.json').read_text())
        self.assertEqual(report['summary']['changedFiles'],0)
        self.assertTrue(all(c['status']=='unchanged' for c in report['learning']['concepts']))

    def test_semantic_source_change_requires_refresh(self):
        p=self.source/'runtime.py';p.write_text(p.read_text().replace('json.dumps(asdict(state), sort_keys=True)','json.dumps(asdict(state))'))
        run_script('update_course.py',self.course)
        report=json.loads((self.course/'course-update-report.json').read_text())
        concepts={c['id']:c for c in report['learning']['concepts']}
        self.assertEqual(concepts['snapshot']['status'],'refresh')
        self.assertIn('reconstruct',report['learning']['needsReview'])

    def test_attach_to_old_course_preserves_modules_and_assets(self):
        config_path=self.course/'course.json';config=json.loads(config_path.read_text());del config['learningKit']
        config_path.write_text(json.dumps(config));(self.course/'learning-kit.json').unlink()
        before={p.relative_to(self.course).as_posix():p.read_bytes() for name in ('modules','assets') for p in (self.course/name).glob('*') if p.is_file()}
        run_script('scaffold_learning.py','--from-course',self.course)
        after={p.relative_to(self.course).as_posix():p.read_bytes() for name in ('modules','assets') for p in (self.course/name).glob('*') if p.is_file()}
        self.assertEqual(before,after)
        refused=run_script('scaffold_learning.py','--from-course',self.course,check=False)
        self.assertNotEqual(refused.returncode,0)


if __name__ == '__main__':
    unittest.main()
