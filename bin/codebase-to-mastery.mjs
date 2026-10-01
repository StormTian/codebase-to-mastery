#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
const name = 'codebase-to-mastery';
const clients = { codex: '.agents', 'claude-code': '.claude' };

function options(args) {
  const result = { agents: [], global: false, directory: null, dryRun: false };
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--global' || arg === '-g') result.global = true;
    else if (arg === '--dry-run') result.dryRun = true;
    else if (arg === '--directory') {
      if (!args[i + 1] || args[i + 1].startsWith('-')) throw new Error('--directory needs a skill parent directory');
      result.directory = args[++i];
    } else if (arg === '--agent' || arg === '-a') {
      const start = i;
      while (args[i + 1] && !args[i + 1].startsWith('-')) result.agents.push(args[++i]);
      if (i === start) throw new Error('--agent needs codex or claude-code');
    } else throw new Error(`Unknown option: ${arg}`);
  }
  if (result.directory && (result.global || result.agents.length)) {
    throw new Error('--directory is used on its own, without --global or --agent');
  }
  for (const agent of result.agents) {
    if (!clients[agent]) throw new Error(`Unsupported agent: ${agent}. Use --directory for another client.`);
  }
  if (!result.agents.length) result.agents = Object.keys(clients);
  result.agents = [...new Set(result.agents)];
  return result;
}

function install(args) {
  const opts = options(args);
  const base = opts.global ? os.homedir() : process.cwd();
  const targets = opts.directory
    ? [path.join(path.resolve(opts.directory), name)]
    : opts.agents.map(agent => path.join(base, clients[agent], 'skills', name));
  if (opts.dryRun) {
    console.log(JSON.stringify({ version: pkg.version, targets }, null, 2));
    return;
  }
  // Preflight every destination before creating any installation.
  for (const target of targets) {
    try {
      fs.lstatSync(target);
      throw new Error(`Already exists: ${target}. Move the existing folder aside before installing.`);
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
  }
  const resources = [...new Set([...pkg.files.map(item => item.replace(/\/$/, '')), 'README.md', 'LICENSE', 'package.json'])];
  for (const resource of resources) {
    if (!fs.existsSync(path.join(root, resource))) throw new Error(`Missing packaged resource: ${resource}`);
  }
  for (const target of targets) {
    const parent = path.dirname(target);
    fs.mkdirSync(parent, { recursive: true });
    const staged = fs.mkdtempSync(path.join(parent, '.mastery-install-'));
    try {
      for (const resource of resources) {
        fs.cpSync(path.join(root, resource), path.join(staged, resource), { recursive: true, force: false, errorOnExist: true });
      }
      fs.renameSync(staged, target);
    } catch (error) {
      fs.rmSync(staged, { recursive: true, force: true });
      throw error;
    }
    console.log(`Installed ${name}@${pkg.version}: ${target}`);
  }
}

try {
  const args = process.argv.slice(2);
  if (args.includes('--help') || args.includes('-h')) {
    console.log(`Codebase to Mastery ${pkg.version}
Usage: codebase-to-mastery [--agent codex claude-code] [--global] [--dry-run]
       codebase-to-mastery --directory /path/to/skills [--dry-run]
Default: install for Codex and Claude Code in the current project.
Global: ~/.agents/skills (Codex), ~/.claude/skills (Claude Code).
Existing skill folders are preserved; move them aside before reinstalling.`);
  } else if (args.length === 1 && args[0] === '--version') console.log(pkg.version);
  else install(args);
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
