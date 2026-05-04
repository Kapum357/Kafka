from django.core.management.base import BaseCommand

from billing.models import Payment
from inventory.models import Product, StockItem
from ordering.models import Customer, Order


class Command(BaseCommand):
    help = "Seed customers, products, and starter records for the Kafka demo."

    def handle(self, *args, **options):
        customers = [
            ("Daniel Safo", "danielsafo@unisabana.edu.co"),
            ("Daniel Saavedra", "daniel.saavedra.fon@gmail.com"),
        ]
        products = [
            ("SKU-LAP-001", "Laptop", 3500000, 10),
            ("SKU-MOU-002", "Mouse", 80000, 50),
            ("SKU-KBD-003", "Keyboard", 120000, 25),
        ]

        for full_name, email in customers:
            Customer.objects.update_or_create(email=email, defaults={"full_name": full_name})

        for sku, name, price, quantity in products:
            product, _ = Product.objects.update_or_create(
                sku=sku,
                defaults={"name": name, "price": price, "active": True},
            )
            StockItem.objects.update_or_create(
                product=product,
                defaults={"available_quantity": quantity, "reserved_quantity": 0},
            )

        self.stdout.write(self.style.SUCCESS("Seed data created for customers and products."))
        self.stdout.write(self.style.WARNING("Product IDs available for ordering:"))
        for product in Product.objects.order_by("id"):
            self.stdout.write(f"- id={product.id} sku={product.sku} name={product.name} stock={product.stock.available_quantity}")
