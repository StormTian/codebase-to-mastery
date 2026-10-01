# Learning kit authoring

`scaffold_learning.py` creates editable `course.json`, HTML modules and `learning-kit.json`. `--from-course DIR` attaches only the missing learning files to an existing course; it never rewrites module content or assets. A scaffold contains authoring markers that validation intentionally rejects.

## Manifest v2

Use JSON and Python's standard library; no YAML dependency. The manifest is the canonical editable source for generated Markdown and the HTML learning panel.

- `schemaVersion: 2`, stable `kitId`, `mode: read-through|rebuild`, `profile: beginner|intermediate|advanced`, `scope`, `rebuildScope`, `runtimeEvidence`, `unverified`.
- `stages`: ordered entries with `id`, `title`, `outcome`, `modules` (course module IDs), `gate` (an observable learner action). Use `orient`, `trace`, `reason`, `rebuild`, `extend`, `teach-back`; read-through omits rebuild/extend and states the deferral in `rebuildScope`.
- `concepts`: entries with unique `id`, `name`, `stage`, `module`, `requires` (concept IDs), `outcome`, `explanation`, `dependsOn` (uncited repository paths/globs), `anchors`, `checkpoints`.
- Every anchor: `path`, `lines` (`"12-18"`), `text` (exact source), `claim`, `kind: source-observation|documentation|inference`. Exact text supports locating the claim, not automatically proving an interpretation.
- Every checkpoint: `prompt`, `answer`, `rubric` (nonempty list of assessable points), `hints` (optional incremental hints). A correct option alone is not an adequate transfer rubric.
- `notes`: Markdown strings named `overview`, `architecture`, `execution`, `abstractions`, `reading`, `decisions`, `extension`. Describe real paths, observed versus inferred relationships, invariants, counterexamples and excluded branches; use anchor references from the source map. These are authored content, not automatic architecture inference.
- `milestones`: empty for a deferred rebuild; otherwise entries with `id`, `title`, `concepts`, `requires` (earlier milestone IDs), `goal`, `invariant`, `exercise` (kit-relative Markdown), `commands` (argument arrays), `timeoutSeconds` (1–120), `starterExpectation: incomplete|pass`. Each command runs with working directory `playground/<variant>`. `{python}` resolves to the current Python interpreter. Never put a shell string in `commands`.

Paths must remain inside the source or kit as appropriate, including resolved symlinks. Concept and milestone dependencies must exist and form DAGs. Concepts cannot require a later stage. Rebuild/extend stages require behavioral milestones; read-through does not manufacture “all passed” implementation milestones.

## Output and ownership

```text
learning-kit.json           editable learning manifest
course.json / modules/      editable interactive lessons
index.html                  built offline course, includes learning map
LEARNING_PATH.md             generated stage outcomes and gates
study/00-overview.md ...     generated architecture, trace, abstractions,
                            reading order, decisions, source map, recall, extension
source-map.json              generated machine-readable exact anchors and prerequisites
playground/exercises/        authored lab briefs
playground/starter/          authored incomplete implementation
playground/reference/        authored positive control
playground/tests/            authored shared behavioral tests
playground/learner/          created only when starting learner work
lab-runs/                   actual command evidence; never implies mastery
learner-state.json           actual learner attempts; created when needed
LEARNING_JOURNAL.md          generated record of attempts and assessment
course-state.json            accepted source and learning baseline
course-update-report.*       next targeted work queue
```

Build changes a generated document only when its bytes differ. Do not edit generated Markdown and lose the change on rebuild: edit manifest notes/checkpoints instead. Briefs, starter, tests and module HTML remain ordinary editable files. Do not ship unexplained empty exercise trees.

## Adding depth to an old course

Run `scaffold_learning.py --from-course DIR --mode read-through`, author the manifest against its existing module IDs, build/validate, then accept the new baseline. The old `course-state.json` works with the upgraded updater; absent learning baseline entries appear as new concepts. Do not claim that old courses acquired new content merely because the tool now supports kits.

## Focused lessons

Single-file/diff teaching can use `lessons/YYYY-MM-DD-topic.md` without creating a full kit. Follow the same citation and uncertainty rules; use the lesson contract in [change-lessons.md](change-lessons.md). When attached to a kit, map its concepts and dependencies. Validate new HTML and manifest content normally. A standalone Markdown lesson needs manual excerpt checking; the course validator does not parse arbitrary Markdown citations.
