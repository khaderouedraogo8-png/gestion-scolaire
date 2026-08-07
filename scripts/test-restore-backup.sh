#!/bin/sh
# Test restauration backup sans interaction (CI / validation)
# Usage: ./scripts/test-restore-backup.sh [fichier.sql.gz]
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DUMP="${1:-$(ls -t backups/gestion_scolaire_*.sql.gz 2>/dev/null | head -1)}"
ENV_FILE="deploy/.env.prod"
COMPOSE="docker compose --env-file ${ENV_FILE} -f docker-compose.prod.yml"

if [ -z "$DUMP" ] || [ ! -f "$DUMP" ]; then
  echo "Aucun backup trouve dans backups/"
  exit 1
fi

echo "Test restauration depuis ${DUMP}…"
$COMPOSE stop backend
gunzip -c "$DUMP" | $COMPOSE exec -T postgres psql -U gestion -d gestion_scolaire -q
$COMPOSE start backend

for i in $(seq 1 30); do
  if curl -sf "http://localhost:${HTTP_PORT:-8080}/api/health" >/dev/null 2>&1; then
    echo "Restauration OK — health check passed"
    exit 0
  fi
  sleep 2
done

echo "Backend non disponible apres restauration"
exit 1
