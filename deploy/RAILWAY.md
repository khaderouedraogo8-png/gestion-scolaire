# Déploiement Railway (sans VPS)

Hébergement managé : **une seule image** (Nginx + Gunicorn) + **PostgreSQL Railway**.
HTTPS et domaine `*.up.railway.app` inclus — pas de serveur à administrer.

## Architecture

```
Internet (HTTPS Railway)
        │
        ▼
  Service « web »  (deploy/Dockerfile.railway)
   ├── Nginx  → frontend React + proxy /api
   └── Gunicorn → Flask API
        │
        ├── PostgreSQL (plugin Railway)
        └── Redis (optionnel — rate limiting)
```

Même origine `/` + `/api` → cookies refresh `SameSite=Strict` inchangés.

## Prérequis

1. Compte [Railway](https://railway.app)
2. Repo GitHub connecté (`gestion-scolaire`)
3. Carte bancaire parfois demandée selon le plan (crédits gratuits souvent inclus)

## Déploiement pas à pas

### 1. Créer le projet

1. Railway → **New Project** → **Deploy from GitHub repo**
2. Choisir ce dépôt et la branche `main` (ou la branche de cette PR)
3. Railway détecte `railway.toml` → build via `deploy/Dockerfile.railway`

### 2. Ajouter PostgreSQL

1. Dans le projet → **+ New** → **Database** → **PostgreSQL**
2. Sur le service **web** → **Variables** → ajouter une référence :

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

(Remplacez `Postgres` par le nom exact du service Postgres s’il diffère.)

### 3. Variables obligatoires

Sur le service web, définir :

| Variable | Exemple / notes |
|----------|-----------------|
| `FLASK_ENV` | `production` |
| `JWT_SECRET_KEY` | `openssl rand -base64 32` |
| `REFRESH_SECRET_KEY` | autre secret aléatoire |
| `ENCRYPTION_KEY` | 32+ caractères aléatoires |
| `QR_HMAC_SECRET` | secret aléatoire |
| `CORS_ORIGINS` | URL publique Railway, ex. `https://web-production-xxxx.up.railway.app` |
| `RUN_SEED` | `true` au 1er déploiement, puis `false` |
| `GUNICORN_WORKERS` | `2` (recommandé Hobby) |

Génération rapide :

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Redis (optionnel)

**+ New** → **Database** → **Redis**, puis :

```
REDIS_URL=${{Redis.REDIS_URL}}
```

Sans Redis, le rate limiting utilise la mémoire (acceptable pour un établissement).

### 5. Networking public

Sur le service web → **Settings** → **Networking** → **Generate Domain**.

Copiez l’URL HTTPS dans `CORS_ORIGINS`, puis redéployez.

### 6. Volume uploads (recommandé)

**Settings** → **Volumes** → monter un volume sur `/app/uploads`
(sinon les fichiers uploadés sont perdus à chaque redéploiement).

### 7. Premier accès

1. Ouvrir l’URL Railway
2. Connexion seed : `admin@ecole.local` / `Admin123!`
3. **Changer le mot de passe immédiatement**
4. Passer `RUN_SEED=false` et redéployer

## Domaine personnalisé

Settings → Networking → **Custom Domain** → suivre les instructions DNS Railway.
Mettre à jour `CORS_ORIGINS` avec `https://votre-domaine.fr`.

## CLI (optionnel)

```bash
npm i -g @railway/cli
railway login
railway link
railway up
railway variables
railway logs
```

## Coût indicatif

- Hobby / Trial : suffisant pour démo et petit établissement
- Postgres inclus dans le projet
- Surveiller l’usage RAM (image Nginx+Gunicorn+WeasyPrint ≈ 512 Mo–1 Go)

## Dépannage

| Symptôme | Action |
|----------|--------|
| Build échoue | Vérifier les logs Build ; Dockerfile = `deploy/Dockerfile.railway` |
| Crash au boot « secrets » | Variables `JWT_*` / `ENCRYPTION_KEY` / `QR_HMAC_SECRET` manquantes |
| Crash `DATABASE_URL` | Référence `${{Postgres.DATABASE_URL}}` absente |
| Login cookie KO | `CORS_ORIGINS` doit être exactement l’URL HTTPS (sans slash final) |
| Healthcheck timeout | Augmenter le timeout (schéma + seed au 1er boot) |

## Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `railway.toml` | Builder + healthcheck |
| `deploy/Dockerfile.railway` | Image unique |
| `deploy/railway-entrypoint.sh` | Schéma, seed, Nginx+Gunicorn |
| `deploy/nginx.railway.conf.template` | Proxy `/api` + SPA |

## Alternative sans cloud

Prod locale + tunnel Cloudflare : `scripts/tunnel-public.ps1` (démo temporaire uniquement).
