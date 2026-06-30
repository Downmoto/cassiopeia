"""Event listener registry for async in-process callbacks."""

from collections.abc import Awaitable, Callable

from cassiopeia.events.models import EventEnvelope

type EventListener = Callable[[EventEnvelope], Awaitable[None]]


class EventListenerRegistry:
    """Minimal in-process listener registry with deterministic delivery order.

    Listener failures do not prevent later listeners from receiving the event.
    Any failures are collected and raised together after delivery completes.
    """

    def __init__(self) -> None:
        self._listeners: list[EventListener] = []

    def register(self, listener: EventListener) -> None:
        """Register a listener after previously registered listeners."""

        self._listeners.append(listener)

    async def deliver(self, event: EventEnvelope) -> None:
        """Deliver an event to listeners in registration order."""

        failures: list[Exception] = []

        for listener in self._listeners:
            try:
                await listener(event)
            except Exception as error:
                failures.append(error)

        if failures:
            raise ExceptionGroup(
                f"{len(failures)} event listener(s) failed while handling {event.type.value}",
                failures,
            )
