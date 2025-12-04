# 1. Usar una imagen base oficial de Python (Ligera y segura)
FROM python:3.11-slim

# 2. Evitar que Python genere archivos .pyc y permitir logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Crear directorio de trabajo dentro del contenedor
WORKDIR /app

# 4. Instalar dependencias del sistema necesarias para PostgreSQL y otros
# (gcc y libpq-dev son necesarios para compilar psycopg2 si se usa la versión binaria)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 5. Copiar los requerimientos e instalarlos
# Hacemos esto PRIMERO para aprovechar la caché de Docker (si no cambian las librerías, no reinstala)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copiar el resto del código del proyecto
COPY . /app/

# 7. Exponer el puerto donde correrá la app (Cloud Run usa 8080 por defecto)
PORT 8080
EXPOSE 8080

# 8. Comando para iniciar el servidor de producción (Gunicorn)
# Reemplaza 'presuApp' con el nombre de la carpeta donde está tu wsgi.py
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 presuApp.wsgi:application