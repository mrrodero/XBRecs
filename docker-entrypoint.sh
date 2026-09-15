#!/bin/sh
# Punto de entrada del contenedor de la aplicación:
# aplica las migraciones y arranca el comando indicado (gunicorn).
set -e

cd /app/xrecommender
python manage.py migrate --noinput

exec "$@"
