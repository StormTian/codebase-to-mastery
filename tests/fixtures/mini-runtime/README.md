# Mini runtime teaching fixture

Original StormPro test input, created 2026-10-01. `runtime.py` is the inspected source for the v2 learning-kit demonstration. No network, model, MCP, credentials or disk persistence is implemented.

Contract: a fixed plan selects a named deterministic tool, a successful result is appended before the cursor advances, failures leave the failed step uncommitted, and a JSON checkpoint restores the committed prefix. A per-call budget pauses at the next uncommitted step.

Boundaries: the checkpoint contains no plan fingerprint; external side effects are not rolled back, tool execution and checkpoint saving are not atomic, concurrency is absent, and a caller can mutate State. `done` describes plan exhaustion; it does not check the usefulness of results.

Run `python3 tests/create_demo.py <new-output-directory>` from the skill root to build a learning kit. The tooling tests run the same behavioral cases against this source, an incomplete starter and an independently written reference. This fixture demonstrates the tooling workflow; it is not evidence about any existing Agent framework.
