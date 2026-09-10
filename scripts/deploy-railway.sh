#!/usr/bin/env bash
# Déploiement complet Railway (sans VPS) — Gestion Scolaire
# Prérequis :
#   1. railway CLI (curl -fsSL https://railway.com/install.sh | sh)
#   2. Authentification : export RAILWAY_API_TOKEN=...  (Account Token)
#      → https://railway.app/account/tokens
# Usage :
#   ./scripts/deploy-railway.sh
#   ./scripts/deploy-railway.sh --project-name mon-ecole

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PATH="${HOME}/.railway/bin:${PATH}"

PROJECT_NAME="gestion-scolaire"
SERVICE_NAME="web"
SKIP_SEED=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-name) PROJECT_NAME="$2"; shift 2 ;;
    --no-seed) SKIP_SEED=true; shift ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *) echo "Option inconnue: $1" >&2; exit 1 ;;
  esac
done

if ! command -v railway >/dev/null 2>&1; then
  echo "Installation Railway CLI…"
  curl -fsSL https://railway.com/install.sh | sh
  export PATH="${HOME}/.railway/bin:${PATH}"
fi

if [[ -z "${RAILWAY_API_TOKEN:-}${RAILWAY_TOKEN:-}" ]]; then
  if ! railway whoami >/dev/null 2>&1; then
    cat >&2 <<'EOF'
ERREUR: non authentifié sur Railway.

Créez un Account Token : https://railway.app/account/tokens
Puis :
  export RAILWAY_API_TOKEN='votre_token'
  ./scripts/deploy-railway.sh
EOF
    exit 1
  fi
fi

echo "==> Compte Railway"
railway whoami

gen_secret() {
  python3 -c "import secrets; print(secrets.token_urlsafe(32))"
}

JWT_SECRET_KEY="${JWT_SECRET_KEY:-$(gen_secret)}"
REFRESH_SECRET_KEY="${REFRESH_SECRET_KEY:-$(gen_secret)}"
ENCRYPTION_KEY="${ENCRYPTION_KEY:-$(gen_secret)}"
QR_HMAC_SECRET="${QR_HMAC_SECRET:-$(gen_secret)}"

# Lien existant ?
if railway status --json >/dev/null 2>&1; then
  echo "==> Projet déjà lié — réutilisation"
else
  echo "==> Création du projet « ${PROJECT_NAME} »"
  railway init --name "${PROJECT_NAME}" --json >/tmp/railway-init.json || {
    # Si le nom existe déjà, tenter un lien interactif non — créer avec suffixe
    PROJECT_NAME="${PROJECT_NAME}-$(date +%s)"
    echo "    retry avec ${PROJECT_NAME}"
    railway init --name "${PROJECT_NAME}" --json >/tmp/railway-init.json
  }
fi

echo "==> PostgreSQL"
if railway status --json 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
# best-effort: toujours tenter add; ignore si déjà présent
sys.exit(0)
" 2>/dev/null; then
  railway add --database postgres --json >/tmp/railway-pg.json 2>/tmp/railway-pg.err || {
    echo "    (Postgres peut déjà exister — on continue)"
    cat /tmp/railway-pg.err >&2 || true
  }
fi

echo "==> Service ${SERVICE_NAME}"
railway add --service "${SERVICE_NAME}" --json >/tmp/railway-svc.json 2>/tmp/railway-svc.err || {
  echo "    (Service peut déjà exister — on continue)"
  cat /tmp/railway-svc.err >&2 || true
}

# Nom du service Postgres (souvent « Postgres »)
PG_SERVICE="$(railway status --json 2>/dev/null | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    print('Postgres'); sys.exit(0)
# shapes vary — chercher un service type database / nom Postgres
services = d.get('services') or d.get('project',{}).get('services') or []
if isinstance(services, dict):
    services = list(services.values()) if services else []
names=[]
for s in services:
    if isinstance(s, dict):
        n=s.get('name') or s.get('serviceName') or ''
        names.append(n)
for n in names:
    if n and ('postgres' in n.lower() or n.lower()=='pg'):
        print(n); break
else:
    print('Postgres')
" 2>/dev/null || echo Postgres)"

echo "    Référence Postgres: ${PG_SERVICE}"

echo "==> Variables d'environnement"
railway variable set \
  --service "${SERVICE_NAME}" \
  --skip-deploys \
  "FLASK_ENV=production" \
  "RUN_SEED=$([ "$SKIP_SEED" = true ] && echo false || echo true)" \
  "GUNICORN_WORKERS=2" \
  "GUNICORN_TIMEOUT=120" \
  "UPLOAD_FOLDER=/app/uploads" \
  "JWT_SECRET_KEY=${JWT_SECRET_KEY}" \
  "REFRESH_SECRET_KEY=${REFRESH_SECRET_KEY}" \
  "ENCRYPTION_KEY=${ENCRYPTION_KEY}" \
  "QR_HMAC_SECRET=${QR_HMAC_SECRET}" \
  "DATABASE_URL=\${{${PG_SERVICE}.DATABASE_URL}}" \
  "CORS_ORIGINS=https://placeholder.up.railway.app"

echo "==> Volume uploads"
railway volume add --service "${SERVICE_NAME}" --mount-path /app/uploads --json >/tmp/railway-vol.json 2>/tmp/railway-vol.err || {
  echo "    (Volume peut déjà exister — on continue)"
}

echo "==> Déploiement du code (Dockerfile Railway)"
railway up --service "${SERVICE_NAME}" --detach -y --ci

echo "==> Domaine public"
DOMAIN_JSON="$(railway domain --service "${SERVICE_NAME}" --port 8080 --json 2>/dev/null || true)"
PUBLIC_URL="$(printf '%s' "$DOMAIN_JSON" | python3 -c "
import json,sys
raw=sys.stdin.read().strip()
if not raw:
    sys.exit(0)
try:
    d=json.loads(raw)
except Exception:
    sys.exit(0)
# formats possibles
for key in ('domain','url','hostname'):
    if isinstance(d, dict) and d.get(key):
        v=d[key]
        if not str(v).startswith('http'):
            v='https://'+str(v)
        print(v); break
else:
    if isinstance(d, list) and d:
        item=d[0]
        v=item.get('domain') or item.get('url') or ''
        if v and not str(v).startswith('http'):
            v='https://'+str(v)
        print(v)
" 2>/dev/null || true)"

if [[ -z "${PUBLIC_URL}" ]]; then
  # fallback list
  PUBLIC_URL="$(railway domain list --service "${SERVICE_NAME}" --json 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
items=d if isinstance(d,list) else d.get('domains') or d.get('serviceDomains') or []
for item in items:
    v=item.get('domain') or item.get('host') or ''
    if v:
        print('https://'+v if not str(v).startswith('http') else v)
        break
" 2>/dev/null || true)"
fi

if [[ -n "${PUBLIC_URL}" ]]; then
  echo "==> CORS_ORIGINS=${PUBLIC_URL}"
  railway variable set --service "${SERVICE_NAME}" "CORS_ORIGINS=${PUBLIC_URL}"
else
  echo "ATTENTION: domaine non détecté — définissez CORS_ORIGINS manuellement après Generate Domain." >&2
fi

echo
echo "=============================================="
echo " Déploiement lancé."
echo " Projet : ${PROJECT_NAME}"
echo " Service: ${SERVICE_NAME}"
[[ -n "${PUBLIC_URL}" ]] && echo " URL    : ${PUBLIC_URL}"
echo " Compte seed : admin@ecole.local / Admin123!"
echo " Puis : railway variable set --service ${SERVICE_NAME} RUN_SEED=false"
echo " Logs : railway logs --service ${SERVICE_NAME}"
echo "=============================================="
