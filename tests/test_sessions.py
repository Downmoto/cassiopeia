from pathlib import Path
from stat import S_IMODE

import pytest
from pydantic_ai.messages import ModelRequest, UserPromptPart

from ethos.sessions import SessionManager
from ethos.workspaces import WorkspaceManager


def test_sessions_survive_manager_restarts(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    workspaces = WorkspaceManager(workspace_root)
    workspaces.create("my-project")
    manager = SessionManager(workspaces)
    session = manager.create("my-project")
    messages = (ModelRequest(parts=[UserPromptPart(content="hello")]),)
    manager.replace_messages("my-project", str(session.id), messages)

    restarted = SessionManager(WorkspaceManager(workspace_root))
    loaded = restarted.get("my-project", str(session.id))

    assert loaded.workspace_name == "my-project"
    assert loaded.messages == messages
    assert restarted.list("my-project") == (loaded,)
    session_path = workspaces.get("my-project").sessions_path / (
        f"{session.id}.json"
    )
    assert S_IMODE(session_path.stat().st_mode) == 0o600


def test_archived_session_is_recoverable_but_cannot_change(
    tmp_path: Path,
) -> None:
    workspaces = WorkspaceManager(tmp_path / "workspaces")
    workspaces.create("my-project")
    manager = SessionManager(workspaces)
    session = manager.create("my-project")

    archived = manager.archive("my-project", str(session.id))

    assert archived.archived
    assert manager.get("my-project", str(session.id)) == archived
    with pytest.raises(ValueError, match=f"session is archived: {session.id}"):
        manager.replace_messages("my-project", str(session.id), ())


def test_session_cannot_be_loaded_from_another_workspace(
    tmp_path: Path,
) -> None:
    workspaces = WorkspaceManager(tmp_path / "workspaces")
    workspaces.create("first")
    workspaces.create("second")
    manager = SessionManager(workspaces)
    session = manager.create("first")

    with pytest.raises(
        FileNotFoundError, match=f"session does not exist: {session.id}"
    ):
        manager.get("second", str(session.id))


def test_session_rejects_noncanonical_id(tmp_path: Path) -> None:
    workspaces = WorkspaceManager(tmp_path / "workspaces")
    workspaces.create("my-project")
    manager = SessionManager(workspaces)

    with pytest.raises(ValueError, match="invalid session ID"):
        manager.get("my-project", "../session")
