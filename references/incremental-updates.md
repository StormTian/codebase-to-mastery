# Incremental course updates

Use this workflow only after a complete course has an accepted `course-state.json` baseline.

## What the baseline records

The baseline stores:

- the source revision and a file fingerprint inventory;
- the accepted module file hash;
- every exact code excerpt and its former line range;
- module-level `dependsOn` patterns and course-wide `globalDependsOn` patterns.

It stores hashes and the small cited excerpts needed for relocation, not a duplicate of the source repository.

## Read the update report

Run `update_course.py` without `--accept-baseline`. It writes both JSON and Markdown reports and assigns one status to each module:

- `unchanged`: none of its evidence changed. Do not rewrite or reformat it.
- `rebase-only`: cited text is identical but moved to a unique new line range. With `--apply-safe-rebases`, only `data-lines` changes.
- `review`: a mapped dependency changed while the exact excerpt remains usable, or the course module was edited after the baseline. Inspect the listed diff and change the module only if its claim or teaching flow is affected.
- `refresh`: a cited excerpt changed, disappeared, became ambiguous, or a baseline module is missing. Refresh the affected screens and dependent interactions.
- `new-module`: a course module exists without baseline history. Review it before accepting the next baseline.

Changed source files that match no module or global dependency are listed as unmapped. Most can be irrelevant to the course, but inspect meaningful architecture, entry-point, interface, or feature changes. Add a dependency or a focused course addition only when the curriculum actually needs it.

## Targeted editing rules

1. Preserve `unchanged` module files byte-for-byte.
2. Start with `refresh`, then `review`; do not reopen unrelated modules for stylistic cleanup.
3. Trace only the changed path far enough to re-establish the affected claim. A local update is not permission to speculate about the rest of the system.
4. If a new feature creates a genuinely new actor or user journey, prefer adding one focused screen or module over restructuring the entire course.
5. Re-run the ordinary build and validator. Preview affected modules plus navigation around any newly added module.
6. Run `update_course.py --accept-baseline` only after the course passes validation. This advances the source revision and fingerprints for the next update.

If `course-state.json` is missing for an older course, first build and validate it against the current source, then run `--accept-baseline`. That current state becomes the starting point; changes before it cannot be reconstructed reliably.

## Progressive kits

The unchanged version-1 baseline schema gains an optional `learningKit` section. Old courses need no migration. The section snapshots concept evidence and rubrics, source dependencies, milestone contracts and lab file hashes. An old baseline without this section reports newly attached concepts as `new-concept` until they are validated and accepted.

Both report formats contain concept statuses: `unchanged`, `rebase-only`, `review`, `refresh`, `new-concept`. Safe rebases alter only a uniquely moved anchor's line range. A changed source-map excerpt or interpretation/rubric needs review; dependent concepts are flagged through the prerequisite graph, and affected milestone contracts are listed. Changed lab files conservatively flag lab milestones for review; the updater does not execute them or infer their correctness. Authored note changes are shown separately.

Build rerenders Markdown only where bytes change. Inspect affected source maps, questions and lab tests alongside HTML; a readable explanation alone is not evidence that a changed invariant still holds. Baseline acceptance invokes both validators and refuses bad anchors or DAGs, but it does not rerun positive/negative lab controls. Run affected controls explicitly before delivery.

Learner history is never rewritten by the updater. `learning_state.py status` compares recorded evidence fingerprints with current mapped source and teaching content and marks stale assessments `needsReview`. It does not erase past mastery or invent new attempts. A harmless file change can conservatively request review even when an excerpt rebases unchanged; distinguish that request from proof of a regression.
