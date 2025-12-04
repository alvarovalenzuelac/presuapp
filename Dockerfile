# 1. Usar una imagen base oficial de Python
FROM python:3.11-slim

# 2. Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Crear directorio de trabajo
WORKDIR /app

# 4. Instalar dependencias del sistema (gcc para compilar si es necesario)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 5. Instalar requerimientos
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copiar el código
COPY . /app/

# --- NUEVO PASO: RECOLECTAR ESTÁTICOS ---
# Usamos variables "dummy" (falsas) solo para que este comando funcione durante la construcción.
# WhiteNoise comprimirá los archivos aquí.
RUN SECRET_KEY=dummy_secret_key \
    DATABASE_URL=sqlite:////tmp/db.sqlite3 \
    python manage.py collectstatic --noinput

# 7. Exponer el puerto
ENV PORT 8080
EXPOSE 8080

# 8. Comando para iniciar
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 presuApp.wsgi:application