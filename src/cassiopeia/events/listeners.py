"""In-process event listener registry."""

from dataclasses import dataclass
from typing import Protocol

from cassiopeia.events.models import EventEnvelope


class EventListener(Protocol):
    """Async callable that receives emitted event envelopes."""

    async def __call__(self, event: EventEnvelope) -> None:
        """Handle an emitted event envelope."""
        ...


class EventDispatcher(Protocol):
    """Boundary for delivering emitted events to in-process listeners."""

    async def deliver(self, event: EventEnvelope) -> None:
        """Deliver an event to registered listeners."""
        ...


@dataclass(frozen=True)
class EventListenerFailure:
    """Failure raised by one listener while handling an event."""

    listener: EventListener
    error: Exception


class EventDeliveryError(Exception):
    """Raised after listener delivery when one or more listeners fail."""

    def __init__(
        self,
        event: EventEnvelope,
        failures: tuple[EventListenerFailure, ...],
    ) -> None:
        self.event = event
        self.failures = failures
        super().__init__(
            f"{len(failures)} event listener(s) failed while handling {event.type.value}"
        )


class InProcessEventListenerRegistry:
    """Minimal in-process listener registry with deterministic delivery order.

    Listener failures do not prevent later listeners from receiving the event.
    Any failures are collected and raised together after delivery completes.
    """

    def __init__(self) -> None:
        self._listeners: list[EventListener] = []

    @property
    def listeners(self) -> tuple[EventListener, ...]:
        """Registered listeners in delivery order."""

        return tuple(self._listeners)

    def register(self, listener: EventListener) -> None:
        """Register a listener after previously registered listeners."""

        self._listeners.append(listener)

    async def deliver(self, event: EventEnvelope) -> None:
        """Deliver an event to listeners in registration order."""

        failures: list[EventListenerFailure] = []

        for listener in self._listeners:
            try:
                await listener(event)
            except Exception as error:
                failures.append(EventListenerFailure(listener=listener, error=error))

        if failures:
            raise EventDeliveryError(event=event, failures=tuple(failures))
