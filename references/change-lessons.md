# Lessons from changes

Resolve the user's file/diff/ref first. For uncommitted work, distinguish the working tree from HEAD; for commits, identify both ends and the actual patch. Read enough callers, state and tests to explain the behavioral change. Do not treat every changed line as a new concept.

Deliver a concise lesson in the existing kit's `lessons/`, or a standalone learning directory when no kit exists:

1. Actual trigger and observable before/after behavior; mark inferred behavior.
2. Vocabulary and prerequisite concepts; add a short bridge if a concept was never taught.
3. Pre-question: predict the changed case before revealing the result.
4. Exact source excerpts with revision, path and ranges; distinguish old and new revisions.
5. Explain the responsibility and invariant, then a realistic common mistake/counterexample.
6. Post-question using a different case, staged hints, answer and rubric (collapsed in HTML, separated in Markdown).
7. A runnable small experiment when appropriate, actual result or explicit skip reason.
8. New confusion/review points, linked to existing concepts; record mastery only after real responses.

A single lesson should not rewrite the course or unrelated journal history. If the change invalidates existing material, use the updater and patch only affected concepts/modules. For old-revision excerpts, keep a revision-specific source checkout rather than comparing them against current source and weakening exact validation.
