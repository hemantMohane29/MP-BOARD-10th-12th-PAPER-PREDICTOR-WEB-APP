#!/usr/bin/env bash
set -o errexit

python -m pip install --upgrade pip

echo "=== Python: $(python --version) | Pip: $(pip --version) ==="

pip install -r requirements.txt

echo "=== Running collectstatic ==="
python manage.py collectstatic --no-input --clear

echo "=== Verifying static files collected ==="
ls -la staticfiles/css/ || echo "WARNING: staticfiles/css/ missing!"
ls staticfiles/css/global_animations.css && echo "OK: global_animations.css found" || echo "ERROR: global_animations.css MISSING"

chmod +x start.sh
