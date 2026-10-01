# Curriculum design

## Audience and outcome

Adapt to the learner's stated background. With no background given, begin accessibly and offer optional depth; do not make a self-described engineer sit through a vocabulary interview. Define first-use terms for beginners. Intermediate learners practice tracing and failure diagnosis. Advanced learners focus on invariants, alternatives, bounded reconstruction and extension evidence.

Use the capability ladder in SKILL.md as learning goals, not six mandatory modules. Several goals can share a module, and substantial goals can need multiple lessons. A large repository starts with purposeful read-through and an explicit rebuild deferral. A user-requested subsystem can still receive a verified lab. Maintain one concept map across the overview, source-reading path, exercises and tutor sessions.

## Choose a narrative spine

Anchor the course to one observable action: submitting a form, running a command, importing a file, or calling a library entry point. Follow that action through the code. Add secondary flows only when they clarify an important boundary or failure mode.

A useful arc is:

1. what the product does and what happens after the chosen action;
2. the small cast of components responsible for it;
3. how state or data crosses those boundaries;
4. external systems, persistence, and trust boundaries;
5. one or two design patterns worth recognizing;
6. how the flow fails and where to inspect first;
7. how to request a safe change without breaking an invariant.

This is a menu, not a checklist. A small command-line tool may need four modules; a multi-service application may need six or seven.

## Select evidence

Prefer short excerpts that reveal responsibility, boundaries, and decisions. A useful excerpt lets the learner answer “where does this happen?” or “what would I change?” Avoid boilerplate, generated files, lockfiles, and long blocks whose important line is hidden.

Each excerpt must preserve the original text and identify its repository-relative path and one-based line range. Explain what the code does, why it exists here, and what kind of change would belong elsewhere.

For every module, also record the files that support claims not represented by a code excerpt. Add those repository-relative paths or glob patterns to the module's `dependsOn` entry in `course.json`. Put files whose change could affect the whole course in `globalDependsOn`. Keep the map narrow and causal: a module should depend on the evidence it actually teaches, not every file discovered during analysis.

## Design interactions

Combine active recall with transfer. First predict a concrete case; inspect the source; explain the state; then diagnose a changed or failing case. Recall without explanation is insufficient, but successful recognition of a multiple-choice answer is also insufficient. Save a rubric, a counterexample and optional hints for each checkpoint. Wrong answers should explain the specific misconception.

Do not count completed pages or generated exercises as learner mastery. The frontend stores provisional recall, while the tutor records actual assessments separately. When an assumed prerequisite has never been taught, add a short bridge using the same source instead of an unrelated generic lecture.

Use a component conversation for coordination or handoffs. Use a stepwise data flow for requests, pipelines, state transitions, or event propagation. Animations must remain understandable when motion is disabled.

## Visual pacing

Treat every `.screen` as one visual thought. Use diagrams, cards, flows, or code translation when they convey structure better than prose. Keep prose blocks short and prefer concrete labels from the repository over generic names such as “service A.”
