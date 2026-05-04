"""Shared Kafka event contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class EventEnvelope:
    """Standard event envelope used by all services."""

    event_id: str
    event_type: str
    source: str
    occurred_at: str
    correlation_id: str | None
    payload: dict[str, Any]
    topic: str
    version: int = 1

    @classmethod
    def create(
        cls,
        *,
        event_type: str,
        source: str,
        payload: dict[str, Any],
        topic: str,
        correlation_id: str | None = None,
        version: int = 1,
    ) -> "EventEnvelope":
        return cls(
            event_id=str(uuid4()),
            event_type=event_type,
            source=source,
            occurred_at=datetime.now(timezone.utc).isoformat(),
            correlation_id=correlation_id,
            payload=payload,
            topic=topic,
            version=version,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "occurred_at": self.occurred_at,
            "correlation_id": self.correlation_id,
            "payload": self.payload,
            "topic": self.topic,
            "version": self.version,
        }

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), ensure_ascii=False)


TOPIC_ORDERS = "orders"
TOPIC_PAYMENTS = "payments"
TOPIC_SHIPMENTS = "shipments"

ORDER_CREATED = "OrderCreated"
PAYMENT_PROCESSED = "PaymentProcessed"
PAYMENT_FAILED = "PaymentFailed"
STOCK_RESERVED = "StockReserved"
STOCK_REJECTED = "StockRejected"
SHIPMENT_CREATED = "ShipmentCreated"
NOTIFICATION_SENT = "NotificationSent"
