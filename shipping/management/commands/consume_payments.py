import json
import logging
from uuid import uuid4

from django.core.management.base import BaseCommand
from django.db import transaction

from common.events import SHIPMENT_CREATED, TOPIC_PAYMENTS, TOPIC_SHIPMENTS, EventEnvelope
from common.kafka_client import KafkaEventConsumer
from common.outbox import create_outbox_record
from shipping.models import OutboxEvent, ProcessedEvent, Shipment, ShippingOrchestration

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Consume payment events for shipping orchestration."

    def handle(self, *args, **options):
        consumer = KafkaEventConsumer([TOPIC_PAYMENTS], group_id="shipping-payments-consumer")
        self.stdout.write(self.style.SUCCESS("Shipping payment consumer started"))
        try:
            while True:
                message = consumer.poll(1.0)
                if message is None:
                    continue
                if message.error():
                    logger.error("Shipping payment consumer error: %s", message.error())
                    continue
                payload = json.loads(message.value().decode("utf-8"))
                event_id = payload["event_id"]
                if ProcessedEvent.objects.using("logistics").filter(event_id=event_id).exists():
                    logger.info("Shipping payment skipped duplicate event_id=%s", event_id)
                    consumer.commit(message)
                    continue

                order_id = payload["payload"]["order_id"]
                correlation_id = payload.get("correlation_id") or ""

                with transaction.atomic(using="logistics"):
                    ProcessedEvent.objects.using("logistics").create(
                        event_id=event_id,
                        event_type=payload["event_type"],
                        source=payload["source"],
                        payload=payload,
                    )
                    orchestration, _ = ShippingOrchestration.objects.using("logistics").get_or_create(
                        order_id=order_id,
                        defaults={"correlation_id": correlation_id},
                    )
                    orchestration.payment_received = True
                    orchestration.save(using="logistics")

                    if orchestration.stock_reserved and not orchestration.shipment_created:
                        shipment = Shipment.objects.using("logistics").create(
                            order_id=order_id,
                            tracking_code=f"trk-{uuid4().hex[:16]}",
                            status=Shipment.Status.CREATED,
                            shipping_address=payload["payload"].get("shipping_address", "Pending address"),
                            correlation_id=correlation_id,
                        )
                        orchestration.shipment_created = True
                        orchestration.save(using="logistics", update_fields=["shipment_created", "updated_at"])
                        envelope = EventEnvelope.create(
                            event_type=SHIPMENT_CREATED,
                            source="shipping",
                            payload={"order_id": order_id, "tracking_code": shipment.tracking_code},
                            topic=TOPIC_SHIPMENTS,
                            correlation_id=correlation_id,
                        )
                        create_outbox_record(
                            OutboxEvent,
                            envelope=envelope,
                            aggregate_type="Shipment",
                            aggregate_id=str(shipment.id),
                        )

                logger.info("Shipping updated payment flag for order_id=%s", order_id)
                self.stdout.write(f"Shipping received payment for order_id={order_id}")
                consumer.commit(message)
        finally:
            consumer.close()
