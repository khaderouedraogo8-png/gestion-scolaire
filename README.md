# Gestion Scolaire

Plateforme web complète de gestion scolaire : élèves, notes, bulletins, finance, emploi du temps, absences, documents, notifications et tableau de bord.

**Stack** : Flask + React/Vite + PostgreSQL + Redis + Nginx (prod)

---

## Démarrage rapide (sans Docker — natif Windows)

```powershell
cd gestion-scolaire
.\scripts\install-native.ps1    # PostgreSQL 17, Python 3.12, Node, seed
.\scripts\start-native.ps1      # Backend :5000 + Frontend :5173
```

**Prérequis** : Python 3.12 (`py -3.12`), Node.js 20+, winget.

| Composant | Détail |
|-----------|--------|
| PostgreSQL | Port 5432, user `gestion` / `gestion_dev`, DB `gestion_scolaire` |
| Superuser PG | Mot de passe par défaut winget : `postgres` |
| Redis | Non requis en dev (`memory://`) |
| PDF (WeasyPrint) | MSYS2 Pango (`C:\msys64\mingw64\bin`) — installé par `install-native.ps1` |

---

## Démarrage rapide (Docker — développement)

```powershell
cd gestion-scolaire
docker compose up -d
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API | http://localhost:5000/api/health |
| Swagger (dev) | http://localhost:5000/api/docs |

### Comptes de démonstration

| Rôle | Email | Mot de passe |
|------|-------|--------------|
| Administrateur | `admin@ecole.local` | `Admin123!` |
| Directeur | `directeur@ecole.local` | `Directeur123!` |
| Secrétariat | `secretariat@ecole.local` | `Secret123!` |
| Comptable | `compta@ecole.local` | `Compta123!` |
| Enseignant | `enseignant@ecole.local` | `Enseignant123!` |
| Parent | `parent@demo.local` | `Parent123!` |

Voir [docs/COMPTES-DEMO.md](docs/COMPTES-DEMO.md) pour la liste complète.

---

## Production locale (test)

```powershell
docker compose --env-file deploy/.env.prod -f docker-compose.prod.yml up -d --build
```

| Service | URL |
|---------|-----|
| Application | http://localhost:8080 |
| API health | http://localhost:8080/api/health |
| Mailhog (emails) | http://localhost:8025 |

---

## Tests

```powershell
# Validation mode natif (sans Docker)
.\scripts\validate-native.ps1

# Validation complète (prod + dev Docker)
.\scripts\validate-all.ps1

# Setup from scratch (dev + prod + seed)
.\scripts\setup-local.ps1

# Backend (natif)
cd backend && .\.venv\Scripts\python.exe -m pytest tests/integration/ -q

# Backend (Docker)
docker exec gestion-scolaire-backend-1 python -m pytest tests/integration/ -q

# Frontend unitaires
cd frontend && npm run test -- --run

# E2E Playwright (dev)
cd frontend && npx playwright test

# E2E prod (port 8080)
cd frontend && npx playwright test -c playwright.prod.config.js
```

---

## Déploiement (sans VPS) — Railway

Guide complet : [deploy/RAILWAY.md](deploy/RAILWAY.md)

1. Créer un projet Railway depuis ce repo GitHub  
2. Ajouter PostgreSQL + lier `DATABASE_URL`  
3. Renseigner les secrets (`deploy/env.railway.example`)  
4. **Generate Domain** → mettre l’URL dans `CORS_ORIGINS`

Alternative locale temporaire : [scripts/tunnel-public.ps1](scripts/tunnel-public.ps1) (Cloudflare Tunnel).

Déploiement Docker classique (VPS optionnel) : [deploy/DEPLOIEMENT.md](deploy/DEPLOIEMENT.md)

---

## Documentation

| Fichier | Contenu |
|---------|---------|
| [docs/dossier-technique-complet.md](docs/dossier-technique-complet.md) | Spécifications techniques |
| [docs/GUIDE-UTILISATEUR.md](docs/GUIDE-UTILISATEUR.md) | Guide admin / utilisateurs |
| [docs/INSTALL-TESTEUR.md](docs/INSTALL-TESTEUR.md) | Installation pour testeurs |
| [deploy/RAILWAY.md](deploy/RAILWAY.md) | Déploiement Railway (recommandé) |
| [deploy/DEPLOIEMENT.md](deploy/DEPLOIEMENT.md) | Déploiement Docker / VPS |

---

## Structure

```
gestion-scolaire/
├── backend/          # API Flask
├── frontend/         # React + Vite
├── database/         # Schéma SQL
├── deploy/           # Config prod, Nginx, env
├── scripts/          # Ops, validation, backup
└── docs/             # Documentation
```

---

## Accès public temporaire (PC local)

Expose localhost:8080 via Cloudflare Tunnel (démo uniquement) :

```powershell
.\scripts\tunnel-public.ps1
# Copier l'URL https://xxxx.trycloudflare.com affichée
```

---

## Licence

Projet privé — usage interne établissement scolaire.
