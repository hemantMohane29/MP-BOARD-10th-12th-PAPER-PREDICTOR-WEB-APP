#!/usr/bin/env bash
set -o errexit

python -m pip install --upgrade pip

echo "=== Python: $(python --version) | Pip: $(pip --version) ==="

pip install -r requirements.txt

python manage.py collectstatic --no-input

# Make start.sh executable
chmod +x start.sh
