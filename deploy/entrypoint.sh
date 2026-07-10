#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for Postgres..."
until pg_isready -d "${LOGISTICS_DATABASE_URL}" >/dev/null 2>&1; do
  sleep 2
done
echo "Postgres is ready. Bootstrapping schema + seed..."
python -m logistics_agents.data.bootstrap
echo "Starting API on :80"
exec uvicorn logistics_agents.api.asgi:app --host 0.0.0.0 --port 80
