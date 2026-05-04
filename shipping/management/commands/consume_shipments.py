import json
import logging
from uuid import uuid4

from django.core.management.base import BaseCommand
from django.db import transaction

from common.events import SHIPMENT_CREATED, STOCK_REJECTED, STOCK_RESERVED, TOPIC_SHIPMENTS, EventEnvelope
from common.kafka_client import KafkaEventConsumer
from common.outbox import create_outbox_record
from shipping.models import OutboxEvent, ProcessedEvent, Shipment, ShippingOrchestration

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Consume shipment events for shipping orchestration."

    def handle(self, *args, **options):
        consumer = KafkaEventConsumer([TOPIC_SHIPMENTS], group_id="shipping-shipments-consumer")
        self.stdout.write(self.style.SUCCESS("Shipping shipment consumer started"))
        try:
            while True:
                message = consumer.poll(1.0)
                if message is None:
                    continue
                if message.error():
                    logger.error("Shipping shipment consumer error: %s", message.error())
                    continue
                payload = json.loads(message.value().decode("utf-8"))
                result = self._process_shipment_event(payload)
                if result is None:
                    consumer.commit(message)
                    continue
                logger.info("Shipping received shipment topic event_id=%s type=%s", result["event_id"], result["event_type"])
                self.stdout.write(f"Shipping received {result['event_type']} for order_id={result['order_id']}")
                consumer.commit(message)
        finally:
            consumer.close()

    def _process_shipment_event(self, payload):
        event_id = payload["event_id"]
        if ProcessedEvent.objects.using("logistics").filter(event_id=event_id).exists():
            logger.info("Shipping shipment skipped duplicate event_id=%s", event_id)
            return None

        order_id = payload["payload"].get("order_id")
        with transaction.atomic(using="logistics"):
            ProcessedEvent.objects.using("logistics").create(
                event_id=event_id,
                event_type=payload["event_type"],
                source=payload["source"],
                payload=payload,
            )
            orchestration, _ = ShippingOrchestration.objects.using("logistics").get_or_create(
                order_id=order_id,
                defaults={"correlation_id": payload.get("correlation_id") or ""},
            )
            if payload["event_type"] == STOCK_RESERVED:
                orchestration.stock_reserved = True
            elif payload["event_type"] == STOCK_REJECTED:
                orchestration.shipment_created = False

            if orchestration.payment_received and orchestration.stock_reserved and not orchestration.shipment_created:
                shipment = Shipment.objects.using("logistics").create(
                    order_id=order_id,
                    tracking_code=f"trk-{uuid4().hex[:16]}",
                    status=Shipment.Status.CREATED,
                    shipping_address=payload["payload"].get("shipping_address", "Pending address"),
                    correlation_id=payload.get("correlation_id") or "",
                )
                orchestration.shipment_created = True
                envelope = EventEnvelope.create(
                    event_type=SHIPMENT_CREATED,
                    source="shipping",
                    payload={"order_id": order_id, "tracking_code": shipment.tracking_code},
                    topic=TOPIC_SHIPMENTS,
                    correlation_id=payload.get("correlation_id") or "",
                )
                create_outbox_record(
                    OutboxEvent,
                    envelope=envelope,
                    aggregate_type="Shipment",
                    aggregate_id=str(shipment.id),
                )

            orchestration.save(using="logistics")

        return {"event_id": event_id, "event_type": payload["event_type"], "order_id": order_id}
