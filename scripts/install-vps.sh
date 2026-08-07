#!/bin/sh
# Installation complete sur VPS Ubuntu/Debian — une seule commande apres git clone.
#
# Usage (sur le VPS, en root ou avec sudo) :
#   curl -fsSL https://raw.githubusercontent.com/VOTRE-ORG/gestion-scolaire/main/scripts/install-vps.sh | sudo bash -s -- ecole.votredomaine.fr admin@votredomaine.fr
#
# Ou localement :
#   sudo ./scripts/install-vps.sh ecole.votredomaine.fr admin@votredomaine.fr
set -e

DOMAIN="${1:?Usage: install-vps.sh DOMAINE EMAIL}"
EMAIL="${2:?Usage: install-vps.sh DOMAINE EMAIL}"
APP_USER="${SUDO_USER:-$USER}"

# Dossier = racine du repo (ou parent du script)
SCRIPT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="${APP_DIR:-$SCRIPT_ROOT}"
cd "$APP_DIR"

# --- Secrets ---
echo "[3/6] Generation deploy/.env.prod…"
python3 scripts/init-env-prod.py --domain "$DOMAIN" --force
sed -i "s/^RUN_SEED=true/RUN_SEED=true/" deploy/.env.prod
sed -i "s|^SMTP_HOST=.*|SMTP_HOST=smtp.example.com|" deploy/.env.prod
sed -i "s|^SMTP_FROM=.*|SMTP_FROM=noreply@${DOMAIN}|" deploy/.env.prod

# --- Firewall ---
if command -v ufw >/dev/null 2>&1; then
  echo "[4/6] Firewall (ports 22, 80, 443)…"
  ufw allow 22/tcp 2>/dev/null || true
  ufw allow 80/tcp 2>/dev/null || true
  ufw allow 443/tcp 2>/dev/null || true
  ufw --force enable 2>/dev/null || true
fi

# --- Deploy stack ---
echo "[5/6] Demarrage stack prod…"
docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml up -d --build

echo "Attente health check…"
for i in $(seq 1 60); do
  curl -sf "http://127.0.0.1/api/health" >/dev/null 2>&1 && break
  sleep 3
done
curl -sf "http://127.0.0.1/api/health" && echo ""

# --- HTTPS ---
echo "[6/6] Certificat SSL + activation HTTPS…"
chmod +x scripts/setup-ssl.sh scripts/install-cron.sh
./scripts/setup-ssl.sh "$DOMAIN" "$EMAIL"
./scripts/install-cron.sh "$APP_DIR"

echo ""
echo "============================================"
echo "  DEPLOIEMENT TERMINE"
echo "  Site    : https://${DOMAIN}"
echo "  Admin   : admin@ecole.local / Admin123!"
echo "  Action  : changer le MDP admin immediatement"
echo "  Puis    : RUN_SEED=false dans deploy/.env.prod"
echo "============================================"
