import json
import logging
from uuid import uuid4

from django.core.management.base import BaseCommand
from django.db import transaction

from billing.models import OutboxEvent, Payment, ProcessedEvent
from common.events import PAYMENT_PROCESSED, TOPIC_ORDERS, TOPIC_PAYMENTS, EventEnvelope
from common.kafka_client import KafkaEventConsumer
from common.outbox import create_outbox_record

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Consume order events for billing."

    def handle(self, *args, **options):
        consumer = KafkaEventConsumer([TOPIC_ORDERS], group_id="billing-consumer")
        self.stdout.write(self.style.SUCCESS("Billing consumer started"))
        try:
            while True:
                message = consumer.poll(1.0)
                if message is None:
                    continue
                if message.error():
                    logger.error("Billing consumer error: %s", message.error())
                    continue
                payload = json.loads(message.value().decode("utf-8"))
                event_id = payload["event_id"]
                if ProcessedEvent.objects.using("commercial").filter(event_id=event_id).exists():
                    logger.info("Billing skipped duplicate event_id=%s", event_id)
                    consumer.commit(message)
                    continue

                with transaction.atomic(using="commercial"):
                    ProcessedEvent.objects.using("commercial").create(
                        event_id=event_id,
                        event_type=payload["event_type"],
                        source=payload["source"],
                        payload=payload,
                    )
                    payment = Payment.objects.using("commercial").create(
                        order_id=payload["payload"]["order_id"],
                        amount=payload["payload"].get("total_amount", 0),
                        status=Payment.Status.APPROVED,
                        transaction_id=f"pay-{uuid4().hex[:16]}",
                        correlation_id=payload.get("correlation_id") or "",
                    )
                    envelope = EventEnvelope.create(
                        event_type=PAYMENT_PROCESSED,
                        source="billing",
                        payload={
                            "payment_id": payment.id,
                            "order_id": payment.order_id,
                            "amount": str(payment.amount),
                            "status": payment.status,
                            "customer_email": payload["payload"].get("customer_email"),
                            "items": payload["payload"].get("items", []),
                        },
                        topic=TOPIC_PAYMENTS,
                        correlation_id=payment.correlation_id,
                    )
                    create_outbox_record(
                        OutboxEvent,
                        envelope=envelope,
                        aggregate_type="Payment",
                        aggregate_id=str(payment.id),
                    )

                logger.info("Billing processed order event_id=%s payment_id=%s", event_id, payment.id)
                self.stdout.write(f"Billing processed order_id={payment.order_id} payment_id={payment.id}")
                consumer.commit(message)
        finally:
            consumer.close()
