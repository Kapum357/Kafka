import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from billing.models import OutboxEvent as BillingOutbox
from common.kafka_client import KafkaEventPublisher
from inventory.models import OutboxEvent as InventoryOutbox
from ordering.models import OutboxEvent as OrderingOutbox
from shipping.models import OutboxEvent as ShippingOutbox

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Publish pending outbox events from all services to Kafka."

    def handle(self, *args, **options):
        publisher = KafkaEventPublisher()
        models = [OrderingOutbox, BillingOutbox, InventoryOutbox, ShippingOutbox]
        total_published = 0

        for outbox_model in models:
            for event in outbox_model.objects.filter(published=False).order_by("created_at"):
                publisher.publish(event.topic, event.payload, key=event.aggregate_id)
                event.published = True
                event.published_at = timezone.now()
                event.save(update_fields=["published", "published_at"])
                total_published += 1
                logger.info("Published outbox event_id=%s topic=%s", event.id, event.topic)

        self.stdout.write(self.style.SUCCESS(f"Published {total_published} outbox events."))