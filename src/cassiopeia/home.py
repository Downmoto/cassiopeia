"""Bootstrap the cassiopeia home directory layout."""

import json
from pathlib import Path
from typing import Final

DIRECTORIES: Final[tuple[str, ...]] = (
    "personas",
    "skills",
    "workflows",
    "gateways",
    "data",
)

JSON_FILES: Final[dict[str, object]] = {
    "config.json": {"version": 1},
    "workspaces.json": {"workspaces": []},
    "hooks.json": {"hooks": []},
    "permissions.json": {"grants": []},
    "workflows.json": {"workflows": []},
}


def initialise_home(home: Path) -> Path:
    """Create a new cassiopeia home directory and starter definition files.

    This is a bootstrap operation, not a repair or migration operation. Existing
    homes are rejected so user-authored files are never silently interpreted or
    rewritten by `cass init`.
    """

    resolved_home = home.expanduser()
    if resolved_home.exists():
        raise FileExistsError(f"cassiopeia home already exists: {resolved_home}")

    resolved_home.mkdir(parents=True)

    for directory in DIRECTORIES:
        (resolved_home / directory).mkdir(exist_ok=True)

    for filename, default_content in JSON_FILES.items():
        path = resolved_home / filename
        if not path.exists():
            path.write_text(
                json.dumps(default_content, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

    return resolved_home
