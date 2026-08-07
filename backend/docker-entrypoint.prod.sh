#!/bin/sh
# Entrée production : attente Postgres, seed initial, Gunicorn
set -e

echo "Attente PostgreSQL..."
TRIES=0
until python -c "
import os, psycopg2
from urllib.parse import urlparse
u = urlparse(os.environ['DATABASE_URL'].replace('+psycopg2', ''))
psycopg2.connect(host=u.hostname, port=u.port or 5432, user=u.username, password=u.password, dbname=u.path[1:])
"; do
  TRIES=$((TRIES + 1))
  if [ $((TRIES % 5)) -eq 0 ]; then
    echo "  … toujours en attente (${TRIES} tentatives)"
  fi
  sleep 2
done
echo "PostgreSQL prêt."

if [ "${RUN_SEED:-true}" = "true" ]; then
  echo "Initialisation des données (seed)..."
  flask --app run.py seed || echo "Seed ignoré (déjà initialisé)."
fi

WORKERS="${GUNICORN_WORKERS:-4}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"

echo "Démarrage Gunicorn (${WORKERS} workers)..."
exec gunicorn \
  --bind 0.0.0.0:5000 \
  --workers "${WORKERS}" \
  --timeout "${TIMEOUT}" \
  --access-logfile - \
  --error-logfile - \
  run:app
