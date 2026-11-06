#!/bin/sh
# Applies database migrations (SaaS mode only) and starts the API.
set -e
if [ "$DEPLOYMENT_MODE" = "saas" ]; then
  /opt/venv/bin/alembic upgrade head
fi
exec /opt/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 5000 --proxy-headers --forwarded-allow-ips="*"
