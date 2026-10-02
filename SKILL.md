---
name: codebase-to-mastery
description: Build source-grounded code learning paths from a repository, from accessible architecture lessons to guided reading, active recall, subsystem rebuilding and extension exercises. Also tutor from real code, teach recent changes, track evidenced learning progress, and refresh existing learning kits. Use for learning or teaching codebases, not ordinary implementation or code review.
license: MIT
metadata:
  version: "1.1.1"
  compatibility: Requires Python 3.10+, Git, file access and command execution. Network access is needed only to fetch remote sources. Works with Codex, Claude Code and other Agent Skills clients.
---

# Codebase to Mastery · 源码掌握工坊

Help the learner progress from recognizing a real project to tracing, explaining, rebuilding and extending a bounded part of it. Invoke as `$codebase-to-mastery` in Codex, `/codebase-to-mastery` in Claude Code, or ask another Agent Skills client to use this skill. Default to an offline interactive course plus an editable learning kit; honor requests for a smaller deliverable. A usable kit and demonstrated learner mastery are separate outcomes.

Resolve `<skill-dir>` to this installed folder, not the target repository. Use the host client's file, command and preview tools; no client-specific connector or SDK is required. `agents/openai.yaml` is optional Codex UI metadata and is not part of the shared workflow. Run the original teaching demo with `python3 <skill-dir>/tests/create_demo.py <new-output-dir>`.

## Choose the right scope

Infer language, experience, goal and available scope from the request and existing kit. State reasonable defaults and continue; ask only when an unknown materially changes the work. Use the learner's language. Beginner lessons define terms and show small examples; experienced learners can skip to contracts, failure cases and tradeoffs.

| Request | Route | Read when needed |
|---|---|---|
| Learn/teach an entire project | Progressive kit; large repos begin with read-through | [curriculum](references/curriculum-design.md), [kit authoring](references/learning-kit.md) |
| Only an interactive overview | Existing HTML-only workflow | [HTML contract](references/module-authoring.md) |
| Rebuild/understand a subsystem deeply | Kit with an explicitly bounded rebuild | [rebuild labs](references/rebuild-labs.md) |
| Tutor me / quiz me / continue learning | One prediction → evidence → explanation → transfer cycle | [tutoring and state](references/tutoring.md) |
| Teach today's changed file or diff | Focused lesson linked to existing concepts | [change lessons](references/change-lessons.md) |
| Source project changed | Preserve unaffected material; inspect affected evidence | [incremental updates](references/incremental-updates.md) |

Do not force a Socratic interview on someone asking for finished materials. In tutor mode, give one useful question at a time and wait for the answer before judging it; honor requests for direct explanation. Author sequentially unless the user explicitly authorizes parallel agents.

## Ground the learning in source

Resolve “this project” to the current workspace. Inspect another local path in place. For public URLs reuse a checkout or clone into a temporary directory. Read applicable `AGENTS.md` and entry documentation. Record repository URL, full revision when available, working-tree changes, access date and excluded scope. Use targeted discovery, then follow one concrete input through calls, state, output and a failure path.

Distinguish source observation, documentation claim, research inference and actual runtime evidence. Every teaching excerpt and source-map anchor uses a repository-relative path, a one-based continuous range and exact text. Teach author intent only when documented. Source parsing does not establish a dynamic call graph; label diagrams accordingly. Unverified external services, models, auth, MCP and sandbox behavior stay explicit.

Do not modify the source repo for teaching. Put output outside it unless the user supplies a destination. Keep experiments under the kit's playground. Avoid copying entire upstream implementations; check licenses before distributing excerpts or adaptations.

## Build the progressive path

Use these capability levels, adjusting length to the project:

1. **Orient:** explain the purpose, actors and a visible journey.
2. **Trace:** follow real source in a purposeful reading order; predict intermediate state.
3. **Reason:** identify contracts, invariants, failure paths and design tradeoffs.
4. **Rebuild:** reimplement a small core behavior, then compare with source.
5. **Extend:** make a controlled change and verify a new case plus regression behavior.
6. **Teach back:** reconstruct the mental model from memory and transfer it to a different scenario.

For large projects, deliver levels 1–3 and teach-back first, with an explicit rebuild deferral and candidate subsystem. If a bounded rebuild is requested, deliver it even when the whole repo is large. Avoid converting an eight-subsystem runtime into a pretend complete reconstruction. Agent projects can use the [Agent runtime lens](references/agent-runtime-lens.md); mark absent mechanisms as absent or unverified.

Create source-map concepts with prerequisites, exact anchors, learner outcomes and checkpoints. Teach missing prerequisites locally using this repository's examples. A glossary supplies vocabulary; the prerequisite graph supplies learning order. Reuse [module briefs](references/module-brief-template.md) for substantial modules. A metaphor is optional and should clarify the specific concept.

## Scaffold, author and verify

For a new progressive kit:

```bash
python3 <skill-dir>/scripts/scaffold_learning.py <output-dir> \
  --title "Project learning path" --subtitle "Trace, explain and test one core journey" \
  --source-root <repo> --lang zh-CN --mode read-through --profile beginner
```

For a bounded lab use `--mode rebuild`. Replace all generated authoring markers in `learning-kit.json` and `modules/`; the scaffold is not a finished lesson. Read [kit authoring](references/learning-kit.md) for schema and commands. To add a kit to an existing course use `--from-course <course-dir>`; preserve its modules and assets. HTML-only requests may continue using `scaffold_course.py` unchanged.

Author a concise overview, architecture, execution trace, core abstractions, reading order, decisions and counterexamples. Include a component conversation and a stepwise flow in HTML. Checkpoints should ask for prediction, tracing, debugging or transfer, with answer rubrics and staged hints. HTML active-recall answers start collapsed. Keep editable semantic content in the manifest and module files; generated study documents derive from it.

In rebuild mode, provide starter, separate reference, shared behavioral tests and milestone exercise notes. Review commands before running them. Check environment/import contract first, expected incomplete starter second, reference positive control third. Save runs, including failures. Do not solve a learner's current exercise unless they ask.

```bash
python3 <skill-dir>/scripts/build_course.py <output-dir>
python3 <skill-dir>/scripts/validate_course.py <output-dir> --source-root <repo>
python3 <skill-dir>/scripts/update_course.py <output-dir> --source-root <repo> --accept-baseline
```

Build renders study documents and embeds the learning map when `course.json` declares `learningKit`. Validation checks both formats; old HTML-only courses remain supported. Baseline acceptance does not execute exercises. Run lab controls separately using `check_milestone.py` as described in [rebuild labs](references/rebuild-labs.md).

Preview HTML at desktop and narrow sizes; inspect keyboard operation, quiz feedback, recall, concept map, code scrolling and reduced motion. Fix visible problems. If browser or source access is unavailable, preserve artifacts and disclose that verification limit; do not claim the missing check passed.

## Continue and deliver

Record actual learner responses with `learning_state.py`, following [tutoring](references/tutoring.md). Do not mark concepts mastered from page views, generated answers, self-ratings or reference runs. Learning records live in the kit, not the host client's global memory. Status is read-only; review scheduling is local metadata, not an automatic reminder.

For updates run `update_course.py --apply-safe-rebases`; use both module and learning-concept reports. Update affected lessons, source-map anchors, dependent questions and lab contracts. Keep unaffected modules byte-for-byte; keep all learner history and flag stale evidence for review. Never accept a baseline if either source or kit validation fails.

Deliver links to `index.html`, `LEARNING_PATH.md`, the source map and any playground. State inspected revision, scope, verified controls and untested behavior. For a skill-upgrade request, deliver the working skill and verification artifacts rather than pretending the user has completed its learning path.

See [provenance](references/provenance.md) for the inspected inspirations. Templates and tooling are implemented here independently.
