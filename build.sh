#!/usr/bin/env bash
set -o errexit

echo "=== Python version: $(python --version) ==="
echo "=== Pip version: $(pip --version) ==="

# Upgrade pip first to ensure it can resolve modern packages
pip install --upgrade pip

pip install -r requirements.txt

python manage.py collectstatic --no-input

export DB_PATH=/tmp/db.sqlite3
python manage.py migrate
