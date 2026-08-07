#!/bin/sh
# Restaure une sauvegarde PostgreSQL dans la stack prod.
# Usage : ./scripts/restore-db.sh backups/gestion_scolaire_YYYYMMDD_HHMMSS.sql.gz
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DUMP="${1:?Usage: restore-db.sh fichier.sql.gz}"
ENV_FILE="deploy/.env.prod"
COMPOSE="docker compose --env-file ${ENV_FILE} -f docker-compose.prod.yml"

if [ ! -f "$DUMP" ]; then
  echo "Fichier introuvable : $DUMP"
  exit 1
fi

echo "ATTENTION : cette opération écrase la base prod actuelle."
printf "Continuer ? [y/N] "
read -r CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
  echo "Annulé."
  exit 0
fi

echo "Arrêt du backend…"
$COMPOSE stop backend

echo "Restauration de ${DUMP}…"
gunzip -c "$DUMP" | $COMPOSE exec -T postgres psql -U gestion -d gestion_scolaire

echo "Redémarrage du backend…"
$COMPOSE start backend

echo "Health check…"
for i in $(seq 1 20); do
  if curl -sf "http://localhost:${HTTP_PORT:-8080}/api/health" >/dev/null 2>&1; then
    echo "Restauration terminée."
    exit 0
  fi
  sleep 2
done

echo "Backend non disponible — vérifiez les logs : $COMPOSE logs backend"
exit 1
