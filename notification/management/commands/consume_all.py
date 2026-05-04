import json
import logging
import os
import smtplib
from email.message import EmailMessage

from django.core.management.base import BaseCommand
from django.db import transaction

from common.events import TOPIC_ORDERS, TOPIC_PAYMENTS, TOPIC_SHIPMENTS
from common.kafka_client import KafkaEventConsumer
from notification.models import NotificationLog

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Consume all events for notifications."

    def handle(self, *args, **options):
        consumer = KafkaEventConsumer([TOPIC_ORDERS, TOPIC_PAYMENTS, TOPIC_SHIPMENTS], group_id="notification-consumer")
        self.stdout.write(self.style.SUCCESS("Notification consumer started"))
        try:
            while True:
                message = consumer.poll(1.0)
                if message is None:
                    continue
                if message.error():
                    logger.error("Notification consumer error: %s", message.error())
                    continue
                payload = json.loads(message.value().decode("utf-8"))
                event_id = payload["event_id"]
                
                if NotificationLog.objects.using("commercial").filter(event_id=event_id).exists():
                    logger.info("Notification skipped duplicate event_id=%s", event_id)
                    consumer.commit(message)
                    continue

                target_email = payload["payload"].get("customer_email") or payload["payload"].get("email") or "unknown@example.com"
                sent_status, detail = self._send_notification_email(payload, target_email)

                with transaction.atomic(using="commercial"):
                    NotificationLog.objects.using("commercial").update_or_create(
                        event_id=event_id,
                        defaults={
                            "event_type": payload["event_type"],
                            "target_email": target_email,
                            "status": sent_status,
                            "detail": detail,
                        },
                    )

                logger.info("Notification received from %s: %s", message.topic(), payload)
                self.stdout.write(f"Notification received event_id={event_id} topic={message.topic()}")
                consumer.commit(message)
        finally:
            consumer.close()

    def _send_notification_email(self, payload, target_email):
        subject = f"[{payload['event_type']}] update for order {payload['payload'].get('order_id', 'n/a')}"
        body = json.dumps(payload, ensure_ascii=False, indent=2)
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = os.getenv("SES_FROM_EMAIL", "no-reply@example.com")
        message["To"] = target_email
        message.set_content(body)

        try:
            with smtplib.SMTP(os.getenv("SES_SMTP_HOST", "localhost"), int(os.getenv("SES_SMTP_PORT", "587"))) as smtp:
                smtp.starttls()
                smtp.login(os.getenv("SES_SMTP_USER", ""), os.getenv("SES_SMTP_PASSWORD", ""))
                smtp.send_message(message)
            logger.info("Notification email sent to %s", target_email)
            return "SENT", f"Email sent to {target_email}"
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("Notification email not sent to %s: %s", target_email, exc)
            return "FAILED", f"Email send failed: {exc}"
