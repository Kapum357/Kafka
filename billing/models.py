from django.db import models


class Payment(models.Model):
	class Status(models.TextChoices):
		PENDING = "PENDING", "Pending"
		APPROVED = "APPROVED", "Approved"
		REJECTED = "REJECTED", "Rejected"

	order_id = models.IntegerField(db_index=True)
	amount = models.DecimalField(max_digits=12, decimal_places=2)
	status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
	transaction_id = models.CharField(max_length=80, unique=True)
	correlation_id = models.CharField(max_length=64, db_index=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		app_label = "billing"


class OutboxEvent(models.Model):
	aggregate_type = models.CharField(max_length=80)
	aggregate_id = models.CharField(max_length=80)
	event_type = models.CharField(max_length=80)
	topic = models.CharField(max_length=80)
	payload = models.JSONField()
	correlation_id = models.CharField(max_length=64, db_index=True)
	published = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	published_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		app_label = "billing"


class ProcessedEvent(models.Model):
	event_id = models.CharField(max_length=64, unique=True)
	event_type = models.CharField(max_length=80)
	source = models.CharField(max_length=80)
	payload = models.JSONField()
	processed_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		app_label = "billing"
