# Bounded reconstruction and extension

Choose one contract the inspected repo actually implements. Write input/output, state transition, invariant, failure behavior, and deliberate simplifications first. A lab is a teaching reconstruction; passing it does not establish production equivalence.

Use the project's language when that improves transfer. Python stdlib is suitable for language-independent state-machine exercises, but disclose the translation. A real provider, credentials, container or expensive dependency should normally be replaced by a deterministic fixture, with the missing integration labeled.

Each milestone needs an exercise brief: goal, source anchors, acceptance cases, non-goals, command, expected starter result, staged hints, comparison questions. Preserve starter functions that raise `NotImplementedError`; keep a completed reference in a separate directory. Tests load the selected variant from their working directory, so identical assertions judge both.

Test behavior rather than matching source shape: normal flow, invalid input, interrupted state, consistency after reload, or another invariant the source actually teaches. Include at least one counterexample that a plausible wrong implementation fails. Check the environment/import contract before incomplete milestones; a syntax error, missing import or timeout is a broken lab, not an expected learning failure.

After reviewing the commands:

```bash
python3 <skill-dir>/scripts/check_milestone.py <kit> --milestone contract --variant starter
python3 <skill-dir>/scripts/check_milestone.py <kit> --milestone core --variant starter
python3 <skill-dir>/scripts/check_milestone.py <kit> --milestone core --variant reference
```

The runner executes only the selected commands, uses no shell, applies timeouts, and saves bounded stdout/stderr plus hashes and exit codes in `lab-runs/`. It is not an OS sandbox. Only run reviewed, authorized local exercises. A reference failure blocks delivery; a starter milestone must fail through `NotImplementedError` and not through import/syntax failures. The contract and any setup milestones declare `starterExpectation: pass`.

At learning time, copy starter to `playground/learner/` without overwriting existing work. Predict a case, implement it, run the learner variant, explain why the invariant holds, and only then compare with reference/source. A passed learner run can support a rebuild assessment, but must accompany the learner's explanation.

For extension, declare one changed contract, add a new acceptance case, run the original regression cases, then discuss tradeoffs and a failure boundary. A stub exercise or a list of suggested tests is not a verified rebuild deliverable.
