# Guide de déploiement production — Gestion Scolaire

> **Sans VPS (recommandé)** : voir [RAILWAY.md](./RAILWAY.md) — hébergement managé Railway (HTTPS inclus).

Ce document décrit le déploiement **Docker Compose** (PC local ou serveur).

## Architecture prod

```
Internet → Nginx (:80/443)
              ├── /          → React (fichiers statiques)
              └── /api/*     → Gunicorn / Flask (backend:5000)
                                    ├── PostgreSQL
                                    └── Redis (rate limiting)
```

Stack : `docker compose -f docker-compose.prod.yml` (projet Docker **`gestion-prod`**, isolé du dev local)

> **Dev local** : le compose dev (`docker-compose.yml`) et le compose prod partagent le même dépôt mais **pas** les volumes ni les noms de conteneurs. Ne lancez pas les deux sur le même port sans `HTTP_PORT` différent (ex. `8080` en prod test).

---

## Prérequis (Docker local ou serveur)

- Ubuntu 22.04+ ou Debian 12+
- Docker Engine + Docker Compose v2
- Nom de domaine pointant vers l’IP du serveur (pour HTTPS)
- 2 Go RAM minimum (4 Go recommandé)

---

## 1. Installation Docker (Ubuntu)

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Reconnexion SSH requise
```

---

## 2. Déployer l’application

```bash
git clone <votre-repo> gestion-scolaire
cd gestion-scolaire

# Générer deploy/.env.prod avec secrets aléatoires
python3 scripts/init-env-prod.py --domain votre-domaine.fr

# Ou déploiement en une commande (Linux)
chmod +x scripts/deploy-prod.sh
./scripts/deploy-prod.sh votre-domaine.fr

# Manuellement
docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml up -d --build
docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml ps
curl http://localhost/api/health
```

Le site est accessible sur le port **80**.

Compte admin initial (seed) : `admin@ecole.local` / `Admin123!` — **changez le mot de passe immédiatement**.

Après la première connexion réussie :

```bash
# Désactiver le seed automatique aux prochains redémarrages
# Dans deploy/.env.prod : RUN_SEED=false
docker compose -f docker-compose.prod.yml up -d
```

---

## 3. HTTPS avec Let’s Encrypt (Certbot)

```bash
# Automatisé (Ubuntu VPS, domaine déjà pointé vers le serveur)
chmod +x scripts/setup-ssl.sh
sudo ./scripts/setup-ssl.sh votre-domaine.fr admin@votre-domaine.fr

# Manuel : certificat puis override TLS
docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml stop nginx
sudo certbot certonly --standalone -d votre-domaine.fr
# DOMAIN=votre-domaine.fr dans deploy/.env.prod
docker compose --env-file deploy/.env.prod \
  -f docker-compose.prod.yml -f docker-compose.prod.tls.yml up -d nginx
```

Renouvellement automatique (cron root) :

```cron
0 3 * * * certbot renew --quiet && cd /chemin/gestion-scolaire && docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml -f docker-compose.prod.tls.yml restart nginx
```

---

## 4. Sauvegardes PostgreSQL

```bash
# Sauvegarde manuelle
docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml --profile backup run --rm backup

# Cron quotidien (2h du matin)
0 2 * * * cd /chemin/gestion-scolaire && docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml --profile backup run --rm backup
```

Les dumps sont dans `./backups/` (rotation 30 jours).

**Test de restauration trimestriel recommandé** :

```bash
chmod +x scripts/restore-db.sh
./scripts/restore-db.sh backups/gestion_scolaire_XXXXXX.sql.gz
```

---

## 5. Tâches planifiées (relances, notifications)

Installation automatique des crons (Linux) :

```bash
chmod +x scripts/install-cron.sh
sudo ./scripts/install-cron.sh /chemin/gestion-scolaire
```

Ou manuellement :

```cron
# Relances arriérés (lundi 8h)
0 8 * * 1 docker compose --env-file /chemin/gestion-scolaire/deploy/.env.prod -f /chemin/gestion-scolaire/docker-compose.prod.yml exec -T backend flask --app run.py relancer-arrieres

# Traitement file notifications (toutes les 15 min)
*/15 * * * * docker compose --env-file /chemin/gestion-scolaire/deploy/.env.prod -f /chemin/gestion-scolaire/docker-compose.prod.yml exec -T backend flask --app run.py traiter-notifications
```

---

## 6. Redis (rate limiting prod)

La stack prod inclut **Redis** pour partager les compteurs de rate limiting entre les workers Gunicorn.

```bash
curl http://localhost:8080/api/health
# → {"status":"ok","redis":"ok"}
```

Variable : `RATELIMIT_STORAGE_URI=redis://redis:6379/0` (déjà dans `env.prod.example`).

---

## 7. Mises à jour

```bash
cd gestion-scolaire
git pull
docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml up -d --build
```

---

## Tests de charge

```bash
# Headless 30s, 10 utilisateurs
docker exec gestion-prod-backend-1 python scripts/run_load_test.py --host http://127.0.0.1:5000

# Ou depuis l'hote (prod via nginx)
cd backend && pip install locust && python scripts/run_load_test.py --host http://localhost:8080
```

---

## Variables d’environnement essentielles

| Variable | Description |
|----------|-------------|
| `POSTGRES_PASSWORD` | Mot de passe DB |
| `JWT_SECRET_KEY` | Secret JWT (32+ car.) |
| `REFRESH_SECRET_KEY` | Secret refresh tokens |
| `ENCRYPTION_KEY` | Chiffrement notes médicales (32 car.) |
| `CORS_ORIGINS` | URL publique du frontend |
| `RATELIMIT_STORAGE_URI` | Redis pour rate limiting (`redis://redis:6379/0`) |
| `SMTP_*` | Envoi emails parents |
| `SMS_API_URL` | API SMS (optionnel) |

---

## Dépannage

| Problème | Solution |
|----------|----------|
| Backend bloqué « Attente PostgreSQL » | Dev et prod partageaient le volume : utiliser le projet `gestion-prod` (compose prod) avec volumes dédiés |
| 502 Bad Gateway | `docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml logs backend` |
| Cookie refresh perdu | Vérifier HTTPS + `X-Forwarded-Proto` (ProxyFix activé en prod) |
| PDF ne se génère pas | Vérifier WeasyPrint dans l’image backend (libpango installé) |
| Seed re-exécuté | `RUN_SEED=false` dans `.env.prod` |

---

## Dev vs Prod

| | Dev | Prod |
|---|-----|------|
| Compose | `docker compose up` | `docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml up` |
| Projet Docker | `gestion-scolaire` | `gestion-prod` |
| Frontend | Vite HMR :5173 | Nginx static :80 (8080 en test local) |
| Backend | Flask debug | Gunicorn 4 workers |
| Secrets | Valeurs dev | `.env.prod` sécurisé |
