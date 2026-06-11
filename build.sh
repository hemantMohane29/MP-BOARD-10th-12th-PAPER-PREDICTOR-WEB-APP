#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

# Use /tmp for the SQLite DB during the build migrate step
# (Render's app directory is read-only at runtime)
export DB_PATH=/tmp/db.sqlite3
python manage.py migrate
