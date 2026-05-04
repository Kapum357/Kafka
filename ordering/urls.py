from django.urls import path

from .views import create_order, health, list_products

urlpatterns = [
    path("health/", health),
    path("orders/", create_order),
    path("products/", list_products),
]
