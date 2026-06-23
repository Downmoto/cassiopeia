# Milestone 2: Storage Spike

## Purpose

Prove whether embedded SurrealDB is a good runtime storage backend for
cassiopeia 1.0 before building the real storage layer. This milestone is a
technical decision point: it should produce enough evidence to either commit to
SurrealDB for 1.0 or revise the storage plan.

## Scope

### In Scope

- Embedded persistent SurrealDB from Python.
- Basic records for workspaces, personas, sessions, events, memories,
  permissions, workflow runs, and subagent runs.
- Graph relationships between core records.
- Vector storage and semantic memory search.
- Multi-write reliability for normal event processing.
- Startup, shutdown, and dependency behaviour under `uv`.
- A clear pass/fail decision document.

### Out of Scope

- Production repository implementation.
- Full migration framework.
- Complete memory ranking.
- Agent runtime integration.
- Gateway integration.
- Long-term database administration tooling.

## Deliverables

- A spike script or small spike module that exercises embedded SurrealDB.
- Sample schema/query definitions for the core runtime records.
- A written storage decision with pass/fail outcome and rationale.
- Notes on limitations, risks, and follow-up work for the real storage layer.

## Tasks

- [ ] Add the minimum dependency or local setup required to run embedded
      SurrealDB from Python, after approval if it adds a dependency.
- [ ] Create/open a persistent embedded database under a temporary
      cassiopeia-style home path.
- [ ] Define sample tables/records for workspace, persona, session, event,
      memory, permission grant, workflow run, and subagent run.
- [ ] Append and query session event history.
- [ ] Create graph relationships between workspaces, sessions, personas, and
      memories.
- [ ] Store memory embeddings with provider/model/dimension metadata.
- [ ] Run semantic/vector search over memory records.
- [ ] Test behaviour when the embedding profile changes and records are marked
      stale.
- [ ] Test a realistic multi-write operation for one inbound message turn.
- [ ] Verify startup/shutdown and repeat-open behaviour.
- [ ] Document whether embedded SurrealDB passes or fails for cassiopeia 1.0.

## Acceptance Criteria

- [ ] Embedded persistent storage can be created, closed, reopened, and queried.
- [ ] Session history can be appended and read back in order.
- [ ] Graph relationships can answer basic questions such as which sessions
      belong to a workspace and which memories came from a session.
- [ ] Vector search works for memory-like records, or the limitation is clearly
      documented.
- [ ] Multi-write event processing is reliable enough for 1.0, or the missing
      transaction/recovery behaviour is clearly documented.
- [ ] The spike ends with a written decision: use SurrealDB for 1.0, use
      SurrealDB only in server mode, or choose another storage backend.
- [ ] `scripts/verify` passes, or any failure is documented with the remaining
      risk.

## Verification

```sh
uv run cass storage spike
scripts/verify
```

If the spike remains outside the production CLI, document the exact command used
to run it here before closing the milestone.

## Decisions

- Pending: whether embedded SurrealDB is the 1.0 runtime storage backend.
- Pending: whether the storage layer needs recovery/idempotency patterns for
  partial multi-write failures.
- Pending: exact vector index shape and embedding metadata fields.

## Open Questions

- Whether SurrealDB embedded mode is sufficient or server mode is required.
- Whether cassiopeia needs a formal migration system in 1.0 or can defer it.
- Whether vector search should live entirely in SurrealDB or behind a secondary
  abstraction.

## Notes

This milestone should not grow into the production storage layer. Keep the code
small enough to throw away or rewrite cleanly after the storage decision is made.
