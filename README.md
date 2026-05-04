# Kafka Microservices Demo

Implementación base de 5 microservicios en Django para un flujo de órdenes con Kafka (Confluent Cloud) y 2 bases de datos PostgreSQL.

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
- `COMMERCIAL_DB_*`
- `LOGISTICS_DB_*`
- `KAFKA_BOOTSTRAP_SERVERS`
- `KAFKA_API_KEY`
- `KAFKA_API_SECRET`
- `SES_*`

## Estado actual

La base técnica ya incluye:

- Router de 2 bases de datos
- Modelos iniciales de dominio
- Seed de clientes y productos
- Consumidores Kafka básicos por servicio con logs de recepción
- Publicador genérico de outbox para empujar eventos a Kafka
- Estructura de eventos compartida

## Guía de Despliegue en AWS

Esta arquitectura se diseñó para operar sobre la infraestructura cloud de AWS usando componentes fully-managed:

### 1. Bases de Datos (Amazon RDS)
- Desplegar 2 instancias de **Amazon RDS for PostgreSQL**.
- **DB Commercial**: Crea la base de datos `commercial` (para Ordering, Billing y Notification).
- **DB Logistics**: Crea la base de datos `logistics` (para Inventory y Shipping).
- Asegúrate de asignar los Security Groups para permitir el acceso desde tus VPC/Subnets de contenedores.

### 2. Mensajería (Amazon free plan)
Levanta una máquina virtual en Amazon EC2 usando la capa gratuita (Free Tier). Instala Docker y levanta un contenedor de Kafka (por ejemplo con `bitnami/kafka` en modo KRaft) exponiendo el puerto 9092, y apúntalo en el archivo `.env`.
> - `orders`
> - `payments`
> - `shipments`

### 3. Email (Amazon SES)
- Configura **Amazon Simple Email Service (SES)** en la misma región.
- Verifica los correos emisores y las identidades de prueba (como `danielsafo@unisabana.edu.co`).
- Genera credenciales SMTP e introdúcelas en `SES_HOST`, `SES_USER`, y `SES_PASS`.

### 4. Contenedores y Cómputo (Amazon ECS + AWS Fargate)
- Dockeriza la aplicación (crea un `Dockerfile` base con los requirements.txt).
- Empuja la imagen a **Amazon ECR**.
- Configura **Task Definitions** independientes en **AWS Fargate** por cada microservicio. Cada tarea tendrá su propio comando de inicio.
  - **Servicios API (Ordering)**: `gunicorn patterns.wsgi` exponiendo el puerto HTTP. Usa un **Application Load Balancer (ALB)** para enrutar tráfico.
  - **Consumidores (Billing, Inventory, Shipping, Notification)**: Ejecutan `python manage.py consume_<domain>`.
  - **Outbox Relays**: Ejecutan tareas programadas (o servicios continos) de `python manage.py publish_outbox` por cada app.

### 5. Configuración y Secretos (AWS Secrets Manager)
- Mueve las variables de tu `.env` a **AWS Secrets Manager** o **Systems Manager Parameter Store**.
- Asocia una IAM Role a tus Task Definitions que les permita recuperar estas credenciales en tiempo de ejecución.

## Comandos útiles

- `python manage.py seed_data`
- `python manage.py publish_outbox`
- `python manage.py publish_order --order-id 1 --customer-id 1`
