"""Outbox helpers shared across services."""

from __future__ import annotations

from django.db import models

from common.events import EventEnvelope


def create_outbox_record(model_class: type[models.Model], *, envelope: EventEnvelope, aggregate_type: str, aggregate_id: str):
    return model_class.objects.create(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        event_type=envelope.event_type,
        topic=envelope.topic,
        payload=envelope.to_dict(),
        correlation_id=envelope.correlation_id or "",
    )
