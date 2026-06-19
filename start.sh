#!/usr/bin/env bash
set -o errexit

# Create session directory for file-based sessions
mkdir -p /tmp/django_sessions

echo "=== Running migrations ==="
export DB_PATH=/tmp/db.sqlite3
python manage.py migrate --no-input
echo "=== Migrations complete ==="

exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 120
