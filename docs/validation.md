# Validation and evidence boundaries

The public repository contains original tooling, fixtures and reproducible tests. Personal learner records and machine-specific run receipts are not distributed.

## Reproduce

Use Python 3.10+ from the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 tests/create_demo.py /tmp/codebase-to-mastery-demo-new
python3 scripts/check_milestone.py /tmp/codebase-to-mastery-demo-new --milestone contract --variant starter
python3 scripts/check_milestone.py /tmp/codebase-to-mastery-demo-new --milestone core --variant starter
python3 scripts/check_milestone.py /tmp/codebase-to-mastery-demo-new --milestone budget --variant starter
python3 scripts/check_milestone.py /tmp/codebase-to-mastery-demo-new --milestone core --variant reference
python3 scripts/check_milestone.py /tmp/codebase-to-mastery-demo-new --milestone budget --variant reference
```

Choose a fresh directory. Contract should pass; incomplete core/budget starters should report `EXPECTED_INCOMPLETE`; reference controls should pass. Import errors, syntax errors, assertion failures and timeouts are not accepted as expected incompleteness. The runner writes observed command receipts under the generated kit's `lab-runs/`.

## What the tests check

- Exact source excerpts, final HTML excerpt integrity and literal template-token preservation.
- Source-map fidelity, prerequisite graphs, path/symlink containment and stale generated materials.
- Safe line rebasing, source/teaching changes and downstream concept/lab review.
- Behavioral controls for original source, starter, reference and learner variants.
- Actual answer/assessment requirements, duplicate rejection, stale learning evidence and preserved history.
- Reviewer labels from multiple clients; a label is provenance, not authentication.
- Rejection of reference runs presented as learner mastery evidence.

The miniature runtime covers successful-prefix execution, failure without cursor advancement, JSON state restoration and a per-call budget. It has no real model, MCP, production persistence, concurrency or external-effect transaction guarantee.

## Client compatibility

The shared entrypoint uses the [Agent Skills specification](https://agentskills.io/specification): required `name` and `description`, relative resources, optional MIT/compatibility metadata. Python helpers do not import a Codex or Claude SDK. `agents/openai.yaml` is optional UI metadata.

Installation layout and helper execution can be tested separately from an agent's teaching decisions. A successful install is not an end-to-end evaluation of every client. Learner mastery and educational effectiveness require actual learner work and independent review.

The README installation conventions were checked on 2026-10-01 against [OpenAI](https://learn.chatgpt.com/docs/build-skills), [Claude Code](https://code.claude.com/docs/en/skills) and [Skills CLI](https://github.com/vercel-labs/skills) primary documentation. Client discovery paths can change; use the documentation for your installed version.

## Publication checks · 2026-10-01

| Check | Observed result |
| --- | --- |
| Tooling behavior on Python 3.14.7 | 26 tests passed |
| Codex Skill Creator structural validation | Passed |
| Skills CLI 1.7.0 installation from the local folder | Codex and Claude Code discovery files and full resource copies verified in a fresh temporary project |
| Helpers from both installed copies | Demo build, exact source validation, starter contract and reference core/budget controls passed |
| Incomplete starter core/budget | Both clients reported `EXPECTED_INCOMPLETE` as required |
| Revised offline UI at 1280×720 and 390×844 | Six-stage path, chapter navigation, J/K, quiz feedback, reduced motion, flow/chat, collapsed answers, persisted recall and unassessed JSON export checked in a browser |

These checks exercised installation and Python helpers. They did not evaluate an end-to-end teaching session in Claude Code or every compatible client. The [Checks workflow](https://github.com/StormTian/codebase-to-mastery/actions/workflows/checks.yml) repeats the behavioral tests and demo controls on Python 3.10 and 3.12; its run status is the current evidence for those versions.

## Release packaging · v1.0.0

The local suite now passes 30 tests, including four release checks: repeated builds are byte-identical on the same compression runtime; ZIP/tar payloads and file checksums match the committed revision even with uncommitted local changes; mismatched tags and symbolic-link resources are rejected; existing assets are preserved.

The [Release workflow](../.github/workflows/release.yml) runs the Python 3.10/3.12 suite and demo controls before building the tagged archives, then repeats the suite and demo controls from an extracted ZIP. Its published manifest and workflow run provide the source revision and actual publication evidence. See [releasing](releasing.md) for reproduction and checksum instructions.

## npm distribution · v1.1.0

The local suite passes 32 Python tests and six Node installer tests. New checks exercise actual offline `npm pack` output, committed-payload equality, version alignment, multi-client resource installation, custom targets, existing-folder preservation, dangling-symlink refusal and read-only preview/help/version behavior.

Run the Node tests with `npm test` or `node --test tests/npm/*.test.mjs`. The optional npm packaging test in the Python suite requires npm; without it the test reports a skip rather than claiming a pass. Full release CI includes both runtimes, builds the `.tgz` from a committed staging tree and executes `npm exec` against that actual file before publishing. This proves installation and fixture behavior, not learner mastery.

## Remote npm installation · 2026-10-02

On Node 22.23.0 / npm 12.0.2, direct installation from the public v1.1.0 GitHub tarball succeeded in a fresh project with an empty cache when using `npx --yes --allow-remote=all --package=URL codebase-to-mastery --agent codex claude-code`. All 45 installed resources per client matched the public manifest; both installed copies built the demo and passed all five positive/incomplete controls. The first attempt without the opt-in failed with `EALLOWREMOTE`, consistent with [npm 12's remote-source default](https://docs.npmjs.com/cli/v12/using-npm/config/#allow-remote). v1.1.1 updates the packaged instructions; the installer and teaching behavior are unchanged.

The v1.1.1 local suite passes 33 Python tests and six Node tests. The added check excludes the root distribution archive from Skill ZIP/tar files; the actual npm packaging test also includes a tracked root archive and verifies that it is excluded from the complete npm payload. Release CI compares the committed root download with the freshly built npm tarball before publishing, so a stale root package blocks the release.
