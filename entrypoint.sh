#!/bin/sh
set -e

echo "==> Running database migrations..."
python manage.py migrate --no-input

echo "==> Seeding initial user accounts..."
python manage.py seed_users || true

echo "==> Seeding requirement templates..."
python manage.py seed_requirement_templates || true

echo "==> Starting Gunicorn WSGI Server on port 8000..."
exec gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 120 etala_project.wsgi:application
