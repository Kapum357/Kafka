from django.db import models


class Shipment(models.Model):
	class Status(models.TextChoices):
		CREATED = "CREATED", "Created"
		IN_TRANSIT = "IN_TRANSIT", "In transit"
		DELIVERED = "DELIVERED", "Delivered"

	order_id = models.IntegerField(db_index=True)
	tracking_code = models.CharField(max_length=80, unique=True)
	status = models.CharField(max_length=32, choices=Status.choices, default=Status.CREATED)
	shipping_address = models.TextField()
	correlation_id = models.CharField(max_length=64, db_index=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		app_label = "shipping"


class ShippingOrchestration(models.Model):
	order_id = models.IntegerField(unique=True)
	payment_received = models.BooleanField(default=False)
	stock_reserved = models.BooleanField(default=False)
	shipment_created = models.BooleanField(default=False)
	correlation_id = models.CharField(max_length=64, db_index=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = "shipping"


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
		app_label = "shipping"


class ProcessedEvent(models.Model):
	event_id = models.CharField(max_length=64, unique=True)
	event_type = models.CharField(max_length=80)
	source = models.CharField(max_length=80)
	payload = models.JSONField()
	processed_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		app_label = "shipping"
