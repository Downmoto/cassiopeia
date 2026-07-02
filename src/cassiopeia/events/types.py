"""Event type primitives."""

from enum import StrEnum


class EventType(StrEnum):
    """Canonical event type names for cassiopeia lifecycle events."""

    APP_STARTED = "app.started"
    APP_INITIALISED = "app.initialised"
