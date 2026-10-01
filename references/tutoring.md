# Tutoring, active recall and durable state

Start from the learner's request and existing journal, not a fixed onboarding questionnaire. Select one concept and its prerequisites. The useful cycle is: predict from the interface → inspect a short exact excerpt → explain state/control flow → try a changed or failing case → reconstruct the idea without the excerpt. Ask one question, allow the response, then assess with the checkpoint rubric. Use hints before a full answer when wanted. If the user asks for the answer, explain it directly and record no invented attempt.

Return to a missing prerequisite in this codebase. Keep useful confusions as specific questions, such as “does FINISHED also prove the artifact exists?” A self-rating or confidence statement can guide pace but is not mastery evidence.

## State commands

```bash
python3 <skill-dir>/scripts/learning_state.py <kit> status --source-root <repo> --today 2026-10-01
python3 <skill-dir>/scripts/learning_state.py <kit> record --attempt-file <attempt.json> --source-root <repo>
```

`status` never writes files. `record` creates state only when there is a real assessment. The attempt file contains:

```json
{
  "conceptId": "event-loop",
  "kind": "debug",
  "response": "The learner's actual answer, in their own words.",
  "score": 2,
  "feedback": "Which rubric points were met or missed.",
  "assessor": "codex",
  "date": "2026-10-01"
}
```

Kinds: `predict`, `trace`, `debug`, `rebuild`, `extend`, `teach-back`, `recall`. Scores: 0 = incorrect/confused, 1 = partial/assisted, 2 = independently correct with explanation, 3 = independently correct with a counterexample/transfer. Use actual evidence; a generated reference answer is not a response. `assessor` is a nonempty label identifying the actual reviewer, such as `codex`, `claude-code`, `opencode`, `agent` or `user`. The label records provenance; it does not authenticate the reviewer. Open-ended grading is human/model judgment against the saved rubric, not automatic truth detection.

For `rebuild` or `extend`, include `labRun` pointing to a runner-generated JSON under `lab-runs/`, with variant `learner`, PASS, and a milestone that covers this concept. The source/manifest evidence fingerprint must still match. Passing a reference variant is rejected as learner evidence.

States: `new`, `reviewing`, `confused`, `mastered`. A failed latest response means confused. Partial means reviewing. Mastered requires two distinct correct attempts on current evidence, including a transfer kind (`debug`, `rebuild`, `extend`, `teach-back`). The response and kind identify duplicate attempts; repeating the same answer cannot manufacture mastery. After an incorrect attempt, require two fresh correct attempts again. This is a modest local criterion, not certification.

Review intervals after consecutive correct attempts: 1, 3, 7, 14 days (then 14); incorrect/assisted resets to tomorrow. `--today` sets an explicit learner-local date; default uses the execution machine's local date. On a remote host, pass the learner's local date explicitly. Due dates are hints, not scheduled notifications. Use the host's automation tool only if the user asks for reminders.

Each attempt stores its source/teaching fingerprint. Source or rubric changes leave historical responses intact; status reports `needsReview` and uses `reviewing` as the effective state until new evidence meets the criterion. Do not silently rewrite old answers or delete mastered history.

The HTML recall field and reading checklist store provisional notes locally, survive reload, and can export them. They do not update `learner-state.json` or set mastery. Exported answers need actual rubric assessment before recording.
