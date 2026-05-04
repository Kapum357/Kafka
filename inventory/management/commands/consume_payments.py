import json
import logging
from uuid import uuid4

from django.core.management.base import BaseCommand
from django.db import transaction

from common.events import STOCK_REJECTED, STOCK_RESERVED, TOPIC_PAYMENTS, TOPIC_SHIPMENTS, EventEnvelope
from common.kafka_client import KafkaEventConsumer
from common.outbox import create_outbox_record
from inventory.models import OutboxEvent, ProcessedEvent, Product, StockItem, StockReservation

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Consume payment events for inventory."

    def handle(self, *args, **options):
        consumer = KafkaEventConsumer([TOPIC_PAYMENTS], group_id="inventory-consumer")
        self.stdout.write(self.style.SUCCESS("Inventory consumer started"))
        try:
            while True:
                message = consumer.poll(1.0)
                if message is None:
                    continue
                if message.error():
                    logger.error("Inventory consumer error: %s", message.error())
                    continue
                payload = json.loads(message.value().decode("utf-8"))
                processed = self._handle_payment_event(payload)
                if processed is not None:
                    self.stdout.write(f"Inventory processed order_id={processed['order_id']} event={processed['event_type']}")
                consumer.commit(message)
        finally:
            consumer.close()

    def _handle_payment_event(self, payload):
        event_id = payload["event_id"]
        if ProcessedEvent.objects.using("logistics").filter(event_id=event_id).exists():
            logger.info("Inventory skipped duplicate event_id=%s", event_id)
            return None

        items = payload["payload"].get("items", [])
        order_id = payload["payload"]["order_id"]
        correlation_id = payload.get("correlation_id") or ""

        with transaction.atomic(using="logistics"):
            ProcessedEvent.objects.using("logistics").create(
                event_id=event_id,
                event_type=payload["event_type"],
                source=payload["source"],
                payload=payload,
            )
            reservations, can_reserve = self._reserve_stock(order_id, items, correlation_id)
            envelope = self._build_envelope(payload, order_id, correlation_id, reservations, can_reserve)
            create_outbox_record(
                OutboxEvent,
                envelope=envelope,
                aggregate_type="Inventory",
                aggregate_id=str(order_id),
            )

        logger.info("Inventory processed payment event_id=%s order_id=%s", event_id, order_id)
        return {"order_id": order_id, "event_type": envelope.event_type}

    def _reserve_stock(self, order_id, items, correlation_id):
        reservations = []
        can_reserve = True
        for item in items:
            product = Product.objects.using("logistics").select_related("stock").get(id=item["product_id"])
            stock_item = StockItem.objects.using("logistics").select_related("product").get(product=product)
            quantity = int(item["quantity"])
            if stock_item.available_quantity < quantity:
                can_reserve = False
                break
            stock_item.available_quantity -= quantity
            stock_item.reserved_quantity += quantity
            stock_item.save(using="logistics")
            reservation = StockReservation.objects.using("logistics").create(
                order_id=order_id,
                product=product,
                quantity=quantity,
                reservation_code=f"res-{uuid4().hex[:16]}",
                correlation_id=correlation_id,
            )
            reservations.append(
                {
                    "product_id": product.id,
                    "product_name": product.name,
                    "quantity": quantity,
                    "reservation_code": reservation.reservation_code,
                }
            )
        return reservations, can_reserve

    @staticmethod
    def _build_envelope(payload, order_id, correlation_id, reservations, can_reserve):
        if can_reserve:
            return EventEnvelope.create(
                event_type=STOCK_RESERVED,
                source="inventory",
                payload={
                    "order_id": order_id,
                    "reservations": reservations,
                    "customer_email": payload["payload"].get("customer_email"),
                },
                topic=TOPIC_SHIPMENTS,
                correlation_id=correlation_id,
            )
        return EventEnvelope.create(
            event_type=STOCK_REJECTED,
            source="inventory",
            payload={"order_id": order_id, "reason": "Insufficient stock"},
            topic=TOPIC_SHIPMENTS,
            correlation_id=correlation_id,
        )
