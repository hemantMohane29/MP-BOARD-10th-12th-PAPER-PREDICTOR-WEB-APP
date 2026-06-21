#!/usr/bin/env bash
set -o errexit

echo "=== Running migrations ==="
python manage.py migrate --no-input
echo "=== Migrations complete ==="

echo "=== Creating admin account ==="
python manage.py shell -c "
from django.contrib.auth.models import User
email = 'hemantmohane29@gmail.com'
password = 'Admin@12'
if not User.objects.filter(username=email).exists():
    User.objects.create_superuser(username=email, email=email, password=password)
    print('Admin created successfully')
else:
    user = User.objects.get(username=email)
    user.set_password(password)
    user.is_superuser = True
    user.is_staff = True
    user.save()
    print('Admin updated successfully')
"

exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 120
