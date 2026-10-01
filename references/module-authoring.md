# Module authoring contract

Each file under `modules/` contains one top-level section and no document shell:

```html
<section class="course-module" id="module-01" data-title="From click to result">
  <div class="screen hero-screen">
    <p class="eyebrow">Module 1</p>
    <h2>From click to result</h2>
    <p class="lede">A concrete promise to the learner.</p>
  </div>

  <div class="screen">
    <h3>The boundary that starts the flow</h3>
    <p>Short explanation with a <dfn data-definition="A precise plain-language definition.">technical term</dfn>.</p>
  </div>
</section>
```

## Exact code translation

Use one or more figures with exact source text. Escape `<`, `>`, and `&` inside `<code>`. The validator compares the decoded excerpt with the requested source lines.

```html
<figure class="code-translation" data-source="src/app.py" data-lines="12-18">
  <div class="code-pane">
    <p class="pane-label source-label"></p>
    <pre><code>exact source text</code></pre>
  </div>
  <figcaption>
    <p class="pane-label">Plain English</p>
    <p>Explain responsibility, not syntax trivia.</p>
  </figcaption>
</figure>
```

Do not add ellipses inside a cited range. Cite a smaller contiguous range instead.

The course script fills `.source-label` from `data-source` and `data-lines`, so a safe incremental rebase can move an unchanged excerpt without leaving a stale visible label.

## Incremental dependency map

Exact citations are tracked automatically. Add other evidence used by the module to its `dependsOn` list in `course.json`:

```json
{
  "id": "module-01",
  "title": "From click to result",
  "file": "01-from-click-to-result.html",
  "dependsOn": ["src/routes/upload.ts", "src/services/import/**"]
}
```

Use repository-relative paths or glob patterns. Do not add broad patterns such as `**/*` merely to avoid thinking about ownership; they make every update look global and defeat incremental refresh.

## Applied quiz

Each module needs at least one `.quiz`. Exactly one choice has `data-correct="true"`.

```html
<div class="quiz" data-explanation="The handler owns the boundary where this value enters the system.">
  <p class="quiz-kicker">Try it</p>
  <h3>A new field arrives but disappears. Where do you look first?</h3>
  <div class="quiz-options">
    <button type="button" data-correct="true">The request handler</button>
    <button type="button">The color theme</button>
    <button type="button">The package lockfile</button>
  </div>
  <p class="quiz-feedback" aria-live="polite"></p>
</div>
```

## Component conversation

Use at least once per course. The script reveals messages in order and provides a replay button.

```html
<div class="component-chat" aria-label="Conversation between components">
  <div class="chat-message" data-speaker="UI">Here is the validated input.</div>
  <div class="chat-message" data-speaker="API">I will route it to the domain layer.</div>
  <button type="button" class="replay-chat">Replay conversation</button>
</div>
```

## Stepwise data flow

Use at least once per course. Put the human-readable explanation in `data-detail`.

```html
<div class="data-flow" aria-label="Request data flow">
  <button type="button" class="flow-step is-active" data-detail="The browser packages the user's input.">1. Browser</button>
  <button type="button" class="flow-step" data-detail="The handler validates shape and permissions.">2. Handler</button>
  <button type="button" class="flow-step" data-detail="The repository persists the accepted value.">3. Storage</button>
  <p class="flow-detail" aria-live="polite">The browser packages the user's input.</p>
</div>
```

## Other useful patterns

- `.actor-grid` containing `.actor-card` for responsibilities.
- `.callout` for a durable insight; add `.warning` for a failure boundary.
- `.path-chip` for real paths or commands.
- `<details>` for optional depth that should not interrupt the narrative.

Avoid inline scripts and styles. Do not use remote images, fonts, or libraries. The assembled file must work offline.

## Optional depth and active recall

Progressive kits embed a concept map and recall fields from `learning-kit.json` above the module narrative. Every concept has prerequisites, exact source anchors and a checkpoint with collapsed hints/answer/rubric. The frontend saves provisional responses and offers export; the separate tutor workflow assesses real answers. Keep deeper contracts and counterexamples in `<details>` when a beginner needs a lighter first pass. Avoid showing the answer before inviting prediction.

The existing 3–8-module contract remains a useful portable HTML format. A large project should produce a focused first kit rather than compress its entire source into eight superficial slides. Additional deep lessons/labs can be linked from the same learning path. Do not require one metaphor per module when the code and diagram already explain the concept well.
