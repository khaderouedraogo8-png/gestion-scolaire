#!/bin/sh
# Obtient un certificat Let's Encrypt et active HTTPS (nginx TLS).
# Usage : sudo ./scripts/setup-ssl.sh votre-domaine.fr admin@votre-domaine.fr
set -e

DOMAIN="${1:?Usage: setup-ssl.sh DOMAINE EMAIL}"
EMAIL="${2:?Usage: setup-ssl.sh DOMAINE EMAIL}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ENV_FILE="deploy/.env.prod"
COMPOSE="docker compose --env-file ${ENV_FILE} -f docker-compose.prod.yml -f docker-compose.prod.tls.yml"

if [ ! -f "$ENV_FILE" ]; then
  echo "Créez d'abord deploy/.env.prod (scripts/init-env-prod.py --domain ${DOMAIN})"
  exit 1
fi

echo "Arrêt nginx pour libérer le port 80…"
docker compose --env-file "$ENV_FILE" -f docker-compose.prod.yml stop nginx 2>/dev/null || true

if ! command -v certbot >/dev/null 2>&1; then
  echo "Installation de certbot…"
  apt-get update && apt-get install -y certbot
fi

certbot certonly --standalone -d "$DOMAIN" --email "$EMAIL" --agree-tos --non-interactive

# Met à jour CORS et domaine dans .env.prod
sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=https://${DOMAIN}|" "$ENV_FILE"
sed -i "s|^DOMAIN=.*|DOMAIN=${DOMAIN}|" "$ENV_FILE" 2>/dev/null || echo "DOMAIN=${DOMAIN}" >> "$ENV_FILE"

export DOMAIN
echo "Redémarrage avec TLS…"
$COMPOSE up -d --build nginx

echo ""
echo "HTTPS actif sur https://${DOMAIN}"
echo "Renouvellement (cron root) :"
echo "  0 3 * * * certbot renew --quiet && cd ${ROOT} && ${COMPOSE} restart nginx"
