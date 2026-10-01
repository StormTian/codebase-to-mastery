# Optional Agent runtime lens

Use only when the inspected project implements agents. These are investigation questions, not a required architecture or a claimed feature list.

| Dimension | Trace in source | Check understanding |
|---|---|---|
| Loop / termination | entry, step, continuation, budgets | What state ends the loop? Does it prove task success? |
| Run state / events | mutation owners, action vs observation | Which event proposes work, which records its result? |
| Session / persistence | IDs, write ordering, append/replace | What survives reload, and what remains external? |
| Checkpoint / resume | snapshot, pending action, replay | What could execute twice after a crash? |
| Tools / MCP | discovery, schema, dispatch, result handling | Where does model output become an actual side effect? |
| Memory / context | retrieval, injection, compression, isolation | Which evidence is lost or trusted across a boundary? |
| Auth / workspace / sandbox | principal, permission, paths, isolation | Which checks are in code and which depend on runtime? |
| Evaluation | artifact checks, scorers, trace capture | What distinguishes a successful run from useful output? |

Source maps must point to real mechanisms. If MCP or checkpointing is absent, write that rather than designing it into the explanation. Small labs might reconstruct a bounded state transition, tool-result pairing or reload invariant using deterministic fixtures. Label translated/simplified behavior and unsupported concurrency, authentication, external effects and production recovery semantics.
