# Milestone 2: Storage Spike

## Purpose

Prove whether Turso is a reliable runtime storage backend for cassiopeia 1.0
before building the real storage layer. This milestone is a technical decision
point: it should produce enough evidence to either commit to Turso/libSQL for
1.0 or revise the storage plan while the technology is still isolated behind a
spike.

Turso is attractive because it keeps SQLite's local-first programming model
while adding features that matter for agent workflows: concurrent writes through
MVCC and `BEGIN CONCURRENT`, native vector storage/search, and a Python package
that can open local database files directly.

## Scope

### In Scope

- Local persistent Turso/libSQL storage from Python using `pyturso`.
- Basic records for workspaces, personas, sessions, events, memories,
  permissions, workflow runs, and subagent runs.
- Relationship queries between core records using relational tables and joins.
- Vector storage and semantic memory search.
- Multi-write reliability for normal event processing, including conflict
  detection and retry behaviour.
- Multi-session or multi-process access patterns that approximate two users or
  gateways using cassiopeia at the same time.
- Startup, shutdown, and dependency behaviour under `uv`.
- A clear pass/fail decision document.

### Out of Scope

- Production repository implementation.
- Full migration framework.
- Complete memory ranking.
- Agent runtime integration.
- Gateway integration.
- Long-term database administration tooling.
- Turso Cloud sync, remote replica, or managed service adoption decisions.

## Deliverables

- A spike script or small spike module that exercises local Turso/libSQL from
  Python.
- Sample schema/query definitions for the core runtime records.
- A written storage decision with pass/fail outcome and rationale.
- Notes on limitations, risks, and follow-up work for the real storage layer.

## Tasks

- [x] Confirm the existing `pyturso` dependency is sufficient, or request
      approval before adding any other database package or CLI.
- [x] Create/open a persistent embedded database under a temporary
      cassiopeia-style home path.
- [x] Enable and verify Turso MVCC with `PRAGMA journal_mode = 'mvcc'`.
- [x] Define sample tables for workspace, persona, session, event,
      memory, permission grant, workflow run, and subagent run.
- [x] Append and query session event history.
- [x] Model and query relationships between workspaces, sessions, personas, and
      memories.
- [x] Store memory embeddings with provider/model/dimension metadata.
- [x] Run semantic/vector search over memory records using Turso vector
      functions such as `vector32` and `vector_distance_cos`.
- [x] Test behaviour when the embedding profile changes and records are marked
      stale.
- [x] Test a realistic multi-write operation for one inbound message turn inside
      a transaction.
- [x] Test concurrent writers with `BEGIN CONCURRENT`, rollback, and retry logic
      for retryable conflict or busy errors.
- [x] Test multi-process open/write/read behaviour if the Python driver and
      local database mode support it cleanly.
- [x] Verify startup/shutdown and repeat-open behaviour.
- [x] Document whether Turso passes or fails for cassiopeia 1.0.

## Acceptance Criteria

- [x] Embedded persistent storage can be created, closed, reopened, and queried.
- [x] Session history can be appended and read back in order.
- [x] Relationship queries can answer basic questions such as which sessions
      belong to a workspace and which memories came from a session.
- [x] Vector search works for memory-like records with documented dimensionality,
      distance metric, and indexing limitations.
- [x] Concurrent writes are reliable enough for 1.0 under realistic local
      multi-session use, or the missing transaction/recovery behaviour is
      clearly documented.
- [x] Conflict handling has an explicit retry strategy, including which Turso
      errors are treated as retryable.
- [x] The spike ends with a written decision: use Turso for 1.0, use plain
      SQLite with a secondary vector strategy, or choose another storage backend.
- [x] `scripts/verify` passes, or any failure is documented with the remaining
      risk.

## Verification

```sh
uv run python scripts/storage_spike.py
scripts/verify
```

The spike intentionally lives under `scripts/` because it is disposable proof
code, not production CLI or storage-layer code.

## Decisions

- Decision: Turso/libSQL passes the storage spike for cassiopeia 1.0 local
  runtime storage, with documented limits. Use Turso/libSQL behind a
  storage/repository interface. See
  `docs/milestones/02-storage-spike-report.md`.
- Confirmed: the existing `pyturso>=0.6.1` dependency is sufficient to start
  the spike. It imports as `turso`, opens local database files, supports MVCC
  pragmas, and exposes vector functions in a local smoke test.
- Confirmed: `uv run python scripts/storage_spike.py` creates a temporary
  cassiopeia-style home, opens `data/turso/cassiopeia.db`, writes a probe row,
  closes the connection, reopens the database, and reads the probe row back.
- Confirmed: the spike enables `PRAGMA journal_mode = 'mvcc'`, closes that
  connection, reopens the database, and verifies that Turso still reports
  `mvcc` before running write/read probes.
- Confirmed: the spike can create sample runtime tables for workspaces,
  personas, sessions, events, memories, permission grants, workflow runs, and
  subagent runs; append/read ordered session events; and answer relationship
  queries for workspace sessions and session-sourced memories.
- Confirmed: the spike can store memory embeddings as Turso vector blobs with
  provider, model, dimension, and freshness metadata, then use
  `vector_distance_cos` against a `vector32` query to retrieve the expected
  memory.
- Confirmed: the spike can mark embeddings for an old provider/model/dimension
  profile stale, insert a fresh embedding for a new profile, and search only
  fresh embeddings for the selected profile.
- Confirmed: the spike can commit a realistic inbound-turn transaction that
  appends user and assistant events, writes a derived memory and embedding,
  records a permission grant, and records workflow and subagent runs as one
  transaction.
- Confirmed: the spike can run two concurrent writers on separate connections
  using `BEGIN CONCURRENT`; both writers commit their event rows, and the write
  path includes rollback plus bounded retry handling for busy/conflict-style
  errors. The current local run completed without needing a retry.
- Confirmed: the spike can launch separate Python child processes that open the
  same local database file, write distinct event rows, and have the parent
  process read those rows back. This proves multi-process open/write/read works
  for sequential child-process writes; it is not a concurrent multi-process
  stress test.
- Confirmed: the spike can repeatedly reopen the populated database, verify
  `mvcc` remains the active journal mode, and read a stable event count after
  startup/shutdown cycles.
- Decided: Turso/libSQL is the intended 1.0 local runtime storage backend unless
  later implementation work uncovers a blocker not represented in this spike.
- Pending: whether the storage layer needs recovery/idempotency patterns for
  partial multi-write failures.
- Pending: exact vector index shape and embedding metadata fields.
- Pending: whether the spike should keep using only local database files or also
  evaluate Turso Cloud sync after the local reliability question is answered.

## Open Questions

- Whether Turso beta reliability is sufficient for cassiopeia's 1.0 local-first
  runtime state.
- Whether cassiopeia needs a formal migration system in 1.0 or can defer it.
- Whether vector search should live entirely in Turso or behind a secondary
  abstraction.
- Whether the SQLite-compatible relational model is enough for cassiopeia's
  graph-like queries, or whether the storage interface needs explicit graph
  query helpers.

## Notes

This milestone should not grow into the production storage layer. Keep the code
small enough to throw away or rewrite cleanly after the storage decision is made.

Detailed decision report: `docs/milestones/02-storage-spike-report.md`.

Useful Turso documentation:

- Python connection guide: <https://docs.turso.tech/connect/python>
- Concurrent writes: <https://docs.turso.tech/tursodb/concurrent-writes>
- Vector search: <https://docs.turso.tech/guides/vector-search>
- Multi-process access: <https://docs.turso.tech/sql-reference/multiprocess-access>
