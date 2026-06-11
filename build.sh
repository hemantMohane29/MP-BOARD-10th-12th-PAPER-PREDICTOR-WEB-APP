#!/usr/bin/env bash
set -o errexit

# Upgrade pip FIRST using python -m (bypasses old pip limitations)
python -m pip install --upgrade pip

echo "=== Python: $(python --version) | Pip: $(pip --version) ==="

pip install -r requirements.txt

python manage.py collectstatic --no-input

export DB_PATH=/tmp/db.sqlite3
python manage.py migrate
