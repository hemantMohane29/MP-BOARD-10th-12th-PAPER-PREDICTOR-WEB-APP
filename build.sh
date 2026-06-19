#!/usr/bin/env bash
set -o errexit

# Upgrade pip FIRST using python -m (bypasses old pip limitations)
python -m pip install --upgrade pip

echo "=== Python: $(python --version) | Pip: $(pip --version) ==="

pip install -r requirements.txt

python manage.py collectstatic --no-input
