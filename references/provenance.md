# Provenance

This skill was originally designed for Codex on 2026-09-18 after reviewing Zara Zhang's public [codebase-to-course](https://github.com/zarazhangrui/codebase-to-course) repository at commit `ff8837ecf8e9f6ce9874ffa42e42633394a52a00`.

The upstream repository demonstrates a product-first curriculum for non-technical builders, exact code-to-English explanations, quizzes, component conversations, data-flow animations, and modular course assembly. No license file was present in the reviewed revision, so this skill does not copy its CSS, JavaScript, HTML templates, or prose. The offline template and Python tooling here are an original Codex-oriented implementation.

## Progressive learning upgrade · 2026-10-01

Reviewed the following primary skill files and pinned their revisions. User-pasted popularity counts were not used as quality evidence. Ideas were adapted independently; no upstream templates, code or prose were copied.

| Source | Inspected revision | License metadata | Used idea |
|---|---|---|---|
| [zarazhangrui/codebase-to-course](https://github.com/zarazhangrui/codebase-to-course/blob/ff8837ecf8e9f6ce9874ffa42e42633394a52a00/SKILL.md) | `ff8837ecf8e9f6ce9874ffa42e42633394a52a00` | No license identified at inspected revision | Accessible product-first HTML and source translation |
| [StrivingLee/repo-learning-kit](https://github.com/StrivingLee/repo-learning-kit/blob/1a8259fa7df03044551cd9a0bd5508719500e850/SKILL.md) | `1a8259fa7df03044551cd9a0bd5508719500e850` | MIT | Survey, purposeful reading, bounded rebuilding, milestone controls and source comparison |
| [Terryc21/tutorial-creator](https://github.com/Terryc21/tutorial-creator/blob/6d4b025615405ea1fc0c5e7c70b6fb36785ab0d0/skills/tutorial-creator/SKILL.md) | `6d4b025615405ea1fc0c5e7c70b6fb36785ab0d0` | Apache-2.0 | Lessons from actual project changes and explicit learning-state boundaries |
| [shuolsure/code-learning-tutorial-skill](https://github.com/shuolsure/code-learning-tutorial-skill/blob/4e473e3f4d6ac9cb99ca3305353522d1022c78a4/SKILL.md) | `4e473e3f4d6ac9cb99ca3305353522d1022c78a4` | MIT | Concept prerequisites, execution visuals and progressive interactive explanations |
| [ktaletsk/learn-codebase](https://github.com/ktaletsk/learn-codebase/blob/cbc0304609e76041f7f29b3ae9a1e3f1a16e07ad/SKILL.md) | `cbc0304609e76041f7f29b3ae9a1e3f1a16e07ad` | MIT | Prediction, focused Socratic questioning, active recall and a durable learning journal |

Access date: 2026-10-01. Source metadata and file hashes are preserved in [the inspiration-source record](../docs/inspiration-sources.json). The v2 kit differs from these inspirations: it preserves existing Codex courses, uses exact excerpt validation across source maps and HTML, keeps reference controls separate from learner mastery, and reports concept/lab impact on source updates. The fixture is a small original runtime; it does not establish external framework behavior.

Codex packaging guidance: [official skill structure and progressive resources](https://developers.openai.com/plugins/build/skills), accessed 2026-10-01. On 2026-10-01 the user requested a distinct name for the progressive learning design: `codebase-to-mastery` (源码掌握工坊). The earlier local name was `codebase-to-course`; upstream repository names above are unchanged. Instructions are concise at entry and mode-specific details are linked for selective reading.

## Portable distribution · 2026-10-01

The core uses the open [Agent Skills format](https://agentskills.io/specification), with optional Codex UI metadata. Installation guidance was checked against [OpenAI skills documentation](https://learn.chatgpt.com/docs/build-skills), [Claude Code skills documentation](https://code.claude.com/docs/en/skills), [anthropics/skills](https://github.com/anthropics/skills) and [vercel-labs/skills](https://github.com/vercel-labs/skills). README layout and installation examples are written independently. MIT applies to this repository’s original code and assets, not to source material from projects taught with the skill.
