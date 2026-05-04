# Guía Detallada de Despliegue en AWS (Free Tier)

Este documento expande las instrucciones del `README.md` con los comandos y pasos exactos para configurar los componentes clave del proyecto utilizando la capa gratuita de AWS.

## 1. Despliegue de Kafka en Amazon EC2 (Free Tier)

Dado que Amazon MSK tiene costo, levantaremos Kafka usando Docker en una instancia gratuita de EC2.

### Paso 1: Lanzar la instancia EC2
1. Ve a la consola de AWS -> **EC2** -> **Launch Instance**.
2. **Nombre:** `kafka-server`
3. **AMI:** Ubuntu Server 22.04 LTS o Amazon Linux 2023 (ambas elegibles para Free Tier).
4. **Tipo de instancia:** `t2.micro` o `t3.micro` (Free Tier).
5. **Key pair:** Crea uno nuevo o usa uno existente para conectarte por SSH.
6. **Network settings:**
   - Habilita auto-asignación de IP pública.
   - En el **Security Group**, añade una regla para permitir **Custom TCP en el puerto 9092** (Kafka) desde cualquier lugar (`0.0.0.0/0`) o desde la IP/VPC de tu aplicación.
   - Deja el puerto 22 (SSH) abierto para conectarte.
7. Lanza la instancia.

### Paso 2: Instalar Docker y levantar Kafka
Conéctate por SSH a la instancia:
```bash
ssh -i "tu-llave.pem" ubuntu@<IP_PUBLICA_EC2>
```

Instala Docker y Docker Compose:
```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker ubuntu
# Sal y vuelve a entrar por SSH para aplicar los permisos de grupo
```

Crea un archivo `docker-compose.yml` para Kafka:
```yaml
services:
  kafka:
    image: confluentinc/cp-kafka:latest
    container_name: kafka
    ports:
      - "9092:9092"
    environment:
      KAFKA_NODE_ID: "1"
      KAFKA_PROCESS_ROLES: "broker,controller"
      KAFKA_CONTROLLER_LISTENER_NAMES: "CONTROLLER"
      KAFKA_CONTROLLER_QUORUM_VOTERS: "1@kafka:9093"
      CLUSTER_ID: "5L6g3nShT-eMCtK--X86sw"

      KAFKA_LISTENERS: "CONTROLLER://0.0.0.0:9093,INTERNAL://0.0.0.0:29092,EXTERNAL://0.0.0.0:9092"
      KAFKA_ADVERTISED_LISTENERS: "INTERNAL://kafka:29092,EXTERNAL://18.221.108.81:29092"
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: "CONTROLLER:PLAINTEXT,INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT"
      KAFKA_INTER_BROKER_LISTENER_NAME: "INTERNAL"

      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: "1"
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: "1"
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: "1"

      # AJUSTE CLAVE PARA NO MORIR POR RAM
      KAFKA_HEAP_OPTS: "-Xms256m -Xmx256m"
      # o si tienes un poco más de RAM:
      # KAFKA_HEAP_OPTS: "-Xms256m -Xmx512m"
```

### Paso 3: Crear los tópicos
Ingresa al contenedor para crear los tópicos requeridos manualmente:
```bash
docker exec -it <ID_DEL_CONTENEDOR_KAFKA> bash
```

# Dentro del contenedor ejecuta:
```bash
kafka-topics --create --topic orders --bootstrap-server localhost:29092 --partitions 3 --replication-factor 1
kafka-topics --create --topic payments --bootstrap-server localhost:29092 --partitions 3 --replication-factor 1
kafka-topics --create --topic shipments --bootstrap-server localhost:29092 --partitions 3 --replication-factor 1
```

**En tu `.env` local o en Fargate, actualiza:**
```env
KAFKA_BOOTSTRAP_SERVERS=<IP_PUBLICA_EC2>:29092
# Si no usas SSL/SASL en tu EC2 propio, remueve KAFKA_API_KEY y KAFKA_SECURITY_PROTOCOL.
```

---

## 2. Configuración de Amazon SES (Envío de Emails)

### Paso 1: Verificar Identidades
1. Ve a la consola de AWS -> **Amazon SES** -> **Verified identities**.
2. Haz clic en **Create identity**.
3. Selecciona **Email address** y pon tu correo (ej. `danielsafo@unisabana.edu.co`).
4. Ve a tu bandeja de entrada y haz clic en el enlace de verificación de AWS.
5. (Opcional) Verifica otros correos de prueba si tu cuenta de SES está en **Sandbox** (modo de prueba de AWS, solo puedes enviar a correos verificados).

### Paso 2: Generar credenciales SMTP
1. En la consola de SES, ve a **SMTP settings**.
2. Haz clic en **Create SMTP credentials**.
3. Escribe un nombre para el usuario IAM (ej. `ses-smtp-user`).
4. Haz clic en **Create**.
5. Copia el **SMTP Username** y la **SMTP Password**. *(¡No los pierdas, no podrás verlos de nuevo!)*

**En tu `.env` o Secrets Manager, actualiza:**
```env
SES_REGION=us-east-2 # (o tu región)
SES_SMTP_HOST=email-smtp.<tu-region>.amazonaws.com
SES_SMTP_PORT=587
SES_SMTP_USER=<TU_SMTP_USERNAME>
SES_SMTP_PASSWORD=<TU_SMTP_PASSWORD>
SES_FROM_EMAIL=danielsafo@unisabana.edu.co # (o tu correo verificado)
```

---

## 3. Despliegue en AWS ECS (Fargate)

AWS Fargate te permite correr contenedores sin administrar los servidores subyacentes.

### Paso 1: Subir imagen a Amazon ECR
1. En AWS, ve a **ECR** y crea un repositorio llamado `kafka-microservices`.
2. Autentica Docker en tu terminal (Sigue los comandos de *View push commands* en la consola de ECR).
3. Construye y sube la imagen:
```bash
docker build -t kafka-microservices .
docker tag kafka-microservices:latest 035839414719.dkr.ecr.us-east-2.amazonaws.com/kafka-microservices:latest
docker push 035839414719.dkr.ecr.us-east-2.amazonaws.com/kafka-microservices:latest
```

### Paso 2: Crear el Cluster en ECS
1. Ve a **ECS** -> **Clusters** -> **Create cluster**.
2. Ponle un nombre (ej. `microservices-cluster`) y usa **AWS Fargate** como infraestructura.

### Paso 3: Definiciones de Tareas (Task Definitions)
Necesitas crear diferentes Task Definitions basadas en la misma imagen, pero con distinto comando de inicio (`CMD`). Esto permite que cada contenedor se especialice en una función (API, Consumidor, etc.) compartiendo el mismo código base.

1. Ve a **Task definitions** -> **Create new task definition**.
2. Selecciona **Fargate** y el tamaño (ej. 0.5 vCPU, 1 GB RAM).
3. Configura los detalles del contenedor según la siguiente tabla:

| Servicio / Tarea | Nombre TD | Command (CMD) | SERVICE_NAME | Port Mapping |
| :--- | :--- | :--- | :--- | :--- |
| **Ordering API** | `ordering-api` | `gunicorn patterns.wsgi -b 0.0.0.0:8000` | `ordering` | 8000 |
| **Billing Consumer** | `billing-consumer` | `python manage.py consume_orders` | `billing` | - |
| **Inventory Consumer** | `inventory-consumer` | `python manage.py consume_payments` | `inventory` | - |
| **Shipping Payments** | `shipping-payments` | `python manage.py consume_payments` | `shipping` | - |
| **Shipping Shipments** | `shipping-shipments` | `python manage.py consume_shipments` | `shipping` | - |
| **Notification Worker** | `notification-worker` | `python manage.py consume_all` | `notification` | - |
| **Outbox Publisher** | `outbox-publisher` | `python manage.py publish_outbox` | `common` | - |

**Notas importantes:**
- **Command:** Asegúrate de escribir el comando exacto. En la consola de AWS, esto suele ir en un campo llamado "Command override" o similar.
- **Environment variables:** 
  - Todas las tareas deben tener las variables de base: `KAFKA_BOOTSTRAP_SERVERS`, `DATABASE_URL`, `SECRET_KEY`, etc.
  - No olvides `SERVICE_NAME` para que el ruteo de base de datos funcione correctamente (especialmente en `billing`, `inventory` y `shipping`).
  - Las tareas de **Notification** necesitan las credenciales de SES (`SES_SMTP_HOST`, `SES_SMTP_USER`, etc.).
- **Outbox Publisher:** Es vital para que los eventos guardados en la base de datos se envíen a Kafka. Sin este proceso, el flujo de eventos se detendrá.

### Paso 4: Ejecutar los Servicios
1. En tu Cluster ECS, ve a la pestaña **Services** -> **Create**.
2. Elige Fargate y selecciona tu Task Definition (ej. `ordering-api`).
3. (Opcional para APIs) Configura un Application Load Balancer (ALB) si quieres tráfico desde internet.
4. (Para Consumidores) Simplemente lánzalos como servicios en Fargate sin balanceador de carga, ya que se comunican vía Kafka.

---

## 4. Gestión de Secretos (AWS Secrets Manager)

Para no exponer contraseñas (DB, SES) en texto plano en la definición de la tarea:
1. Ve a **AWS Secrets Manager** -> **Store a new secret**.
2. Selecciona **Other type of secret**.
3. Añade las llaves y valores (ej. `ORDERING_DB_PASSWORD`, `LOGISTICS_DB_PASSWORD`).
4. Guarda el secreto y copia su **ARN**.
5. En la definición de la tarea (Task Definition) de ECS, en la sección de **Environment variables**, cambia a **ValueFrom** y pega el ARN del secreto.
6. Asegúrate de que el **Task execution role** de ECS tenga permisos `secretsmanager:GetSecretValue` para leer el ARN.

---

## 5. Verificación Manual del Flujo

Una vez que los servicios estén corriendo, puedes verificar el flujo de eventos de principio a fin.

1. **Generar Datos Semilla:**
   Ejecuta el script de seed en uno de los contenedores o localmente (apuntando a RDS):
   ```bash
   python manage.py seed_data
   ```
   Esto creará clientes y productos iniciales, y mostrará en consola los IDs de los productos.

2. **Verificar Productos:**
   Haz una petición `GET` a tu API:
   ```bash
   curl http://<tu-alb-o-ip>:8000/products/
   ```
   Debe devolver la lista de productos con su stock disponible.

3. **Crear una Orden:**
   Envía una petición `POST` al endpoint de creación de órdenes:
   ```bash
   curl -X POST http://<tu-alb-o-ip>:8000/orders/ \
     -H "Content-Type: application/json" \
     -d '{
           "customer_email": "danielsafo@unisabana.edu.co",
           "items": [
               {"product_id": 1, "quantity": 1}
           ]
         }'
   ```
   Esto devolverá el `order_id` y el `event_id` guardado en la tabla outbox.

4. **Publicar y Consumir (Flujo de Kafka):**
   - Asegúrate de que el `outbox-publisher` esté publicando el evento en Kafka.
   - Revisa los logs en CloudWatch (`/ecs/microservices-system`) para cada consumidor:
     - **Billing** emitirá un pago (`PaymentProcessed`).
     - **Inventory** reservará el stock (`StockReserved`).
     - **Shipping** actualizará las banderas, y una vez que tenga ambas (pago y stock), creará el envío (`ShipmentCreated`).
     - **Notification** interceptará los eventos y enviará los correos a través de Amazon SES.

¡Listo! Con esto tu arquitectura de microservicios estará corriendo completamente sobre AWS, utilizando opciones económicas o gratuitas.
