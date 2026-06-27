import subprocess
import sys


def test_storage_spike_script_runs_open_reopen_probe() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/storage_spike.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "home: " in result.stdout
    assert "database: " in result.stdout
    assert "data/turso/cassiopeia.db" in result.stdout
    assert "journal_mode: mvcc" in result.stdout
    assert "probe: open-reopen-ok" in result.stdout
    assert "sample_tables: 9" in result.stdout
    assert "session_events: user: hello cassiopeia, assistant: hello arad" in result.stdout
    assert "workspace_sessions: session-main" in result.stdout
    assert "session_memories: prefers Canadian spelling, prefers American spelling" in result.stdout
    assert "embedding_profile: test-embedding-provider/test-memory-3-small/3/fresh" in result.stdout
    assert "vector_match: prefers Canadian spelling" in result.stdout
    assert "vector_distance: " in result.stdout
    assert (
        "stale_embedding_profile: test-embedding-provider/test-memory-3-small/3/stale"
        in result.stdout
    )
    assert (
        "refreshed_embedding_profile: test-embedding-provider/test-memory-4-small/4/fresh"
        in result.stdout
    )
    assert "refreshed_vector_match: prefers Canadian spelling" in result.stdout
    assert (
        "transaction_writes: events:2, memories:1, embeddings:1, grants:1, "
        "workflow_runs:1, subagent_runs:1"
    ) in result.stdout
    assert "concurrent_writes: writers:2, events:2, retryable_errors:" in result.stdout
    assert "multiprocess_writes: processes:2, events:2" in result.stdout
    assert "repeat_open: opens:3, journal_mode:mvcc, events:8" in result.stdout
