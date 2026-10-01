# Codebase to Mastery

**From reading real code to explaining, rebuilding and transferring its ideas.**

[中文说明](README.zh-CN.md) · [Skill instructions](SKILL.md) · [Validation](docs/validation.md) · [MIT license](LICENSE)

A portable Agent Skill for **Codex, Claude Code and other clients that support `SKILL.md`**. It turns a repository into a source-grounded learning path, with an offline interactive course, purposeful reading, active recall and bounded implementation exercises.

![Six-level learning path](docs/learning-path.jpg)

## What makes it different

The goal is a learning loop with observable evidence:

| Level | Learner capability | Materials and checks |
| --- | --- | --- |
| Orient | Explain purpose, actors and boundaries | Architecture overview and one visible journey |
| Trace | Follow calls and state through real source | Reading order, exact excerpts and prerequisite map |
| Reason | Explain contracts and failure paths | Invariants, counterexamples and assessment rubrics |
| Rebuild | Implement a bounded core behavior | Starter, separate reference and shared behavioral tests |
| Extend | Change one behavior while preserving others | Extension cases and regression checks |
| Teach back | Reconstruct the model and apply it elsewhere | Recall, transfer questions and assessed learning history |

Large repositories begin with a read-through path and an explicit candidate subsystem for rebuilding. A requested subsystem can receive a bounded lab without pretending to reproduce the entire project.

Source excerpts are checked against exact file paths and line ranges, including the final HTML. Incremental updates report affected modules, concepts, prerequisites and lab contracts. Historical learner responses survive source changes and are flagged for review.

**A usable course, a passing reference implementation and learner mastery are separate outcomes.** Mastery records require actual answers, rubric assessments and, for implementation exercises, a current passing learner run.

## Install

### One command for Codex and Claude Code

From the project where you want the skill available:

```bash
npx skills add StormTian/codebase-to-mastery \
  --skill codebase-to-mastery --agent codex claude-code
```

The [open-source Skills CLI](https://github.com/vercel-labs/skills) also supports other clients. Add `--global` for a personal installation, or select a different `--agent`. Node.js is required only for this installation method; the skill's helpers use Python's standard library.

### Manual installation

Codex, using the current documented personal skill location:

```bash
mkdir -p ~/.agents/skills
git clone https://github.com/StormTian/codebase-to-mastery.git \
  ~/.agents/skills/codebase-to-mastery
```

Claude Code:

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/StormTian/codebase-to-mastery.git \
  ~/.claude/skills/codebase-to-mastery
```

For project-scoped installation, put this folder at `.agents/skills/codebase-to-mastery` for Codex or `.claude/skills/codebase-to-mastery` for Claude Code. Some Codex installations and the Skills CLI's global Codex target use `~/.codex/skills`; use the location recognized by your installed client. Install one copy per client to avoid duplicate discovery. An existing clone can be updated with `git pull --ff-only` after reviewing local changes.

For another Agent Skills client, place the complete folder in its documented skill directory. Preserve `scripts/`, `references/`, `assets/` and their relative paths. `agents/openai.yaml` supplies optional Codex UI metadata; the shared workflow does not depend on it. See the [Agent Skills specification](https://agentskills.io/specification), [OpenAI documentation](https://learn.chatgpt.com/docs/build-skills) and [Claude Code documentation](https://code.claude.com/docs/en/skills).

## Use

In Codex:

```text
Use $codebase-to-mastery to teach me this repository progressively.
Start with its purpose and one request path, then guide source reading.
Choose a small subsystem for rebuilding and verified extension exercises.
```

In Claude Code:

```text
/codebase-to-mastery Teach me this repository progressively, from architecture
and source tracing to a bounded rebuild, active recall and transfer.
```

You can also request a focused mode:

- **Overview:** an accessible interactive architecture course.
- **Deep subsystem study:** contracts, source tracing, rebuild and failure cases.
- **Tutor:** one prediction → evidence → explanation → transfer cycle at a time.
- **Change lesson:** learn a changed file or diff with its prerequisites.
- **Refresh:** update affected learning material after the source changes.

Specify your background, language, goal and subsystem when useful. The skill adapts depth and uses the learner's language; it does not require an onboarding questionnaire before producing materials.

## Requirements and output

The host agent needs file access and command execution, **Python 3.10+**, and Git for source revisions or cloning. Browser access helps verify the interactive course. Network access is needed to fetch remote sources; built courses are self-contained HTML. No model API key, MCP server or paid service is required by the helper scripts.

Typical output:

```text
learning-kit.json / course.json / modules/   Editable teaching sources
index.html                                  Offline interactive course
LEARNING_PATH.md / study/ / source-map.json   Reading, recall and exact anchors
playground/starter/ / reference/ / tests/    Bounded exercises and controls
lab-runs/                                   Actual execution receipts
learner-state.json / LEARNING_JOURNAL.md      Actual assessed attempts, when present
course-state.json / course-update-report.*   Baseline and targeted update queue
```

Generated study documents derive from the manifest. Edit the manifest or modules, then rebuild. Browser notes are provisional and unassessed; they do not set mastery.

## Try the original teaching demo

From this repository's root, choose a **new output directory**:

```bash
python3 tests/create_demo.py /tmp/codebase-to-mastery-demo
python3 scripts/check_milestone.py /tmp/codebase-to-mastery-demo \
  --milestone core --variant starter
python3 scripts/check_milestone.py /tmp/codebase-to-mastery-demo \
  --milestone core --variant reference
```

Open the generated `index.html`. The core starter should report `EXPECTED_INCOMPLETE`; the reference should report `PASS`. This miniature runtime is an original teaching fixture, not production checkpoint/resume evidence.

For tests and reproducible controls:

```bash
python3 -m unittest discover -s tests -v
```

See [validation scope](docs/validation.md), [learning-kit authoring](references/learning-kit.md), [rebuild labs](references/rebuild-labs.md) and [tutoring/state](references/tutoring.md). Client installation compatibility does not establish educational effectiveness or production equivalence.

## Boundaries

The skill separates source observation, documentation claims, inference and actual runtime evidence. Real providers require separate verification, and learner mastery requires assessed learner work. Exercise commands require review; the runner avoids shell strings but is not an operating-system sandbox. Personal answers, credentials and machine-specific run evidence belong outside a shared skill repository.

## Repository and provenance

This is a single-skill repository: `SKILL.md` is at the root, with helpers in `scripts/`, guidance in `references/`, the offline template in `assets/`, and original fixtures/tests in `tests/`. The layout follows the reusable-folder pattern demonstrated by [anthropics/skills](https://github.com/anthropics/skills); installation examples follow [vercel-labs/skills](https://github.com/vercel-labs/skills).

[Provenance](references/provenance.md) records pinned inspirations and independent implementation. The [MIT license](LICENSE) covers this repository's original material. Teaching excerpts from other repositories retain their own license terms.
