import json
import logging
from decimal import Decimal

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from common.events import ORDER_CREATED, TOPIC_ORDERS, EventEnvelope
from common.outbox import create_outbox_record
from inventory.models import Product
from .models import Customer, Order, OrderItem, OutboxEvent

logger = logging.getLogger(__name__)


@require_GET
def health(request):
	return JsonResponse({"service": "ordering", "status": "ok"})


@csrf_exempt
@require_http_methods(["POST"])
def create_order(request):
	payload = json.loads(request.body.decode("utf-8") or "{}")
	customer_email = payload.get("customer_email")
	items = payload.get("items", [])

	if not customer_email or not items:
		return JsonResponse({"detail": "customer_email and items are required"}, status=400)

	try:
		customer = Customer.objects.using("commercial").get(email=customer_email)
	except Customer.DoesNotExist:
		return JsonResponse({"detail": f"Customer with email {customer_email} not found"}, status=404)

	products_data = []
	for item in items:
		product_id = item.get("product_id")
		if not product_id:
			return JsonResponse({"detail": "product_id is required in all items"}, status=400)
		try:
			product = Product.objects.using("logistics").get(id=product_id)
			products_data.append({"product": product, "quantity": int(item.get("quantity", 1))})
		except Product.DoesNotExist:
			return JsonResponse({"detail": f"Product with id {product_id} not found"}, status=404)

	with transaction.atomic(using="commercial"):
		order = Order.objects.using("commercial").create(
			customer=customer,
			status=Order.Status.PENDING_PAYMENT,
			total_amount=Decimal("0"),
			correlation_id=payload.get("correlation_id") or f"order-{customer.pk}-{customer_email}",
		)

		total_amount = Decimal("0")
		serializable_items = []
		for p_data in products_data:
			product = p_data["product"]
			quantity = p_data["quantity"]
			unit_price = Decimal(str(product.price))
			total_amount += unit_price * quantity
			OrderItem.objects.using("commercial").create(
				order=order,
				product_id=product.pk,
				product_name=product.name,
				quantity=quantity,
				unit_price=unit_price,
			)
			serializable_items.append(
				{
					"product_id": product.pk,
					"product_name": product.name,
					"quantity": quantity,
					"unit_price": str(unit_price),
				}
			)

		order.total_amount = total_amount
		order.save(using="commercial", update_fields=["total_amount"])

		envelope = EventEnvelope.create(
			event_type=ORDER_CREATED,
			source="ordering",
			payload={
				"order_id": order.pk,
				"customer_id": customer.pk,
				"customer_email": customer.email,
				"items": serializable_items,
				"total_amount": str(order.total_amount),
			},
			topic=TOPIC_ORDERS,
			correlation_id=order.correlation_id,
		)
		create_outbox_record(
			OutboxEvent,
			envelope=envelope,
			aggregate_type="Order",
			aggregate_id=str(order.pk),
		)

	logger.info("Ordering stored order_id=%s and created outbox event_id=%s", order.pk, envelope.event_id)
	return JsonResponse(
		{
			"order_id": order.pk,
			"status": order.status,
			"total_amount": str(order.total_amount),
			"event_id": envelope.event_id,
		},
		status=201,
	)


@require_GET
def list_products(request):
	products = []
	for product in Product.objects.using("logistics").select_related("stock").all().order_by("id"):
		stock = getattr(product, "stock", None)
		products.append(
			{
				"product_id": product.pk,
				"sku": product.sku,
				"name": product.name,
				"price": str(product.price),
				"available_quantity": stock.available_quantity if stock is not None else None,
			}
		)
	return JsonResponse({"products": products})
