# Kafka Microservices Demo

Implementación base de 5 microservicios en Django para un flujo de órdenes con Kafka (EC2) y 2 bases de datos PostgreSQL.

## Servicios

- **Ordering**: recibe la petición inicial y expone `POST /orders/` y `GET /products/`.
- **Billing**: consume `OrderCreated` y procesa el pago.
- **Inventory**: valida y reserva stock.
- **Shipping**: coordina pago + stock y genera el envío.
- **Notification**: escucha todos los eventos y prepara el envío de correo.

## Bases de datos

- **Commercial**: `ordering`, `billing`, `notification`
- **Logistics**: `inventory`, `shipping`

## Kafka topics

- `orders`
- `payments`
- `shipments`

## Datos iniciales

Ejecuta el seed:

```bash
python manage.py seed_data
```

Clientes creados:

- `danielsafo@unisabana.edu.co`
- `daniel.saavedra.fon@gmail.com`

Productos semilla disponibles para probar en Postman:

- `id=1` — Laptop
- `id=2` — Mouse
- `id=3` — Keyboard

## Endpoints iniciales

### Ordering

- `GET /health/`
- `POST /orders/`
- `GET /products/`

### Otros servicios

- `GET /health/`

## Variables de entorno

Configura `.env` antes de arrancar:

- `DJANGO_SECRET_KEY`
- `ORDERING_DB_*`
- `LOGISTICS_DB_*`
- `KAFKA_BOOTSTRAP_SERVERS`
- `SES_*`

## Estado actual

La base técnica ya incluye:

- Router de 2 bases de datos
- Modelos iniciales de dominio
- Seed de clientes y productos
- Consumidores Kafka básicos por servicio con logs de recepción
- Publicador genérico de outbox para empujar eventos a Kafka
- Estructura de eventos compartida

## Comandos útiles

- `python manage.py seed_data`
- `python manage.py publish_outbox`
- `python manage.py publish_order --order-id 1 --customer-id 1`
