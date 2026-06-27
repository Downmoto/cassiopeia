# Milestone 2 Storage Spike Report

## Decision

Turso/libSQL passes the milestone 2 storage spike for cassiopeia 1.0 local
runtime storage, with documented limits.

The recommended next step is to use local Turso/libSQL as the 1.0 runtime
storage backend behind a storage/repository interface. Production code should
keep SQL, vector search, transaction boundaries, retry handling, and
database-specific details inside that storage implementation.

This decision does not include Turso Cloud sync, remote replicas, or managed
service features. The spike tested local file-backed Turso/libSQL only.

## Evidence

The spike lives at `scripts/storage_spike.py` so it remains disposable proof
code rather than production storage code.

Run it with:

```sh
uv run python scripts/storage_spike.py
```

Expected output shape:

```text
journal_mode: mvcc
probe: open-reopen-ok
sample_tables: 9
session_events: user: hello cassiopeia, assistant: hello arad
workspace_sessions: session-main
session_memories: prefers Canadian spelling, prefers American spelling
embedding_profile: test-embedding-provider/test-memory-3-small/3/fresh
vector_match: prefers Canadian spelling
vector_distance: <driver-provided numeric distance>
stale_embedding_profile: test-embedding-provider/test-memory-3-small/3/stale
refreshed_embedding_profile: test-embedding-provider/test-memory-4-small/4/fresh
refreshed_vector_match: prefers Canadian spelling
transaction_writes: events:2, memories:1, embeddings:1, grants:1, workflow_runs:1, subagent_runs:1
concurrent_writes: writers:2, events:2, retryable_errors:<n>, attempts:<n>
multiprocess_writes: processes:2, events:2
repeat_open: opens:3, journal_mode:mvcc, events:8
```

`scripts/verify` passed after the spike was completed.

## What Passed

- `pyturso>=0.6.1` imports as `turso` and opens a local database file.
- Runtime state can live under `data/turso/cassiopeia.db` in a
  cassiopeia-style home.
- `PRAGMA journal_mode = 'mvcc'` can be enabled, closed, reopened, and verified
  from a new connection.
- Runtime-shaped tables can represent workspaces, personas, sessions, events,
  memories, memory embeddings, permission grants, workflow runs, and subagent
  runs.
- Session events can be appended and queried in sequence order.
- Relationship queries can answer workspace-to-session and session-to-memory
  questions through joins.
- Memory embeddings can be stored as Turso vector blobs with provider, model,
  dimension, and freshness metadata.
- `vector_distance_cos` and `vector32` can retrieve the expected memory.
- Old embedding profiles can be marked stale and excluded from search.
- A realistic inbound turn can be committed as one transaction across multiple
  tables.
- Two concurrent thread-backed writers can use separate connections and
  `BEGIN CONCURRENT` to commit distinct event rows.
- The concurrent write path includes rollback and bounded retry handling for
  busy/conflict-style errors.
- Separate Python child processes can open the same local database file, write
  rows, and have the parent read those rows back.
- Repeated open/read/close cycles preserve readable state and keep `mvcc` as the
  journal mode.

## Code Walkthrough

### Entry Point

`main()` has two modes.

Normal mode runs the full spike and prints one line per proof point. The test at
`tests/test_storage_spike_script.py` runs the script as a subprocess and checks
those output lines.

Worker mode is used only by the multi-process probe:

```sh
python scripts/storage_spike.py --multiprocess-worker <db-path> <event-id> <sequence>
```

That lets the parent process prove separate Python processes can open and write
to the same local database file.

### Result Types

`StorageOpenProbeResult` carries every visible proof point, including the
database path, journal mode, session history result, relationship query result,
vector result, transaction result, concurrent writer summary, multi-process
summary, and repeat-open summary.

`VectorSearchMatch` stores a memory content string and numeric distance.

`ConcurrentWriterResult` stores each concurrent writer's id, number of attempts,
and number of retryable errors observed.

### Database Creation and MVCC

`run_open_reopen_probe()` creates a temporary cassiopeia-style home with
`initialise_home()` and uses:

```text
<home>/data/turso/cassiopeia.db
```

`_enable_mvcc()` runs:

```sql
PRAGMA journal_mode = 'mvcc'
```

It closes that connection and calls `_read_journal_mode()` on a fresh connection.
That proves MVCC survives close/reopen instead of only proving the setter call
returned `mvcc`.

### Persistence Probe

`_write_probe_row()` creates `storage_spike_probe` and writes one row.
`_read_probe_row()` opens a separate connection and reads the row back. This is
the smallest persistence check before the script creates the larger sample
schema.

### Sample Schema

`_create_sample_schema()` creates nine tables:

- `workspaces`
- `personas`
- `sessions`
- `events`
- `memories`
- `memory_embeddings`
- `permission_grants`
- `workflow_runs`
- `subagent_runs`

This is a representative schema for spike evidence, not a final production
schema.

`memory_embeddings` is separate from `memories` so a memory can have multiple
embedding profiles over time. The table stores provider, model, dimension,
vector blob, freshness, and creation time.

### Sample Data

`_seed_sample_records()` inserts one workspace, one persona, one session, two
events, two memories, two embeddings, one permission grant, one workflow run,
and one subagent run.

The initial memories are:

- `prefers Canadian spelling`
- `prefers American spelling`

They intentionally use different vectors so the vector search proof can check
ranking.

### Session History

`_read_session_events()` selects events for `session-main` ordered by
`sequence`. The expected result is:

```text
user: hello cassiopeia
assistant: hello arad
```

This proves ordered session history reads.

### Relationship Queries

`_read_workspace_sessions()` joins sessions to workspaces and proves a workspace
can find its sessions.

`_read_session_memories()` joins memories to sessions through
`source_session_id` and proves a session can find memories derived from it.

The original storage plan referred to graph relationships while SurrealDB was
the candidate. Under Turso, the equivalent proof is that relational joins can
answer the graph-like questions cassiopeia needs for 1.0.

### Embedding Metadata and Vector Search

`_read_embedding_profile()` reads provider, model, dimension, and `is_stale`,
then formats the result as:

```text
provider/model/dimension/freshness
```

`_search_memory_embeddings()` filters by provider, model, dimension, and
`is_stale = 0`, then ranks rows with:

```sql
vector_distance_cos(memory_embeddings.embedding, vector32(?))
```

The spike requires the expected memory to rank first and the distance to be a
finite number. It does not require an exact numeric distance because the exact
value is driver/database implementation detail.

### Embedding Profile Changes

`_mark_embedding_profile_stale()` marks all embeddings for an old
provider/model/dimension profile stale.

`_insert_refreshed_embedding()` inserts a fresh four-dimensional embedding for a
new profile. Search is then scoped to the new profile and stale rows are
excluded.

### Inbound Turn Transaction

`_write_inbound_turn_transaction()` models a realistic inbound message turn.

Inside one transaction it writes:

- user event
- assistant event
- derived memory
- memory embedding
- permission grant
- workflow run
- subagent run

The function uses `BEGIN`, commits on success, and rolls back on failure.
`_read_inbound_turn_writes()` verifies that all expected rows exist after the
commit.

### Concurrent Writers

`_run_concurrent_writer_probe()` starts two thread-backed writers. Each writer
gets its own connection and writes one event with:

```sql
BEGIN CONCURRENT
```

The writers wait on a barrier during the first attempt so their work overlaps.
`_write_concurrent_event_with_retry()` rolls back on errors and retries when the
error message contains retryable markers such as `busy`, `locked`, `conflict`,
`concurrent`, `snapshot`, or `retry`.

The local run completed without needing a retry, but the write path has bounded
retry handling.

### Multi-Process Probe

`_run_multiprocess_probe()` launches two child Python processes. Each child runs
the same script in worker mode and writes one event. The parent then opens the
database and verifies both rows exist.

This proves sequential multi-process open/write/read behaviour. It is not a
concurrent multi-process stress test.

### Repeat Open

`_run_repeat_open_probe()` opens and closes the populated database three times.
Each open verifies that:

- `PRAGMA journal_mode` still reports `mvcc`
- the total event count is stable

The expected summary is:

```text
repeat_open: opens:3, journal_mode:mvcc, events:8
```

## Limitations

- The schema is representative, not final.
- The migration strategy is still undecided.
- The local concurrent writer run did not force a retry; it proved overlapping
  `BEGIN CONCURRENT` writers can commit and that retry code exists.
- Multi-process testing used sequential child-process writes, not simultaneous
  multi-process stress.
- Vector distance values should not be treated as stable contracts.
- Turso Cloud sync and remote replica behaviour were not evaluated.
- Crash recovery, backup, file corruption recovery, and long-running durability
  were not evaluated.
- The script opens many short-lived connections to prove persistence and reopen
  behaviour. Production code should use intentional connection and transaction
  management.
- Retryable error classification currently uses message markers. Production
  code should prefer typed driver errors or stable error codes if available.

## Follow-Up Work

For the production storage layer:

- define repository interfaces before exposing Turso details to runtime code
- keep SQL isolated under the storage implementation
- add explicit transaction helpers for multi-write turns
- define bounded retry policy for busy/conflict errors
- inspect driver exception types and document retryable errors
- define a migration plan
- keep embedding profile metadata in the schema
- filter vector search by provider, model, dimension, scope, and freshness
- avoid relying on exact vector distance numbers
- add rollback and failed multi-write tests
- decide whether concurrent multi-process stress testing is required before
  release hardening

## Final Recommendation

Use Turso/libSQL for cassiopeia 1.0 local runtime storage, behind a
storage/repository interface.

The spike provides enough evidence to continue with Turso for local sessions,
event history, memory, relationship queries, vector search, and normal
multi-write processing. The remaining risks are manageable if the production
storage layer keeps transaction boundaries, retry handling, migration discipline,
and database-specific details inside one implementation boundary.
