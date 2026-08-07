# Guide installateur / testeur

Installation rapide pour tester l'application en local (Windows recommandé).

## Prérequis

- Windows 10/11
- Python 3.12 (`py -3.12`)
- Node.js 20+
- winget (installé par défaut sur Windows 11)

## Installation (15–30 min)

```powershell
git clone https://github.com/VOTRE-ORG/gestion-scolaire.git
cd gestion-scolaire

# Installe PostgreSQL 17, MSYS2/Pango, venv Python, npm, seed demo
.\scripts\install-native.ps1

# Démarre backend :5000 + frontend :5173
.\scripts\start-native.ps1
```

> Mot de passe superuser PostgreSQL (winget) : `postgres`  
> Si la connexion échoue : `.\scripts\install-native.ps1 -PostgresPassword VOTRE_MDP`

## URLs

| Service | URL |
|---------|-----|
| Application | http://localhost:5173 |
| API health | http://localhost:5000/api/health |

## Comptes de test

| Rôle | Email | Mot de passe |
|------|-------|--------------|
| Admin | `admin@ecole.local` | `Admin123!` |
| Directeur | `directeur@ecole.local` | `Directeur123!` |
| Secrétariat | `secretariat@ecole.local` | `Secret123!` |
| Comptable | `compta@ecole.local` | `Compta123!` |
| Enseignant | `enseignant@ecole.local` | `Enseignant123!` |
| Parent | `parent@demo.local` | `Parent123!` |

Liste complète : [COMPTES-DEMO.md](COMPTES-DEMO.md)

## Validation

```powershell
.\scripts\validate-native.ps1
```

## Arrêter

```powershell
.\scripts\stop-native.ps1
```

## Alternative Docker

```powershell
docker compose up -d
```

Voir [README.md](../README.md) pour la prod et le déploiement VPS.
