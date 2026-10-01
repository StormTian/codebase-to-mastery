import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const cli = path.join(root, 'bin/codebase-to-mastery.mjs');
const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
function project(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'mastery-installer-test-'));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  return directory;
}
function run(cwd, ...args) {
  return spawnSync(process.execPath, [cli, ...args], { cwd, encoding: 'utf8' });
}
function checkResources(destination) {
  for (const relative of ['SKILL.md', 'VERSION', 'LICENSE', 'scripts/build_course.py',
    'references/learning-kit.md', 'assets/course-template/base.html', 'tests/create_demo.py']) {
    assert.deepEqual(fs.readFileSync(path.join(destination, relative)), fs.readFileSync(path.join(root, relative)));
  }
}

test('default installation copies complete resources to both project clients', t => {
  const cwd = project(t);
  assert.equal(run(cwd).status, 0);
  for (const client of ['.agents', '.claude']) checkResources(path.join(cwd, client, 'skills/codebase-to-mastery'));
});
test('explicit client and custom directory select only their intended targets', t => {
  const cwd = project(t);
  assert.equal(run(cwd, '--agent', 'codex', 'codex').status, 0);
  assert.equal(fs.existsSync(path.join(cwd, '.claude')), false);
  const custom = path.join(cwd, 'other-client/skills');
  assert.equal(run(cwd, '--directory', custom).status, 0);
  checkResources(path.join(custom, 'codebase-to-mastery'));
});
test('an existing second destination blocks all writes and preserves local edits', t => {
  const cwd = project(t);
  const existing = path.join(cwd, '.claude/skills/codebase-to-mastery');
  fs.mkdirSync(existing, { recursive: true });
  fs.writeFileSync(path.join(existing, 'SKILL.md'), 'preserve my changes');
  assert.notEqual(run(cwd).status, 0);
  assert.equal(fs.existsSync(path.join(cwd, '.agents')), false);
  assert.equal(fs.readFileSync(path.join(existing, 'SKILL.md'), 'utf8'), 'preserve my changes');
});
test('dangling target symlinks are preserved and refused', t => {
  const cwd = project(t);
  const parent = path.join(cwd, '.agents/skills');
  fs.mkdirSync(parent, { recursive: true });
  const target = path.join(parent, 'codebase-to-mastery');
  fs.symlinkSync(path.join(cwd, 'missing'), target, 'dir');
  assert.notEqual(run(cwd, '--agent', 'codex').status, 0);
  assert.equal(fs.lstatSync(target).isSymbolicLink(), true);
});
test('dry run, help and version are read-only, including global destinations', t => {
  const cwd = project(t);
  assert.equal(run(cwd, '--version').stdout.trim(), pkg.version);
  assert.equal(run(cwd, '--help').status, 0);
  const global = run(cwd, '--global', '--dry-run');
  assert.equal(global.status, 0);
  assert.deepEqual(JSON.parse(global.stdout).targets, ['.agents', '.claude'].map(client => path.join(os.homedir(), client, 'skills/codebase-to-mastery')));
  assert.deepEqual(fs.readdirSync(cwd), []);
});
test('unsupported or conflicting options fail before creating files', t => {
  const cwd = project(t);
  for (const args of [['--agent'], ['--agent', 'unknown'], ['--directory'],
    ['--directory', 'skills', '--global'], ['--directory', 'skills', '--agent', 'codex'], ['--unknown']]) {
    assert.notEqual(run(cwd, ...args).status, 0);
  }
  assert.deepEqual(fs.readdirSync(cwd), []);
});
