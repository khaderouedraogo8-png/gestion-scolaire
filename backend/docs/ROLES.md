# Rôles métier — Gestion scolaire

## Décision Directeur / Administrateur

| Rôle | Intention produit |
|------|-------------------|
| **directeur** | Direction de l’établissement — accès maximal métier dans l’école |
| **administrateur** | Rôle administratif à accès maximal (équivalent direction aujourd’hui) |

Aucune hiérarchie complexe n’est introduite. Si aucune différence métier n’existe
encore dans le code, **leurs permissions API/UI sont identiques**. Les JWT et
rôles existants sont conservés (pas de migration de comptes).

## Matrice cible (vérifiée vs domaine)

| Domaine | Directeur | Admin | Secrétariat | Comptable | Enseignant | Parent |
|---------|-----------|-------|-------------|-----------|------------|--------|
| Élèves | RW | RW | RW | R | scope | R enfants |
| Classes | RW | RW | R/RW | R (scolarité) | scope | R enfants |
| Enseignants | RW | RW | R | — | scope | — |
| Matières / Évals / Notes | RW | RW | R | — | scope | R publié |
| Absences | RW | RW | RW | — | scope | R enfants |
| Discipline | RW | RW | RW | — | scope | — |
| Bulletins | RW | RW | R | — | scope | R publié |
| Finance | RW | RW | — | RW | — | R paiements |
| Rulesets | RW | RW | — | — | — | — |
| Documents | RW | RW | RW | — | — | — |
| Notifications | RW | RW | R | R (finance) | R | R inbox |

## Mécanismes conservés

- JWT + `require_role`
- Scoping enseignant (`AffectationEnseignant`)
- Scoping parent (`EleveParent`)
- Isolation tenant `school_id` / `tenant_query`

## Notifications

Architecture inchangée : table `notification` (file) → canaux `email` / `sms` / `interne`.

- SMTP existant pour l’email
- SMS : stub ou `SMS_API_URL` HTTP (ne pas prétendre un provider réel sans config)
- Digest absences hebdo : CLI `digest-absences-hebdo` + cron lundi 09:00
- Idempotence via `idempotency_key`
- Inbox parent : `GET /api/notifications/me` + `lu_le`
