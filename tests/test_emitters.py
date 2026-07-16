import asyncio
from pathlib import Path

from ethos.config import EventsConfig
from ethos.events import create_event_emitter
from ethos.events.emitters import EnvelopeEventEmitter
from ethos.events.listeners import EventListenerRegistry
from ethos.events.models import EventEnvelope, EventSource
from ethos.events.sinks import InMemoryEventSink
from ethos.events.types import EventType
from ethos.storage import StorageEventSink


def test_emitter_appends_event_to_sink() -> None:
    sink = InMemoryEventSink()
    emitter = EnvelopeEventEmitter(enabled=True, sink=sink)
    event = EventEnvelope(
        type=EventType.APP_STARTED,
        source=EventSource(name="test"),
    )

    emitted = asyncio.run(emitter.emit(event))

    assert emitted == event
    assert emitted is event
    assert sink.events == (emitted,)


def test_event_emitter_is_created_with_explicit_storage(
    tmp_path: Path,
) -> None:
    emitter = create_event_emitter(tmp_path / "events.db", EventsConfig())

    assert isinstance(emitter._sink, StorageEventSink)


def test_emitter_works_without_sink_or_dispatcher() -> None:
    emitter = EnvelopeEventEmitter(enabled=True)
    event = EventEnvelope(
        type=EventType.APP_STARTED,
        source=EventSource(name="test"),
    )

    emitted = asyncio.run(emitter.emit(event))

    assert emitted == event
    assert emitted is event


def test_emitter_dispatches_event_to_listener() -> None:
    registry = EventListenerRegistry()
    emitter = EnvelopeEventEmitter(enabled=True, dispatcher=registry)
    delivered: list[EventEnvelope] = []
    event = EventEnvelope(
        type=EventType.APP_STARTED,
        source=EventSource(name="test"),
    )

    async def listener(event: EventEnvelope) -> None:
        delivered.append(event)

    registry.register(listener)

    emitted = asyncio.run(emitter.emit(event))

    assert delivered == [emitted]


def test_emitter_appends_before_dispatching() -> None:
    sink = InMemoryEventSink()
    registry = EventListenerRegistry()
    emitter = EnvelopeEventEmitter(enabled=True, sink=sink, dispatcher=registry)
    sink_events_seen_by_listener: list[tuple[EventEnvelope, ...]] = []
    event = EventEnvelope(
        type=EventType.APP_STARTED,
        source=EventSource(name="test"),
    )

    async def listener(_event: EventEnvelope) -> None:
        sink_events_seen_by_listener.append(sink.events)

    registry.register(listener)

    emitted = asyncio.run(emitter.emit(event))

    assert sink_events_seen_by_listener == [(emitted,)]
