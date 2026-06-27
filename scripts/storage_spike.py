"""Throwaway Turso storage spike.

Run with:

    uv run python scripts/storage_spike.py
"""

import math
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier, BrokenBarrierError
from typing import Any

from cassiopeia.home import initialise_home


@dataclass(frozen=True)
class StorageOpenProbeResult:
    home: Path
    database_path: Path
    probe_value: str
    journal_mode: str
    table_count: int
    session_events: tuple[str, ...]
    workspace_sessions: tuple[str, ...]
    session_memories: tuple[str, ...]
    embedding_profile: str
    vector_match: str
    vector_distance: float
    stale_embedding_profile: str
    refreshed_embedding_profile: str
    refreshed_vector_match: str
    transaction_writes: tuple[str, ...]
    concurrent_writes: str
    multiprocess_writes: str
    repeat_open: str


@dataclass(frozen=True)
class VectorSearchMatch:
    content: str
    distance: float


@dataclass(frozen=True)
class ConcurrentWriterResult:
    writer_id: str
    attempts: int
    retryable_errors: int


def main() -> None:
    if len(sys.argv) == 5 and sys.argv[1] == "--multiprocess-worker":
        _run_multiprocess_worker(
            Path(sys.argv[2]),
            event_id=sys.argv[3],
            sequence=int(sys.argv[4]),
        )
        return

    result = run_open_reopen_probe()
    print(f"home: {result.home}")
    print(f"database: {result.database_path}")
    print(f"journal_mode: {result.journal_mode}")
    print(f"probe: {result.probe_value}")
    print(f"sample_tables: {result.table_count}")
    print(f"session_events: {', '.join(result.session_events)}")
    print(f"workspace_sessions: {', '.join(result.workspace_sessions)}")
    print(f"session_memories: {', '.join(result.session_memories)}")
    print(f"embedding_profile: {result.embedding_profile}")
    print(f"vector_match: {result.vector_match}")
    print(f"vector_distance: {result.vector_distance:.6f}")
    print(f"stale_embedding_profile: {result.stale_embedding_profile}")
    print(f"refreshed_embedding_profile: {result.refreshed_embedding_profile}")
    print(f"refreshed_vector_match: {result.refreshed_vector_match}")
    print(f"transaction_writes: {', '.join(result.transaction_writes)}")
    print(f"concurrent_writes: {result.concurrent_writes}")
    print(f"multiprocess_writes: {result.multiprocess_writes}")
    print(f"repeat_open: {result.repeat_open}")


def run_open_reopen_probe() -> StorageOpenProbeResult:
    with TemporaryDirectory(prefix="cassiopeia-storage-spike-") as temporary_home:
        home = initialise_home(Path(temporary_home) / "home")
        database_path = home / "data" / "turso" / "cassiopeia.db"
        database_path.parent.mkdir(parents=True, exist_ok=True)

        journal_mode = _enable_mvcc(database_path)
        if journal_mode != "mvcc":
            raise RuntimeError(f"storage spike journal mode is {journal_mode!r}, expected 'mvcc'")

        probe_value = "open-reopen-ok"
        _write_probe_row(database_path, probe_value)
        reopened_value = _read_probe_row(database_path)

        if reopened_value != probe_value:
            raise RuntimeError(
                f"storage spike probe returned {reopened_value!r}, expected {probe_value!r}"
            )

        _create_sample_schema(database_path)
        _seed_sample_records(database_path)
        table_count = _count_sample_tables(database_path)
        session_events = _read_session_events(database_path, "session-main")
        workspace_sessions = _read_workspace_sessions(database_path, "workspace-main")
        session_memories = _read_session_memories(database_path, "session-main")
        embedding_profile = _read_embedding_profile(database_path, "memory-001")
        vector_matches = _search_memory_embeddings(database_path)
        vector_match = vector_matches[0]
        _mark_embedding_profile_stale(
            database_path,
            provider="test-embedding-provider",
            model="test-memory-3-small",
            dimension=3,
        )
        _insert_refreshed_embedding(database_path)
        stale_embedding_profile = _read_embedding_profile(
            database_path,
            "memory-001",
            provider="test-embedding-provider",
            model="test-memory-3-small",
            dimension=3,
        )
        refreshed_embedding_profile = _read_embedding_profile(
            database_path,
            "memory-001",
            provider="test-embedding-provider",
            model="test-memory-4-small",
            dimension=4,
        )
        refreshed_vector_matches = _search_memory_embeddings(
            database_path,
            provider="test-embedding-provider",
            model="test-memory-4-small",
            dimension=4,
            query_vector="[0.1, 0.2, 0.3, 0.4]",
        )
        refreshed_vector_match = refreshed_vector_matches[0]
        _write_inbound_turn_transaction(database_path)
        transaction_writes = _read_inbound_turn_writes(database_path)
        concurrent_writes = _run_concurrent_writer_probe(database_path)
        multiprocess_writes = _run_multiprocess_probe(database_path)
        repeat_open = _run_repeat_open_probe(database_path)

        if session_events != ("user: hello cassiopeia", "assistant: hello arad"):
            raise RuntimeError(
                f"session event probe returned unexpected events: {session_events!r}"
            )

        if workspace_sessions != ("session-main",):
            raise RuntimeError(
                f"workspace relationship probe returned unexpected sessions: {workspace_sessions!r}"
            )

        expected_session_memories = (
            "prefers Canadian spelling",
            "prefers American spelling",
        )
        if session_memories != expected_session_memories:
            raise RuntimeError(
                f"session memory probe returned unexpected memories: {session_memories!r}"
            )

        expected_profile = "test-embedding-provider/test-memory-3-small/3/fresh"
        if embedding_profile != expected_profile:
            raise RuntimeError(
                f"embedding metadata probe returned {embedding_profile!r}, "
                f"expected {expected_profile!r}"
            )

        if vector_match.content != "prefers Canadian spelling":
            raise RuntimeError(
                f"vector search probe returned {vector_match.content!r} as the nearest memory"
            )

        expected_stale_profile = "test-embedding-provider/test-memory-3-small/3/stale"
        if stale_embedding_profile != expected_stale_profile:
            raise RuntimeError(
                f"stale embedding probe returned {stale_embedding_profile!r}, "
                f"expected {expected_stale_profile!r}"
            )

        expected_refreshed_profile = "test-embedding-provider/test-memory-4-small/4/fresh"
        if refreshed_embedding_profile != expected_refreshed_profile:
            raise RuntimeError(
                f"refreshed embedding probe returned {refreshed_embedding_profile!r}, "
                f"expected {expected_refreshed_profile!r}"
            )

        if refreshed_vector_match.content != "prefers Canadian spelling":
            raise RuntimeError(
                "refreshed vector search probe returned "
                f"{refreshed_vector_match.content!r} as the nearest memory"
            )

        expected_transaction_writes = (
            "events:2",
            "memories:1",
            "embeddings:1",
            "grants:1",
            "workflow_runs:1",
            "subagent_runs:1",
        )
        if transaction_writes != expected_transaction_writes:
            raise RuntimeError(
                f"turn transaction probe returned {transaction_writes!r}, "
                f"expected {expected_transaction_writes!r}"
            )

        if not concurrent_writes.startswith("writers:2, events:2, retryable_errors:"):
            raise RuntimeError(
                f"concurrent writer probe returned unexpected summary: {concurrent_writes!r}"
            )

        if multiprocess_writes != "processes:2, events:2":
            raise RuntimeError(
                f"multi-process probe returned unexpected summary: {multiprocess_writes!r}"
            )

        if repeat_open != "opens:3, journal_mode:mvcc, events:8":
            raise RuntimeError(f"repeat-open probe returned unexpected summary: {repeat_open!r}")

        return StorageOpenProbeResult(
            home=home,
            database_path=database_path,
            probe_value=reopened_value,
            journal_mode=journal_mode,
            table_count=table_count,
            session_events=session_events,
            workspace_sessions=workspace_sessions,
            session_memories=session_memories,
            embedding_profile=embedding_profile,
            vector_match=vector_match.content,
            vector_distance=vector_match.distance,
            stale_embedding_profile=stale_embedding_profile,
            refreshed_embedding_profile=refreshed_embedding_profile,
            refreshed_vector_match=refreshed_vector_match.content,
            transaction_writes=transaction_writes,
            concurrent_writes=concurrent_writes,
            multiprocess_writes=multiprocess_writes,
            repeat_open=repeat_open,
        )


def _connect(database_path: Path) -> Any:
    turso = import_module("turso")
    return turso.connect(str(database_path))


def _enable_mvcc(database_path: Path) -> str:
    connection = _connect(database_path)
    try:
        row = connection.execute("PRAGMA journal_mode = 'mvcc'").fetchone()
        connection.commit()
    finally:
        connection.close()

    if row is None:
        raise RuntimeError("storage spike could not read journal mode")

    set_journal_mode = str(row[0]).lower()
    if set_journal_mode != "mvcc":
        return set_journal_mode

    return _read_journal_mode(database_path)


def _read_journal_mode(database_path: Path) -> str:
    connection = _connect(database_path)
    try:
        row = connection.execute("PRAGMA journal_mode").fetchone()
    finally:
        connection.close()

    if row is None:
        raise RuntimeError("storage spike could not read reopened journal mode")

    return str(row[0]).lower()


def _write_probe_row(database_path: Path, probe_value: str) -> None:
    connection = _connect(database_path)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS storage_spike_probe (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                value TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO storage_spike_probe (id, value)
            VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET value = excluded.value
            """,
            (probe_value,),
        )
        connection.commit()
    finally:
        connection.close()


def _read_probe_row(database_path: Path) -> str:
    connection = _connect(database_path)
    try:
        row = connection.execute("SELECT value FROM storage_spike_probe WHERE id = 1").fetchone()
    finally:
        connection.close()

    if row is None:
        raise RuntimeError("storage spike probe row was not persisted")

    return str(row[0])


def _create_sample_schema(database_path: Path) -> None:
    connection = _connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS workspaces (
                id TEXT PRIMARY KEY,
                slug TEXT NOT NULL UNIQUE,
                root_path TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS personas (
                id TEXT PRIMARY KEY,
                slug TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL REFERENCES workspaces(id),
                persona_id TEXT NOT NULL REFERENCES personas(id),
                title TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                sequence INTEGER NOT NULL,
                actor TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(session_id, sequence)
            );

            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                workspace_id TEXT REFERENCES workspaces(id),
                persona_id TEXT REFERENCES personas(id),
                source_session_id TEXT REFERENCES sessions(id),
                scope TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memory_embeddings (
                id TEXT PRIMARY KEY,
                memory_id TEXT NOT NULL REFERENCES memories(id),
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                dimension INTEGER NOT NULL,
                embedding BLOB NOT NULL,
                is_stale INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(memory_id, provider, model, dimension)
            );

            CREATE TABLE IF NOT EXISTS permission_grants (
                id TEXT PRIMARY KEY,
                session_id TEXT REFERENCES sessions(id),
                ring INTEGER NOT NULL,
                action TEXT NOT NULL,
                decision TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS workflow_runs (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL REFERENCES workspaces(id),
                session_id TEXT REFERENCES sessions(id),
                workflow_slug TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS subagent_runs (
                id TEXT PRIMARY KEY,
                parent_session_id TEXT NOT NULL REFERENCES sessions(id),
                persona_id TEXT REFERENCES personas(id),
                task TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        connection.commit()
    finally:
        connection.close()


def _seed_sample_records(database_path: Path) -> None:
    connection = _connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            INSERT INTO workspaces (id, slug, root_path, created_at)
            VALUES ('workspace-main', 'cassiopeia', '/tmp/cassiopeia', '2026-06-25T00:00:00Z');

            INSERT INTO personas (id, slug, name, created_at)
            VALUES ('persona-manager', 'workspace-manager', 'Workspace Manager',
                    '2026-06-25T00:00:01Z');

            INSERT INTO sessions (id, workspace_id, persona_id, title, created_at)
            VALUES ('session-main', 'workspace-main', 'persona-manager',
                    'Spike session', '2026-06-25T00:00:02Z');

            INSERT INTO events (id, session_id, sequence, actor, content, created_at)
            VALUES
                ('event-001', 'session-main', 1, 'user', 'hello cassiopeia',
                 '2026-06-25T00:00:03Z'),
                ('event-002', 'session-main', 2, 'assistant', 'hello arad',
                 '2026-06-25T00:00:04Z');

            INSERT INTO memories (id, workspace_id, persona_id, source_session_id,
                                  scope, content, created_at)
            VALUES ('memory-001', 'workspace-main', 'persona-manager', 'session-main',
                    'workspace', 'prefers Canadian spelling', '2026-06-25T00:00:05Z');

            INSERT INTO memories (id, workspace_id, persona_id, source_session_id,
                                  scope, content, created_at)
            VALUES ('memory-002', 'workspace-main', 'persona-manager', 'session-main',
                    'workspace', 'prefers American spelling', '2026-06-25T00:00:05Z');

            INSERT INTO memory_embeddings (id, memory_id, provider, model, dimension,
                                           embedding, is_stale, created_at)
            VALUES
                ('embedding-001', 'memory-001', 'test-embedding-provider',
                 'test-memory-3-small', 3,
                 vector32('[0.1, 0.2, 0.3]'), 0, '2026-06-25T00:00:05Z'),
                ('embedding-002', 'memory-002', 'test-embedding-provider',
                 'test-memory-3-small', 3,
                 vector32('[0.8, 0.1, 0.1]'), 0, '2026-06-25T00:00:05Z');

            INSERT INTO permission_grants (id, session_id, ring, action, decision, created_at)
            VALUES ('grant-001', 'session-main', 1, 'read workspace metadata',
                    'approved', '2026-06-25T00:00:06Z');

            INSERT INTO workflow_runs (id, workspace_id, session_id, workflow_slug,
                                       status, created_at)
            VALUES ('workflow-run-001', 'workspace-main', 'session-main',
                    'summarize-thread', 'completed', '2026-06-25T00:00:07Z');

            INSERT INTO subagent_runs (id, parent_session_id, persona_id, task,
                                       status, created_at)
            VALUES ('subagent-run-001', 'session-main', 'persona-manager',
                    'review storage spike output', 'completed', '2026-06-25T00:00:08Z');
            """
        )
        connection.commit()
    finally:
        connection.close()


def _count_sample_tables(database_path: Path) -> int:
    connection = _connect(database_path)
    try:
        row = connection.execute(
            """
            SELECT count(*)
            FROM sqlite_schema
            WHERE type = 'table'
              AND name IN (
                  'workspaces',
                  'personas',
                  'sessions',
                  'events',
                  'memories',
                  'permission_grants',
                  'workflow_runs',
                  'subagent_runs',
                  'memory_embeddings'
              )
            """
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        raise RuntimeError("storage spike could not count sample tables")

    return int(row[0])


def _read_session_events(database_path: Path, session_id: str) -> tuple[str, ...]:
    connection = _connect(database_path)
    try:
        rows = connection.execute(
            """
            SELECT actor, content
            FROM events
            WHERE session_id = ?
            ORDER BY sequence
            """,
            (session_id,),
        ).fetchall()
    finally:
        connection.close()

    return tuple(f"{row[0]}: {row[1]}" for row in rows)


def _read_workspace_sessions(database_path: Path, workspace_id: str) -> tuple[str, ...]:
    connection = _connect(database_path)
    try:
        rows = connection.execute(
            """
            SELECT sessions.id
            FROM sessions
            JOIN workspaces ON workspaces.id = sessions.workspace_id
            WHERE workspaces.id = ?
            ORDER BY sessions.created_at
            """,
            (workspace_id,),
        ).fetchall()
    finally:
        connection.close()

    return tuple(str(row[0]) for row in rows)


def _read_session_memories(database_path: Path, session_id: str) -> tuple[str, ...]:
    connection = _connect(database_path)
    try:
        rows = connection.execute(
            """
            SELECT memories.content
            FROM memories
            JOIN sessions ON sessions.id = memories.source_session_id
            WHERE sessions.id = ?
            ORDER BY memories.created_at, memories.id
            """,
            (session_id,),
        ).fetchall()
    finally:
        connection.close()

    return tuple(str(row[0]) for row in rows)


def _read_embedding_profile(
    database_path: Path,
    memory_id: str,
    *,
    provider: str = "test-embedding-provider",
    model: str = "test-memory-3-small",
    dimension: int = 3,
) -> str:
    connection = _connect(database_path)
    try:
        row = connection.execute(
            """
            SELECT provider, model, dimension, is_stale
            FROM memory_embeddings
            WHERE memory_id = ?
              AND provider = ?
              AND model = ?
              AND dimension = ?
            """,
            (memory_id, provider, model, dimension),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        raise RuntimeError(f"storage spike could not find embedding for {memory_id!r}")

    freshness = "stale" if int(row[3]) else "fresh"
    return f"{row[0]}/{row[1]}/{row[2]}/{freshness}"


def _mark_embedding_profile_stale(
    database_path: Path,
    *,
    provider: str,
    model: str,
    dimension: int,
) -> None:
    connection = _connect(database_path)
    try:
        connection.execute(
            """
            UPDATE memory_embeddings
            SET is_stale = 1
            WHERE provider = ?
              AND model = ?
              AND dimension = ?
            """,
            (provider, model, dimension),
        )
        connection.commit()
    finally:
        connection.close()


def _insert_refreshed_embedding(database_path: Path) -> None:
    connection = _connect(database_path)
    try:
        connection.execute(
            """
            INSERT INTO memory_embeddings (id, memory_id, provider, model, dimension,
                                           embedding, is_stale, created_at)
            VALUES (?, ?, ?, ?, ?, vector32(?), ?, ?)
            """,
            (
                "embedding-003",
                "memory-001",
                "test-embedding-provider",
                "test-memory-4-small",
                4,
                "[0.1, 0.2, 0.3, 0.4]",
                0,
                "2026-06-25T00:01:00Z",
            ),
        )
        connection.commit()
    finally:
        connection.close()


def _search_memory_embeddings(
    database_path: Path,
    *,
    provider: str = "test-embedding-provider",
    model: str = "test-memory-3-small",
    dimension: int = 3,
    query_vector: str = "[0.1, 0.2, 0.3]",
) -> tuple[VectorSearchMatch, ...]:
    connection = _connect(database_path)
    try:
        rows = connection.execute(
            """
            SELECT
                memories.content,
                vector_distance_cos(
                    memory_embeddings.embedding,
                    vector32(?)
                ) AS distance
            FROM memory_embeddings
            JOIN memories ON memories.id = memory_embeddings.memory_id
            WHERE memory_embeddings.provider = ?
              AND memory_embeddings.model = ?
              AND memory_embeddings.dimension = ?
              AND memory_embeddings.is_stale = 0
            ORDER BY distance
            LIMIT 2
            """,
            (query_vector, provider, model, dimension),
        ).fetchall()
    finally:
        connection.close()

    if not rows:
        raise RuntimeError("storage spike vector search returned no rows")

    matches = tuple(VectorSearchMatch(str(row[0]), float(row[1])) for row in rows)
    for match in matches:
        if not math.isfinite(match.distance):
            raise RuntimeError(f"vector search returned non-finite distance: {match!r}")

    return matches


def _write_inbound_turn_transaction(database_path: Path) -> None:
    connection = _connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN")
        connection.execute(
            """
            INSERT INTO events (id, session_id, sequence, actor, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "event-003",
                "session-main",
                3,
                "user",
                "remember that I prefer local-first tools",
                "2026-06-25T00:02:00Z",
            ),
        )
        connection.execute(
            """
            INSERT INTO events (id, session_id, sequence, actor, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "event-004",
                "session-main",
                4,
                "assistant",
                "noted your local-first preference",
                "2026-06-25T00:02:01Z",
            ),
        )
        connection.execute(
            """
            INSERT INTO memories (id, workspace_id, persona_id, source_session_id,
                                  scope, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "memory-003",
                "workspace-main",
                "persona-manager",
                "session-main",
                "workspace",
                "prefers local-first tools",
                "2026-06-25T00:02:02Z",
            ),
        )
        connection.execute(
            """
            INSERT INTO memory_embeddings (id, memory_id, provider, model, dimension,
                                           embedding, is_stale, created_at)
            VALUES (?, ?, ?, ?, ?, vector32(?), ?, ?)
            """,
            (
                "embedding-004",
                "memory-003",
                "test-embedding-provider",
                "test-memory-4-small",
                4,
                "[0.2, 0.3, 0.4, 0.5]",
                0,
                "2026-06-25T00:02:02Z",
            ),
        )
        connection.execute(
            """
            INSERT INTO permission_grants (id, session_id, ring, action, decision, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "grant-002",
                "session-main",
                1,
                "write workspace memory",
                "approved",
                "2026-06-25T00:02:03Z",
            ),
        )
        connection.execute(
            """
            INSERT INTO workflow_runs (id, workspace_id, session_id, workflow_slug,
                                       status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "workflow-run-002",
                "workspace-main",
                "session-main",
                "extract-memory",
                "completed",
                "2026-06-25T00:02:04Z",
            ),
        )
        connection.execute(
            """
            INSERT INTO subagent_runs (id, parent_session_id, persona_id, task,
                                       status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "subagent-run-002",
                "session-main",
                "persona-manager",
                "classify memory from inbound turn",
                "completed",
                "2026-06-25T00:02:05Z",
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _read_inbound_turn_writes(database_path: Path) -> tuple[str, ...]:
    connection = _connect(database_path)
    try:
        events = _read_count(
            connection,
            "events",
            "id IN ('event-003', 'event-004')",
        )
        memories = _read_count(connection, "memories", "id = 'memory-003'")
        embeddings = _read_count(connection, "memory_embeddings", "id = 'embedding-004'")
        grants = _read_count(connection, "permission_grants", "id = 'grant-002'")
        workflow_runs = _read_count(connection, "workflow_runs", "id = 'workflow-run-002'")
        subagent_runs = _read_count(connection, "subagent_runs", "id = 'subagent-run-002'")
    finally:
        connection.close()

    return (
        f"events:{events}",
        f"memories:{memories}",
        f"embeddings:{embeddings}",
        f"grants:{grants}",
        f"workflow_runs:{workflow_runs}",
        f"subagent_runs:{subagent_runs}",
    )


def _read_count(connection: Any, table: str, where: str) -> int:
    row = connection.execute(f"SELECT count(*) FROM {table} WHERE {where}").fetchone()
    if row is None:
        raise RuntimeError(f"storage spike could not count rows in {table}")

    return int(row[0])


def _run_concurrent_writer_probe(database_path: Path) -> str:
    barrier = Barrier(2)
    writer_specs = (
        ("writer-a", "event-005", 5, "concurrent user turn a"),
        ("writer-b", "event-006", 6, "concurrent user turn b"),
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(
            executor.submit(
                _write_concurrent_event_with_retry,
                database_path,
                writer_id,
                event_id,
                sequence,
                content,
                barrier,
            )
            for writer_id, event_id, sequence, content in writer_specs
        )
        writer_results = tuple(result.result() for result in results)

    connection = _connect(database_path)
    try:
        event_count = _read_count(
            connection,
            "events",
            "id IN ('event-005', 'event-006')",
        )
    finally:
        connection.close()

    retryable_errors = sum(result.retryable_errors for result in writer_results)
    attempts = sum(result.attempts for result in writer_results)
    return (
        f"writers:{len(writer_results)}, events:{event_count}, "
        f"retryable_errors:{retryable_errors}, attempts:{attempts}"
    )


def _write_concurrent_event_with_retry(
    database_path: Path,
    writer_id: str,
    event_id: str,
    sequence: int,
    content: str,
    barrier: Barrier,
) -> ConcurrentWriterResult:
    retryable_errors = 0
    max_attempts = 4

    for attempt in range(1, max_attempts + 1):
        connection = _connect(database_path)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN CONCURRENT")

            if attempt == 1:
                try:
                    barrier.wait(timeout=5)
                except BrokenBarrierError:
                    pass

            connection.execute(
                """
                INSERT INTO events (id, session_id, sequence, actor, content, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    "session-main",
                    sequence,
                    writer_id,
                    content,
                    f"2026-06-25T00:03:0{sequence - 5}Z",
                ),
            )
            connection.commit()
            return ConcurrentWriterResult(writer_id, attempt, retryable_errors)
        except Exception as error:
            _rollback_quietly(connection)
            if not _is_retryable_database_error(error) or attempt == max_attempts:
                raise
            retryable_errors += 1
        finally:
            connection.close()

    raise RuntimeError(f"concurrent writer {writer_id!r} exhausted retry attempts")


def _rollback_quietly(connection: Any) -> None:
    try:
        connection.rollback()
    except Exception:
        pass


def _is_retryable_database_error(error: Exception) -> bool:
    message = str(error).lower()
    retryable_markers = (
        "busy",
        "locked",
        "conflict",
        "concurrent",
        "snapshot",
        "retry",
    )
    return any(marker in message for marker in retryable_markers)


def _run_multiprocess_probe(database_path: Path) -> str:
    worker_specs = (
        ("event-007", 7),
        ("event-008", 8),
    )

    for event_id, sequence in worker_specs:
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--multiprocess-worker",
                str(database_path),
                event_id,
                str(sequence),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    connection = _connect(database_path)
    try:
        event_count = _read_count(
            connection,
            "events",
            "id IN ('event-007', 'event-008')",
        )
    finally:
        connection.close()

    return f"processes:{len(worker_specs)}, events:{event_count}"


def _run_multiprocess_worker(database_path: Path, *, event_id: str, sequence: int) -> None:
    connection = _connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO events (id, session_id, sequence, actor, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                "session-main",
                sequence,
                "process-worker",
                f"multi-process event {sequence}",
                f"2026-06-25T00:04:0{sequence - 7}Z",
            ),
        )
        connection.commit()
    finally:
        connection.close()


def _run_repeat_open_probe(database_path: Path) -> str:
    event_counts: list[int] = []
    journal_modes: list[str] = []

    for _ in range(3):
        connection = _connect(database_path)
        try:
            journal_row = connection.execute("PRAGMA journal_mode").fetchone()
            event_count = _read_count(connection, "events", "1 = 1")
        finally:
            connection.close()

        if journal_row is None:
            raise RuntimeError("repeat-open probe could not read journal mode")

        journal_modes.append(str(journal_row[0]).lower())
        event_counts.append(event_count)

    if len(set(journal_modes)) != 1:
        raise RuntimeError(f"repeat-open probe saw unstable journal modes: {journal_modes!r}")

    if len(set(event_counts)) != 1:
        raise RuntimeError(f"repeat-open probe saw unstable event counts: {event_counts!r}")

    return f"opens:{len(event_counts)}, journal_mode:{journal_modes[0]}, events:{event_counts[0]}"


if __name__ == "__main__":
    main()
