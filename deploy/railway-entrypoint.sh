#!/bin/sh
# Entrée Railway : normalise l'URL Postgres, applique le schéma si besoin, seed, Nginx+Gunicorn
set -e

PORT="${PORT:-8080}"
export PORT

# --- DATABASE_URL Railway (postgres://…) → dialecte SQLAlchemy/psycopg2 ---
if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERREUR: DATABASE_URL est obligatoire (ajoutez le plugin PostgreSQL Railway)." >&2
  exit 1
fi

case "$DATABASE_URL" in
  postgres://*)
    export DATABASE_URL="postgresql+psycopg2://${DATABASE_URL#postgres://}"
    ;;
  postgresql://*)
    export DATABASE_URL="postgresql+psycopg2://${DATABASE_URL#postgresql://}"
    ;;
esac

# URL libpq (sans +psycopg2) pour psql / attente connexion
PSQL_URL=$(python -c "
import os
u = os.environ['DATABASE_URL'].replace('postgresql+psycopg2://', 'postgresql://', 1)
print(u)
")

# Redis Railway optionnel → rate limiting
if [ -z "${RATELIMIT_STORAGE_URI:-}" ]; then
  if [ -n "${REDIS_URL:-}" ]; then
    export RATELIMIT_STORAGE_URI="$REDIS_URL"
  else
    export RATELIMIT_STORAGE_URI="memory://"
    echo "Info: pas de Redis — rate limiting en mémoire (OK pour un petit établissement)."
  fi
fi

echo "Attente PostgreSQL..."
TRIES=0
until python -c "
import os, psycopg2
from urllib.parse import urlparse
u = urlparse(os.environ['DATABASE_URL'].replace('+psycopg2', ''))
psycopg2.connect(
    host=u.hostname,
    port=u.port or 5432,
    user=u.username,
    password=u.password,
    dbname=(u.path or '/').lstrip('/') or 'postgres',
    connect_timeout=3,
)
"; do
  TRIES=$((TRIES + 1))
  if [ "$TRIES" -ge 60 ]; then
    echo "ERREUR: PostgreSQL injoignable après ${TRIES} tentatives." >&2
    exit 1
  fi
  if [ $((TRIES % 5)) -eq 0 ]; then
    echo "  … toujours en attente (${TRIES} tentatives)"
  fi
  sleep 2
done
echo "PostgreSQL prêt."

SCHEMA_FILE="/app/database/schema_v2_mono_etablissement.sql"
TABLE_EXISTS=$(psql "$PSQL_URL" -tAc "SELECT to_regclass('public.etablissement') IS NOT NULL;" | tr -d '[:space:]')

if [ "$TABLE_EXISTS" != "t" ] && [ "$TABLE_EXISTS" != "true" ]; then
  echo "Application du schéma SQL..."
  psql "$PSQL_URL" -v ON_ERROR_STOP=1 -f "$SCHEMA_FILE"
  echo "Marquage Alembic (stamp head)..."
  (cd /app && alembic stamp head) || echo "Alembic stamp ignoré."
else
  echo "Schéma déjà présent — migrations Alembic éventuelles..."
  (cd /app && alembic upgrade head) || echo "Alembic upgrade ignoré (schéma déjà à jour)."
fi

if [ "${RUN_SEED:-true}" = "true" ]; then
  echo "Initialisation des données (seed)..."
  flask --app run.py seed || echo "Seed ignoré (déjà initialisé)."
fi

# Nginx écoute sur $PORT (Railway)
envsubst '${PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf
# Désactive le default package si présent
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

WORKERS="${GUNICORN_WORKERS:-2}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"

echo "Démarrage Gunicorn (${WORKERS} workers) sur 127.0.0.1:5000..."
gunicorn \
  --bind 127.0.0.1:5000 \
  --workers "${WORKERS}" \
  --timeout "${TIMEOUT}" \
  --access-logfile - \
  --error-logfile - \
  run:app &
GUNICORN_PID=$!

# Attendre que l'API réponde avant Nginx
TRIES=0
until curl -sf http://127.0.0.1:5000/api/health >/dev/null; do
  TRIES=$((TRIES + 1))
  if [ "$TRIES" -ge 30 ]; then
    echo "ERREUR: Gunicorn n'a pas démarré." >&2
    kill "$GUNICORN_PID" 2>/dev/null || true
    exit 1
  fi
  # Si Gunicorn est mort, sortir immédiatement
  if ! kill -0 "$GUNICORN_PID" 2>/dev/null; then
    echo "ERREUR: Gunicorn s'est arrêté prématurément." >&2
    exit 1
  fi
  sleep 1
done

echo "Démarrage Nginx sur le port ${PORT}..."
nginx -g 'daemon off;' &
NGINX_PID=$!

term_handler() {
  echo "Arrêt..."
  kill -TERM "$NGINX_PID" "$GUNICORN_PID" 2>/dev/null || true
  wait "$NGINX_PID" "$GUNICORN_PID" 2>/dev/null || true
}
trap term_handler TERM INT

# Sortir si l'un des deux processus meurt
while kill -0 "$GUNICORN_PID" 2>/dev/null && kill -0 "$NGINX_PID" 2>/dev/null; do
  sleep 2
done

echo "Un processus s'est arrêté — redémarrage nécessaire." >&2
term_handler
exit 1
