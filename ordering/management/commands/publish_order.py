import json
import logging

from django.core.management.base import BaseCommand

from common.events import ORDER_CREATED, TOPIC_ORDERS, EventEnvelope
from common.kafka_client import KafkaEventPublisher

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Publish a demo OrderCreated event."

    def add_arguments(self, parser):
        parser.add_argument("--order-id", type=int, required=True)
        parser.add_argument("--customer-id", type=int, required=True)

    def handle(self, *args, **options):
        envelope = EventEnvelope.create(
            event_type=ORDER_CREATED,
            source="ordering",
            payload={
                "order_id": options["order_id"],
                "customer_id": options["customer_id"],
                "total_amount": "3500000.00",
                "customer_email": "danielsafo@unisabana.edu.co",
                "items": [{"product_id": 1, "quantity": 1}],
            },
            topic=TOPIC_ORDERS,
        )
        KafkaEventPublisher().publish(TOPIC_ORDERS, envelope.to_dict(), key=str(options["order_id"]))
        logger.info("Ordering published order event: %s", json.dumps(envelope.to_dict()))
        self.stdout.write(self.style.SUCCESS("OrderCreated event published"))
