from django.db import models


class Product(models.Model):
	sku = models.CharField(max_length=64, unique=True)
	name = models.CharField(max_length=160)
	price = models.DecimalField(max_digits=12, decimal_places=2)
	active = models.BooleanField(default=True)

	class Meta:
		app_label = "inventory"


class StockItem(models.Model):
	product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="stock")
	available_quantity = models.PositiveIntegerField(default=0)
	reserved_quantity = models.PositiveIntegerField(default=0)

	class Meta:
		app_label = "inventory"


class StockReservation(models.Model):
	order_id = models.IntegerField(db_index=True)
	product = models.ForeignKey(Product, on_delete=models.PROTECT)
	quantity = models.PositiveIntegerField()
	reservation_code = models.CharField(max_length=80, unique=True)
	correlation_id = models.CharField(max_length=64, db_index=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		app_label = "inventory"


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
		app_label = "inventory"


class ProcessedEvent(models.Model):
	event_id = models.CharField(max_length=64, unique=True)
	event_type = models.CharField(max_length=80)
	source = models.CharField(max_length=80)
	payload = models.JSONField()
	processed_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		app_label = "inventory"
