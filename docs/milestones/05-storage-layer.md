# Milestone 5: Storage Layer

## Purpose

Build the production storage boundary for cassiopeia runtime state now that the
storage spike has passed and the core domain models exist. This milestone turns
the Turso/libSQL spike evidence into maintainable repository interfaces,
transaction handling, schema creation, and query operations that later runtime,
memory, permission, workflow, hook, subagent, gateway, TUI, and CLI work can
depend on.

The goal is not to build application behaviour. The goal is to contain SQL,
database lifecycle, retry handling, vector storage, and persistence details
inside `cassiopeia.storage` while the rest of cassiopeia talks to typed
repository ports and domain models.

## Scope

### In Scope

- Storage package layout under `src/cassiopeia/storage/`, including repository
  protocols, Turso/libSQL implementation modules, schema creation, and
  transaction helpers.
- Local database path resolution under the cassiopeia home layout, including
  `data/turso/cassiopeia.db`.
- Production table definitions for runtime state: sessions, messages, events,
  memories, memory embeddings, permission grants and audit records, workflow
  runs, subagent runs, and relationship/index tables needed by those records.
- Repository interfaces for appending and querying the runtime-state models
  defined in milestone 4.
- Event sink implementation for the milestone 3 emitter persistence boundary.
- Memory embedding persistence and semantic search using the Turso vector
  functions proven in milestone 2.
- Transaction helpers for multi-record operations, including rollback and
  bounded retry handling for retryable busy/conflict errors.
- Startup, close, reopen, and schema initialisation behaviour.
- Focused tests for schema creation, CRUD/query operations, transaction
  rollback, retry classification, vector search, and import boundaries.

### Out of Scope

- Agent runtime execution, model calls, context packet construction, or memory
  ranking beyond storage query primitives.
- Permission decision logic, prompt rendering, grant evaluation policy, or
  gateway interactions.
- Workflow graph execution, hook matching, node execution, or dispatch.
- CLI administration commands beyond small placeholders if needed to verify the
  storage package.
- Remote Turso Cloud sync, managed replicas, or multi-device sync.
- A second storage backend unless the Turso implementation uncovers a blocker.
- Full user-authored JSON definition loading; this milestone stores runtime
  state, not persona/workflow/workspace definition files.

## Deliverables

- `src/cassiopeia/storage/` package with clear module ownership, likely:

  ```text
  storage/
    __init__.py
    ports.py
    errors.py
    transactions.py
    libsql/
      __init__.py
      connection.py
      schema.py
      repositories.py
  ```

- Repository protocols for runtime records, with feature code depending on
  protocols rather than Turso-specific classes.
- Turso/libSQL implementation backed by `pyturso`.
- Schema creation or migration baseline for the 1.0 runtime database.
- Event sink implementation that can append `EventEnvelope` records.
- Memory embedding storage and vector search implementation with provider,
  model, vector dimension, stale flag, and creation timestamp metadata.
- Tests under `tests/storage/` covering persistence, query shape, rollback,
  retry classification, vector search, and package dependency direction.
- Documentation updates if the storage implementation changes the scope or
  project-structure assumptions.

## Tasks

- [x] Review `docs/02-storage-spike-report.md`,
      `docs/cassiopeia-1.0-scope.md`, and `docs/project-structure.md` before
      editing storage code.
- [x] Create the `cassiopeia.storage` package layout with repository ports,
      storage errors, transaction helpers, and Turso/libSQL implementation
      modules.
- [ ] Define repository protocols for sessions, messages, events, memories,
      permission grants/audit records, workflow runs, and subagent runs.
- [ ] Define storage-specific errors for connection failures, schema failures,
      not-found records, constraint violations, and retryable write conflicts.
- [ ] Implement local Turso/libSQL connection creation for a cassiopeia home,
      including database directory creation and `PRAGMA journal_mode = 'mvcc'`.
- [ ] Add schema creation for the runtime tables required by 1.0, keeping
      user-authored JSON definitions out of runtime storage.
- [ ] Implement event append/query operations and wire them to the milestone 3
      event sink protocol.
- [ ] Implement session and message persistence, including ordered session
      history reads.
- [ ] Implement memory record persistence, exposure/rejection state updates,
      embedding storage, stale embedding marking, and scoped vector search.
- [ ] Implement permission grant and audit record persistence without adding
      permission decision behaviour.
- [ ] Implement workflow run and subagent run summary persistence without adding
      workflow or subagent execution behaviour.
- [ ] Add transaction helpers for multi-record writes, rollback on failure, and
      bounded retry for retryable conflict or busy errors.
- [ ] Add tests that close and reopen the database and confirm persisted records
      remain readable.
- [ ] Add tests for relationship queries needed by later runtime work, such as
      sessions by workspace, messages by session, memories by scope/source, and
      recent workflow/subagent runs by session.
- [ ] Add tests for vector search using the same provider/model/dimension
      profile and for excluding stale embeddings.
- [ ] Add tests that storage implementation details do not leak into feature
      packages, app services, gateway code, or provider code.
- [ ] Update milestone 5 decisions and open questions as the storage boundary
      settles.

## Acceptance Criteria

- [ ] Runtime storage can create, close, reopen, and query a local Turso/libSQL
      database under a cassiopeia home directory.
- [ ] Repository protocols exist for all runtime records needed by later 1.0
      milestones, and feature packages do not import Turso implementation
      modules directly.
- [ ] Event emission can persist through the storage sink boundary.
- [ ] Sessions and messages can be appended and read back in deterministic
      order.
- [ ] Memory records can be stored, exposed, rejected, tagged, scoped, embedded,
      marked stale, and retrieved through vector search.
- [ ] Permission grants, permission audit records, workflow run summaries, and
      subagent run summaries can be persisted and queried by id or session where
      applicable.
- [ ] Multi-record writes have explicit transaction boundaries, rollback, and
      retry handling for retryable conflict or busy errors.
- [ ] SQL, Turso connection details, vector functions, and retry classification
      are contained inside the storage package.
- [ ] Full runtime, permission, workflow, hook, gateway, and CLI behaviour
      remains deferred to later milestones.
- [ ] `scripts/verify` passes, or any failure is documented with the remaining
      risk.

## Verification

```sh
scripts/verify
```

Optional focused checks during implementation:

```sh
uv run pytest tests/storage
uv run python scripts/storage_spike.py
```

The spike script remains useful as a regression reference, but production
storage tests should live under `tests/storage/`.

## Decisions

- Use local Turso/libSQL as the 1.0 runtime storage backend based on milestone 2.
- Keep runtime state in storage and user-authored definitions in JSON files.
- Store cross-feature relationships as ids, not nested object graphs.
- Depend on repository protocols outside the storage package.
- Keep SQL, vector search calls, connection setup, schema creation, transaction
  retry handling, and Turso-specific errors inside `cassiopeia.storage`.
- Treat migrations as a minimal baseline for now: create the 1.0 schema cleanly,
  then add a formal migration system only when versioned upgrades are needed.

## Open Questions

- Whether the first production implementation should include a formal schema
  version table or defer it until the first breaking schema change.
- Exact index strategy for common session, memory, event, permission, workflow,
  and subagent queries.
- Whether storage write APIs need idempotency keys for gateway retry and crash
  recovery scenarios.
- How much of memory ranking belongs in storage queries versus the later runtime
  and memory milestones.

## Notes

Use `docs/02-storage-spike-report.md` as the implementation evidence source.
The spike proved local persistence, MVCC, vector search, stale embeddings,
transaction-shaped writes, retry-aware concurrent writes, multiprocess
open/write/read, and repeat-open behaviour. This milestone should turn those
proof points into a small production boundary, not copy the spike wholesale.
