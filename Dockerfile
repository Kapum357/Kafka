# Usa una imagen oficial de Python ligera como imagen base
FROM python:3.12-slim

# Configura variables de entorno de Python
# Evita que Python escriba archivos .pyc en el disco
ENV PYTHONDONTWRITEBYTECODE=1
# Evita que Python haga buffering en la salida estándar (asegura que los logs fluyan a stdout)
ENV PYTHONUNBUFFERED=1

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instala dependencias del sistema que podrían ser necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia el archivo de dependencias al directorio de trabajo
COPY requirements.txt /app/

# Instala las dependencias de Python
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia el resto del código del proyecto al directorio de trabajo
COPY . /app/

# Expone el puerto 8000 (útil para el servicio API - Ordering)
EXPOSE 8000

# Comando por defecto. 
# En ECS/Fargate, este comando se sobrescribirá en la definición de la tarea 
# (por ej: python manage.py consume_orders o gunicorn patterns.wsgi).
# Se deja runserver como fallback para pruebas locales rápidas.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
