# Imagen de la aplicación Django (XBRecs).
#
# La base de datos (PostgreSQL + pgvector) se proporciona con
# `docker-compose.yml` (imagen `pgvector/pgvector:pg17`).
#
# Construcción:
#   docker build -t xrecommender .
#
# Arranque (con compose):
#   docker compose up --build

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencias primero (aprovecha la caché de capas).
COPY xrecommender/requirements.txt /app/xrecommender/requirements.txt
RUN pip install --no-cache-dir -r /app/xrecommender/requirements.txt

# Código de la aplicación.
COPY xrecommender /app/xrecommender

# Compila los assets estáticos (whitenoise) dentro de la imagen.
RUN cd /app/xrecommender && \
    SECRET_KEY=dummy-for-collectstatic DEBUG=0 \
    DATABASE_URL=postgres://user:pass@localhost:5432/placeholder \
    python manage.py collectstatic --noinput

EXPOSE 8000

# En producción: gunicorn + whitenoise (ver settings.py).
CMD ["gunicorn", "xrecommender.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120"]
