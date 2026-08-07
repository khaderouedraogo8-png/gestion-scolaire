#!/bin/sh
# Installe les tâches cron pour backup, relances, notifications et renouvellement SSL.
# Usage : sudo ./scripts/install-cron.sh /chemin/vers/gestion-scolaire
set -e

ROOT="${1:?Usage: install-cron.sh /chemin/gestion-scolaire}"
ROOT="$(cd "$ROOT" && pwd)"
ENV_FILE="${ROOT}/deploy/.env.prod"
COMPOSE="docker compose --env-file ${ENV_FILE} -f ${ROOT}/docker-compose.prod.yml"
COMPOSE_TLS="${COMPOSE} -f ${ROOT}/docker-compose.prod.tls.yml"

MARKER="# gestion-scolaire-cron"
TMP="$(mktemp)"

cat > "$TMP" <<EOF
${MARKER}
0 2 * * * cd ${ROOT} && ${COMPOSE} --profile backup run --rm backup >> ${ROOT}/backups/cron.log 2>&1
0 8 * * 1 cd ${ROOT} && ${COMPOSE} exec -T backend flask --app run.py relancer-arrieres >> ${ROOT}/backups/relances.log 2>&1
*/15 * * * * cd ${ROOT} && ${COMPOSE} exec -T backend flask --app run.py traiter-notifications >> ${ROOT}/backups/notifications.log 2>&1
0 3 * * * certbot renew --quiet && cd ${ROOT} && ${COMPOSE_TLS} restart nginx >> ${ROOT}/backups/certbot.log 2>&1
EOF

# Fusionne avec crontab existante (sans doublons)
( crontab -l 2>/dev/null | grep -v "$MARKER" | grep -v "gestion-scolaire" || true
  cat "$TMP"
) | crontab -

rm -f "$TMP"
mkdir -p "${ROOT}/backups"
echo "Cron installé pour ${ROOT}"
crontab -l | grep -A4 "$MARKER"
