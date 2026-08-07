# Comptes de démonstration

Tous les comptes ont `doit_changer_mdp = false` pour faciliter les tests.

## Personnel

| Rôle | Email | Mot de passe | Accès |
|------|-------|--------------|-------|
| Administrateur | `admin@ecole.local` | `Admin123!` | Accès total |
| Directeur | `directeur@ecole.local` | `Directeur123!` | Validation bulletins, audit |
| Secrétariat | `secretariat@ecole.local` | `Secret123!` | Élèves, inscriptions, absences |
| Comptable | `compta@ecole.local` | `Compta123!` | Finance, arriérés, reçus |
| Enseignant (Math) | `enseignant@ecole.local` | `Enseignant123!` | Notes de ses classes |

## Portail parent

| Email | Mot de passe | Enfant lié |
|-------|--------------|------------|
| `parent@demo.local` | `Parent123!` | Amadou Diallo (2025M-001) |

## Données seed

- **Établissement** : École Exemplaire, Ouagadougou
- **Année active** : 2025-2026
- **Classes** : 6ème A/B, Terminale A/C
- **Élèves** : ~13 (5 initiaux + 8 étendus)
- **Matières** : Math, Français, Anglais, PC, SVT, HG
- **Finance** : frais scolarité 150 000 FCFA (3 tranches), 1 paiement démo
- **Notifications** : 1 email en file (`demo_bienvenue`)

## Réinitialiser les données

```powershell
# Dev
docker exec gestion-scolaire-backend-1 flask --app run.py seed

# Prod locale
docker exec gestion-prod-backend-1 flask --app run.py seed
```

## Emails de test (prod locale)

Les notifications partent vers **Mailhog** : http://localhost:8025

```powershell
docker exec gestion-prod-backend-1 flask --app run.py traiter-notifications
```
