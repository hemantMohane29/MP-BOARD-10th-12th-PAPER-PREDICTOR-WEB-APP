#!/usr/bin/env bash
set -o errexit

echo "=== Running migrations ==="
python manage.py migrate --no-input

echo "=== Starting gunicorn ==="
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
