from decimal import Decimal

from django.db import models


class Customer(models.Model):
	email = models.EmailField(unique=True)
	full_name = models.CharField(max_length=160)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		app_label = "ordering"


class Order(models.Model):
	class Status(models.TextChoices):
		PENDING_PAYMENT = "PENDING_PAYMENT", "Pending payment"
		PAID = "PAID", "Paid"
		REJECTED = "REJECTED", "Rejected"

	customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
	status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING_PAYMENT)
	total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
	correlation_id = models.CharField(max_length=64, db_index=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		app_label = "ordering"


class OrderItem(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
	product_id = models.IntegerField()
	product_name = models.CharField(max_length=160)
	quantity = models.PositiveIntegerField()
	unit_price = models.DecimalField(max_digits=12, decimal_places=2)

	class Meta:
		app_label = "ordering"


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
		app_label = "ordering"


class ProcessedEvent(models.Model):
	event_id = models.CharField(max_length=64, unique=True)
	event_type = models.CharField(max_length=80)
	source = models.CharField(max_length=80)
	payload = models.JSONField()
	processed_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		app_label = "ordering"
