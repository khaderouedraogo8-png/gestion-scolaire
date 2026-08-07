#!/bin/sh
# Déploiement production — usage : ./scripts/deploy-prod.sh [domaine]
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ENV_FILE="deploy/.env.prod"
COMPOSE="docker compose --env-file ${ENV_FILE} -f docker-compose.prod.yml"
DOMAIN="${1:-}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Création de ${ENV_FILE}…"
  if [ -n "$DOMAIN" ]; then
    python3 scripts/init-env-prod.py --domain "$DOMAIN"
  else
    python3 scripts/init-env-prod.py --http-port 80
  fi
fi

echo "Build et démarrage de la stack prod…"
$COMPOSE up -d --build

echo "Attente du backend…"
for i in $(seq 1 30); do
  if $COMPOSE exec -T backend python -c \
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/health')" 2>/dev/null; then
    break
  fi
  sleep 2
done

HTTP_PORT=$(grep -E '^HTTP_PORT=' "$ENV_FILE" | cut -d= -f2)
HTTP_PORT="${HTTP_PORT:-80}"
if [ "$HTTP_PORT" = "80" ]; then
  URL="http://localhost/api/health"
else
  URL="http://localhost:${HTTP_PORT}/api/health"
fi

echo "Health check : $URL"
curl -sf "$URL" && echo ""

echo ""
echo "Déploiement terminé."
echo "  Admin seed : admin@ecole.local / Admin123!"
echo "  Après 1ère connexion : RUN_SEED=false dans ${ENV_FILE}"
$COMPOSE ps
