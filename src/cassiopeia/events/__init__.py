"""Typed cassiopeia event APIs.

The events package owns the stable contract for lifecycle events emitted by
cassiopeia feature packages. `EventType` is the canonical event name set.
`EventCreate` is the caller-owned request shape, while `EventEnvelope` is the
persisted shape produced by an emitter with generated identity and time.

Payload models only contain details that are not already expressed by the event
type or envelope scope fields. Stored historical events should still load
through the generic `EventPayload`, even when newer code uses a narrower
family-specific payload model for write-time validation.
"""
