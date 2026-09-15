# AUDIT — Gestion Scolaire SaaS

**Date :** 2026-09-14  
**Branche d’analyse :** `main` (+ contexte produit cible multi-tenant)  
**Auteur :** Audit Lead (architecture / sécurité / produit)  
**Périmètre :** repository complet (`backend/`, `frontend/`, `database/`, `deploy/`, CI)

---

## 1. Architecture actuelle

```
┌─────────────┐     ┌──────────────────────┐     ┌────────────┐
│ React/Vite  │────▶│ Flask + flask-smorest│────▶│ PostgreSQL │
│ Tailwind    │ /api│ JWT + Argon2id       │     │ (1 école)  │
│ Zustand     │     │ WeasyPrint PDF       │     └────────────┘
└─────────────┘     │ Redis (rate-limit)   │
                    └──────────────────────┘
                              │
                    Nginx (prod Docker/VPS)
```

- **Modèle de déploiement documenté :** **mono-établissement** — une base PostgreSQL = une école (`database/schema_v2_mono_etablissement.sql`, trigger / contrainte « une seule ligne » sur `etablissement`).
- **Pas de `school_id` / tenant** sur les entités métier. Isolation « SaaS » aujourd’hui = **redeploy / clone DB par client**, pas multi-tenant partagé.
- **Pas de SUPER_ADMIN plateforme** ni console multi-écoles.
- API REST OpenAPI (Swagger hors production), blueprints sous `/api/*`.
- Frontend SPA : routes protégées + RBAC UI (doit être miroir du backend).

---

## 2. Technologies utilisées

| Couche | Stack |
|--------|--------|
| Backend | Flask 3, flask-smorest, flask-jwt-extended, SQLAlchemy 2, Alembic, Argon2id, flask-limiter, WeasyPrint |
| Frontend | React 18, Vite 6, Tailwind 3, Zustand, Axios, Lucide, React Router 6 |
| DB | PostgreSQL 15+ (`uuid-ossp`, `pgcrypto`) |
| Cache / rate-limit | Redis (prod), `memory://` (dev) |
| PDF | Jinja2 templates + WeasyPrint |
| Tests | pytest (backend), Vitest + Playwright (frontend) |
| CI | GitHub Actions (ruff, bandit, pytest, lint, build, e2e, prod-build) |
| Déploiement | Docker Compose + Nginx (VPS). Railway mentionné dans l’historique produit ; **pas de `Procfile` / `railway.toml` dans le repo actuel sur `main`**. |

---

## 3. Fonctionnalités existantes

| Domaine | État |
|---------|------|
| Auth (login, refresh cookie httpOnly, logout, change password, forgot/reset) | ✅ Solide |
| Utilisateurs / rôles (admin, directeur, enseignant, comptable, secrétariat, parent) | ✅ Partiel (pas SUPER_ADMIN, pas élève-login) |
| Établissement, années, trimestres, niveaux, classes, calendrier | ✅ |
| Élèves, parents, inscriptions, upload pièces, photo | ✅ |
| Matières, coefficients, évaluations, saisie notes | ✅ |
| Calcul moyennes / rangs / mentions (backend) | ✅ (`calcul_moyennes.py`) |
| Bulletins PDF | ✅ |
| Finance : frais, échéances, encaissements, reçus, arriérés, export Excel | ✅ |
| Emploi du temps, affectations, salles | ✅ |
| Absences / discipline | ✅ |
| Documents admin + QR | ✅ |
| Notifications | ✅ Basique |
| Dashboard admin | ✅ |
| Portail parent (notes/bulletins/absences/paiements) | ✅ |
| Journal d’audit | ✅ |
| Landing page marketing | ❌ Absente (login = entrée publique) |
| Dashboards TEACHER / ACCOUNTANT / STUDENT dédiés | ⚠️ Partiel (dashboard surtout admin) |
| Mobile Money réel (Orange/Moov) | ❌ Non intégré (ne pas prétendre le contraire) |
| Multi-tenant shared DB | ❌ Absent |

---

## 4. Problèmes critiques (P0)

1. **Écart produit vs architecture :** la cible métier est un **SaaS multi-tenant** (SUPER_ADMIN → Écoles A/B/C) ; le code et le schéma sont **mono-établissement**. Sans migration, on ne peut pas vendre une plateforme multi-écoles sur une seule instance.
2. **Contrôle d’accès objet incomplet (IDOR / broken access control) :**
   - `GET /api/notes/evaluations/<id>` : pas de `teacher_has_*` — un enseignant peut lire une évaluation hors de ses classes.
   - `GET /api/eleves/<id>` : parents filtrés ; **enseignant / comptable** peuvent ouvrir **n’importe quel** élève (la liste est filtrée, le détail non).
   - Génération / patch bulletins et certaines grilles notes : contrôles enseignant absents ou incomplets.
3. **Upload fichiers sans allowlist MIME/extension** (`eleves/.../upload`) — risque fichiers exécutables / polyglots.
4. **Fuite `reset_token` si `DEBUG=True`** (`forgot-password`) — dangereux en cas de mauvais déploiement.
5. **Secrets par défaut en non-production** (`config.py`) — OK pour local ; **catastrophe** si `FLASK_ENV≠production` en exposé.

---

## 5. Problèmes importants (P1)

1. **Pas de SUPER_ADMIN / onboarding école** — indispensable pour commercialiser le SaaS.
2. **RBAC : pas de modèle Permission granulaire** — seulement rôles string + décorateur ; pas de matrice permissions persistée.
3. **Rôle STUDENT / SUPERVISOR** absents (surveillant = non modélisé).
4. **Validation Marshmallow inégale** — plusieurs endpoints utilisent `request.json` brut (users PATCH, reset password, documents).
5. **Pas de handler d’erreurs global** — 500 Flask bruts possibles ; messages parfois techniques.
6. **Dashboards par rôle incomplets** — teacher / accountant / student / parent analytics limités.
7. **Landing page + funnel démo** absents — frein commercial.
8. **Email reset password** : structure token OK, envoi SMTP souvent **NON CONFIGURÉ** (token exposé en DEBUG pour pallier).
9. **Admin reset password renvoie le MDP temporaire dans le JSON** — risque logs / interception.
10. **Tests IDOR enseignant** insuffisants (parent RBAC bien couvert).
11. **Absence de pagination systématique** sur certaines listes (risque perf).
12. **PWA légère** — SW basique ; offline métier non maîtrisé.

---

## 6. Problèmes mineurs (P2/P3)

- Duplication listes de rôles `routes.jsx` vs `Sidebar.jsx` (drift).
- `RedirectToDashboard` mort dans `App.jsx`.
- Deux chemins Docker frontend (`Dockerfile.prod` vs `deploy/Dockerfile.nginx`).
- Couverture Vitest très fine (surtout Login).
- Swagger actif hors prod (faible risque).
- Design system en cours d’unification (tokens historiques `or-cachet`).
- QR verify public (by design) — documenter surface d’attaque.

---

## 7. Risques de sécurité

| Risque | Niveau | Commentaire |
|--------|--------|-------------|
| Broken access control / IDOR enseignant | **Élevé** | Voir §4 |
| Privilege escalation via URL/API | **Élevé** | UI RBAC contournable sans backend strict |
| Upload dangereux | **Moyen** | Pas d’allowlist |
| Session / JWT | **Faible–OK** | Access mémoire + refresh httpOnly Strict ; Argon2id ; lockout 5/30min |
| CSRF | **Faible** | SameSite=Strict refresh ; Bearer access |
| SQLi | **Faible** | ORM + binds sur SQL brut observé |
| XSS | **Moyen** | SPA classique — token access volable si XSS |
| Secrets dans Git | **Faible** | Exemples seulement ; comptes démo dans README |
| Mass assignment | **Moyen** | PATCH users / élèves à surveiller |
| SSRF | **Faible** | Peu de fetch URL serveur |
| Fuite reset token DEBUG | **Élevé** si DEBUG prod | |

---

## 8. Risques liés aux données

- Notes médicales chiffrées (`pgcrypto`) — bon point ; accès restreint admin/dir/secrétariat.
- Pas d’isolation tenant → **fuite cross-école** si on héberge plusieurs écoles sur la même DB sans refonte.
- Soft delete peu généralisé — suppressions dures possibles.
- Export Excel finance — contrôler qui exporte.
- Logs audit avec IP — OK si politique claire ; éviter MDP / tokens dans logs.
- Backups DB : à documenter côté ops (hors code).

---

## 9. Problèmes UX/UI

- Entrée = login : **pas de landing** convaincante pour directeurs BF.
- Dashboard admin correct ; manquent dashboards métier par rôle.
- Mobile : sidebar drawer OK ; tables parfois denses (cartes mobiles partiellement traitées).
- Empty / loading / error states présents mais à homogénéiser.
- Connexion faible Afrique : bundle OK (~450 kB JS gzip ~126 kB) — continuer lazy-loading routes.
- FCFA / XOF déjà en schéma (`devise` défaut XOF) — bien.

---

## 10. Problèmes de performance

- Listes élèves / notes : pagination partielle — risque N+1 / payload gros.
- Vue matérialisée `moyenne_matiere_eleve` — bien ; vérifier refresh.
- PDF WeasyPrint : CPU-bound — file / timeout à prévoir en charge.
- Pas de cache applicatif métier (Redis surtout rate-limit).
- Index : présents dans schéma SQL — à audit ciblé sur requêtes lentes prod.

---

## 11. Dette technique

- Architecture **mono** vs ambition **multi-tenant SaaS**.
- RBAC string-based sans permissions table.
- Validation / error handling hétérogènes.
- Documentation technique riche (`docs/`) vs écart produit commercial.
- Railway / PaaS : historique flou sur `main` (Docker VPS documenté).
- `load_dotenv` non appelé — env via Docker/shell uniquement.

---

## 12. Architecture recommandée

### Cible progressive (sans big-bang)

```
SUPER_ADMIN (plateforme)
    └── School (tenant)
            ├── Users (roles)
            ├── AcademicYear, Class, Subject, …
            └── Données isolées par school_id
```

**Stratégie recommandée : shared database + `school_id` (row-level isolation)**  
- Une instance, N écoles, FK `school_id` sur toutes les tables métier.  
- Middleware : résoudre le tenant depuis le JWT (`school_id` claim) + filtre obligatoire sur chaque query.  
- Contraintes DB : composite uniqueness `(school_id, matricule)`, etc.  
- Alternative « DB par école » : garder le mono actuel pour les clients déjà déployés ; orchestrateur SUPER_ADMIN séparé — plus simple court terme, plus cher ops.

**RBAC :** table `permissions` + `role_permissions` + décorateur `@require_permission("notes.write")` en plus des rôles.

**Auth :** conserver Argon2 + JWT access + refresh cookie ; ajouter `school_id` + `role` dans claims.

---

## 13. Plan de migration

| Phase | Contenu | Risque |
|-------|---------|--------|
| **A — Harden (maintenant)** | Fermer IDOR enseignant/élève, allowlist upload, jamais de reset_token hors env explicite, tests négatifs | Faible |
| **B — Produit P1** | Landing + CTA démo ; dashboards teacher/comptable ; pagination ; error handler global | Faible |
| **C — Tenant foundation** | Table `schools` ; `school_id` nullable puis backfill ; claim JWT ; filtre services | Moyen |
| **D — SUPER_ADMIN** | Console création école, provision admin, quotas | Moyen |
| **E — Cutover** | Contraintes NOT NULL `school_id` ; tests isolation A≠B | Élevé |
| **F — Mobile Money** | Adapters Orange/Moov **NON CONFIGURÉ** jusqu’aux clés réelles | Ext. |

**Clients mono existants :** migration = créer 1 row `schools` + backfill `school_id` partout.

---

## 14. Priorités P0 / P1 / P2 / P3

### P0 — Critique (sécurité / perte de confiance / blocage SaaS)

| ID | Action |
|----|--------|
| P0-1 | Corriger IDOR enseignant (évaluations, notes, bulletins, détail élève) |
| P0-2 | Allowlist upload (extensions + content-type + taille) |
| P0-3 | Interdire retour `reset_token` sauf `EXPOSE_RESET_TOKEN=1` explicite (pas seulement DEBUG) |
| P0-4 | Documenter + tester non-accès cross-objet (tests pytest) |
| P0-5 | Spécifier architecture multi-tenant (ce document) — implémentation fondation en phase C |

### P1 — Indispensable production commerciale

| ID | Action |
|----|--------|
| P1-1 | Landing page + « Demander une démonstration » |
| P1-2 | Fondations `school_id` + SUPER_ADMIN (après P0) |
| P1-3 | Dashboards par rôle (enseignant, comptable, parent enrichi) |
| P1-4 | Error handler global + validation Marshmallow manquante |
| P1-5 | Pagination / filtres listes critiques |
| P1-6 | SMTP reset password (sinon message « NON CONFIGURÉ ») |
| P1-7 | Modes paiement explicites CASH / ORANGE_MONEY / MOOV_MONEY / BANK / OTHER (enum) **sans** faux PSP |

### P2 — Améliorations importantes

| ID | Action |
|----|--------|
| P2-1 | Matrice permissions DB |
| P2-2 | Soft delete + rétention |
| P2-3 | Lazy routes frontend / perf |
| P2-4 | Unifier RBAC UI constants |
| P2-5 | Monitoring / structured logs |
| P2-6 | Rôle surveillant + portail élève |

### P3 — Plus tard

| ID | Action |
|----|--------|
| P3-1 | Intégrations Mobile Money réelles |
| P3-2 | SMS gateway production |
| P3-3 | Multi-région / HA |
| P3-4 | Offline-first PWA métier |
| P3-5 | Marketplace modules |

---

## État des correctifs P0 (mise à jour 2026-09-14 — phase implémentation)

### Vérification réelle (Phase 0)

| Contrôle | Résultat |
|----------|----------|
| Code IDOR notes/élèves (helpers `teacher_has_*`) | ✅ Présent backend |
| Upload allowlist + UUID | ✅ Présent |
| `reset_token` ≠ DEBUG seul | ✅ Présent |
| `pytest` suite backend | ✅ **46 passed** |
| `test_teacher_idor.py` + absences + upload/reset | ✅ |

### Correctifs ajoutés cette itération (Phase 1–3)

| ID | Statut | Fichiers | Tests |
|----|--------|----------|-------|
| P0-1 | ✅ Renforcé | `routes/absences.py` — list/create/update + discipline filtrés par classes enseignant ; 403 explicite si `id_eleve` hors périmètre | `test_teacher_idor.py` (+3 cas absences) |
| P0-2 | ✅ Renforcé | `routes/eleves.py` — path traversal, doubles extensions, photo allowlist, nom 100% UUID serveur | `test_upload_reset_security.py` |
| P0-3 | ✅ Renforcé | `routes/users.py` — pas d’expose en production même avec `EXPOSE_RESET_TOKEN` ; SMTP requis sinon **503** ; `localhost` ≠ SMTP configuré | `test_upload_reset_security.py` |
| P0-4 | ✅ | Tests négatifs IDOR + upload + reset | 12 tests ciblés verts |
| P0-5 | 📋 Reporté | Multi-tenant `school_id` — **pas commencé** (volontaire, après P0) | — |

### Risques restants après P0

- Pas encore d’isolation multi-école (`school_id`) — mono-tenant DB.
- Emploi du temps : liste enseignants visible à tous les enseignants (annuaire école — acceptable mono).
- Finance : rôles comptable/admin OK ; pas de filtre enseignant (déjà hors rôle).
- Error handler JSON global / pagination / landing — **P1**, pas P0.


## État des correctifs P1 (mise à jour — Phase 4–6)

| ID | Statut | Détail |
|----|--------|--------|
| P1-4 Error handler | ✅ | `app/utils/errors.py` — JSON stable (`success`/`message`/`error.code`), jamais de stack trace client ; JWT loaders alignés ; messages HTTP FR stables |
| P1-4 Validation | ✅ | Marshmallow sur users PATCH, forgot/reset password, inscription statut, documents generate, bulletins générer/patch (`id_eleve` **ou** `id_classe`), relance arriérés |
| P1-5 Pagination | ✅ | Envelope `items`+`pagination` sur paiements, absences, discipline, évaluations, bulletins, documents, users (élèves : `items`+page/per_page/total) |
| P1-1 Landing | 📋 Reporté | Après hardening |
| P1-2 Multi-tenant | 📋 Reporté | **Pas commencé** (volontaire) |
| Tests P1 | ✅ | `tests/integration/test_p1_errors_pagination.py` |

---

## PR #7 — Final Review

**Date :** 2026-09-14  
**Reviewer :** Senior validation (code réel + runtime, pas seulement AUDIT)  
**Branche :** `cursor/saas-p1-hardening-8bcc`  
**Périmètre :** hardening API P1 + P0 (IDOR / upload / reset) — **sans** multi-tenant / SUPER_ADMIN / school_id / refonte UI.

### Tests

| Métrique | Valeur |
|----------|--------|
| Total collectés | **63** |
| Passed | **63** |
| Failed | **0** |
| Errors | **0** |
| Skipped | **0** |
| P0 IDOR + upload + reset | **14 passed** |
| P1 errors + pagination | **15 passed** |

### Lint / Build

| Outil | Résultat |
|-------|----------|
| `ruff check app tests` | ✅ All checks passed |
| Frontend `eslint` | ✅ 0 errors / 3 warnings hooks (préexistants) |
| Frontend `vite build` | ✅ OK |
| Type checking | ⚠️ N/A (pas de mypy / tsc) |
| Dépendances ajoutées dans la PR | ✅ Aucune |

### Probes sécurité runtime (exécutées)

- IDOR enseignant : tests automatisés + contrôles `teacher_has_*` sur élèves / évaluations / notes / absences / discipline / bulletins
- Upload : rejet `.php`, path traversal, double extension dangereuse ; accept PDF avec nom UUID serveur
- Reset : token hashé, expiration 24h, usage unique ; **jamais** de `reset_token` en production (`EXPOSE_RESET_TOKEN=1` et même `TESTING=True` coincé → 503)
- Erreurs 401/404/422/500 : envelope JSON ; **aucune** stack / secret / chemin système côté client
- Pagination : `page`/`per_page` bornés (min 1, max 100) sur users, paiements, absences, discipline, évaluations, bulletins, documents ; FE consomme `items`

### Problèmes

| Sévérité | Détail |
|----------|--------|
| **P0** | Aucun |
| **P1** | Aucun ouvert (hard-block prod reset token déjà dans la branche) |
| **P2** | Admin reset renvoie `mot_de_passe_temporaire` ; MIME vide soft-allow ; `notes_medicales` via `request.json` hors schéma PUT élève ; N+1 dans `_serialize_*` listes (atténué par `per_page≤100`) ; élèves sans bloc `pagination` imbriqué ; 404/409 manuels hors envelope globale |
| **P3** | Warnings eslint hooks FE ; messages Marshmallow parfois EN |

### Fichiers importants modifiés

- `backend/app/utils/errors.py`, `pagination.py`
- `backend/app/routes/auth.py`, `users.py`, `absences.py`, `notes.py`, `finance.py`, `documents.py`, `eleves.py`
- `backend/app/schemas/*` (auth, notes, documents, eleve, finance)
- `backend/tests/integration/test_teacher_idor.py`, `test_upload_reset_security.py`, `test_p1_errors_pagination.py`
- FE : `users.js`, `ForgotPassword.jsx`, pages listes `items`

### Risques restants

- Mono-établissement : pas d’isolation `school_id` (volontaire, hors PR)
- Admin temp password dans JSON (ops / logs) — backlog P2
- N+1 serialize listes — acceptable sous plafond pagination

### Statut

**READY TO MERGE**

---




## PR #7 — Final Validation

**Date :** 2026-09-14  
**Branche :** `cursor/saas-p1-hardening-8bcc`  
**Exécution :** pytest/ruff/eslint/vite + probes runtime + CI GitHub (4/4) — vérifié dans cet environnement.

### Tests
Total **63** · Passed **63** · Failed **0** · Errors **0** · Skipped **0** · Duration **4.03s**  
P0+P1 ciblés : **29 passed**

### Sécurité / API / FE
IDOR **PASS** · Uploads **PASS** · Reset **PASS** · Secrets prod **PASS** · Error leak **PASS**  
Marshmallow **PASS** · Pagination **PASS** · Routes forgot/reset/users **PASS**  
FE items **PASS** · vite build **PASS** · eslint **PASS** (0 erreur / 3 warnings) · ruff **PASS**

### Classification
**P0:** 0 · **P1:** 0  
**P2:** admin `mot_de_passe_temporaire` ; MIME vide soft-allow ; `notes_medicales` hors schéma ; N+1 serialize (plafonné) ; eleves sans pagination imbriquée ; 404/409 manuels hors envelope  
**P3:** 3 warnings hooks FE ; messages Marshmallow parfois EN

### Risques restants
Mono-école (pas de `school_id`) — volontaire hors PR · temp password admin JSON — backlog ops

### Verdict
**READY TO MERGE**

---

## Synthèse exécutive

**P0 sécurité** + **hardening API P1 (PR #7)** : validés.  
**Phase 1 multi-tenant** démarrée sur branche `cursor/saas-multitenant-foundation-8bcc` (fondation uniquement — pas d’isolation métier complète).

---

# Multi-Tenant Foundation — Phase 1

**Date :** 2026-09-14  
**Branche :** `cursor/saas-multitenant-foundation-8bcc`  
**Statut :** fondation technique prête — **pas** encore un SaaS multi-tenant sécurisé.

## Architecture actuelle

Mono-école (shared app + 1 profil `etablissement`) avec **tenant technique** introduit :

```
JWT → Utilisateur → school_id → School
```

`Etablissement` reste le **profil mono-école** (nom, logo, devise…).  
`School` est le **tenant SaaS** (isolation future des données).

## Architecture cible

Multi-tenant **shared database** :

```
SaaS
 ├── School A → users / students / classes / notes / finances
 ├── School B → …
 └── School C → …
```

Phases prévues : A (cette PR) → B school_id métier → C backfill → D isolation routes → E NOT NULL.

## Modèles modifiés

| Modèle | Changement |
|--------|------------|
| `School` (nouveau) | Table `schools` (id, name, code unique, email, phone, address, city, country, logo, is_active, timestamps) |
| `Utilisateur` | `school_id` FK nullable + index + relationship |

## Modèles volontairement non modifiés (Phase 1)

Pour chaque modèle métier : **Tenant scoped: oui (à terme)** / **Direct school_id: non (Phase 1)** — isolation via parent ou Phase 2.

| Model | Tenant scoped | Direct school_id nécessaire | Justification |
|-------|---------------|----------------------------|---------------|
| Etablissement | Oui (profil école) | Phase 2 ou 1:1 School | Aujourd’hui mono-ligne ; ne pas confondre avec tenant |
| AnneeScolaire | Oui | Oui (ou via School) | Années propres à chaque école |
| Trimestre | Oui | Indirect | Isolé via `id_annee` une fois année scopée |
| NiveauEtude | Oui | À analyser | Souvent catalogue école ; unique global aujourd’hui |
| Classe | Oui | Oui (ou via année) | Classes par école |
| Eleve | Oui | Oui | Donnée cœur tenant |
| ParentTuteur / EleveParent | Oui | Indirect / oui | Via élève ou user.school_id |
| Inscription | Oui | Indirect | Via élève + classe |
| Enseignant | Oui | Oui (ou via user) | Lié à utilisateur |
| AffectationEnseignant / Creneau / Salle | Oui | Indirect / oui | Via enseignant / classe |
| Matiere / CoefficientMatiere | Oui | Oui | Catalogue par école |
| Evaluation / Note / Bulletin | Oui | Oui / indirect | Notes scoppées école |
| ProgrammeDevoir / SeanceCours | Oui | Indirect | Via classe / année |
| FraisScolaire / Echeance / Paiement | Oui | Oui | Finance par école |
| Absence / IncidentDisciplinaire | Oui | Oui / indirect | Via élève |
| DocumentAdministratif | Oui | Oui | Docs par école |
| Notification | Oui | Indirect | Via utilisateur |
| JournalAudit | Oui (filtre) | Optionnel | Traçabilité cross-tenant plateforme à prévoir |
| RefreshToken / ReinitialisationMdp | Non métier | Non | Liés à utilisateur ; tenant via user.school_id |

## Migration

1. Création table `schools` + contrainte unique `code`
2. Colonne `utilisateur.school_id` nullable + FK `ON DELETE SET NULL` + index
3. École par défaut `ECOLE-EXISTANTE` (nom repris de `etablissement.nom` si présent, sinon « École existante »)
4. Backfill : tous les `utilisateur.school_id IS NULL` → école par défaut
5. Rollback : drop FK/index/colonne puis table `schools` (données métier utilisateur conservées)

Schéma de référence CI mis à jour : `database/schema_v2_mono_etablissement.sql`.

## Tenant context

- `app/services/tenant.py` : `get_current_school_id()`, `get_current_school()`, `require_user_school()`
- Source de vérité : JWT → user → `school_id` (**jamais** un `school_id` client)
- API : `GET /api/schools/current` (pas de CRUD public / pas de PATCH cross-tenant)
- FE : `currentSchool` dans `authStore` après login / initialize / refresh

## Risques — endpoints NON isolés

Toutes les routes métier restent **mono-tenant de fait** (pas de filtre `school_id`) :

- `/api/eleves`, `/api/notes`, `/api/pedagogie`, `/api/finance`
- `/api/emploi-temps`, `/api/absences`, `/api/documents`
- `/api/etablissement/*`, `/api/users`, `/api/dashboard`, `/api/notifications`, `/api/audit`

La présence de `school_id` **ne constitue pas** une isolation multi-tenant.

## Indexes Phase 1

- `uq_schools_code` (unicité globale du code école)
- `ix_utilisateur_school_id` (prépare `WHERE school_id = ?`)

Pas de transformation aveugle des UNIQUE métier en `(school_id, …)` — Phase 2+.

## Prochaine étape

**Phase 2 — Tenant isolation des données métier**  
Ajouter `school_id` (où pertinent), backfill, filtrer toutes les requêtes/routes, puis contraintes NOT NULL.

---

## PR #8 — Final Validation

**Date audit (re-run) :** 2026-09-15  
**Branche :** `cursor/saas-multitenant-foundation-8bcc`  
**Commits Phase 1 :** `0d5edf1` + `f0b86aa`  
**Verdict exécuté :** **READY TO MERGE** (Phase 1 foundation) — P0=0, P1=0

### Architecture

shared database + tenant identifier (`schools` / `utilisateur.school_id`)

### Migration (re-exécutée 2026-09-15)

| Étape | Résultat |
|-------|----------|
| `alembic downgrade -1` | PASS — drop `schools` + `utilisateur.school_id` |
| `alembic upgrade head` | PASS — recreate + default school + backfill |
| Préservation données métier | PASS — counts inchangés (utilisateur 623, eleve 1078, classe 736, note 56, paiement 29, …) |
| Backfill | PASS — après upgrade : `school_id IS NULL = 0` (623/623 → 1 school `ECOLE-EXISTANTE`) |
| FK réelle | PASS — `fk_utilisateur_school_id … ON DELETE SET NULL` ; UUID inexistant → IntegrityError |
| Indexes réels | PASS — `uq_schools_code`, `ix_utilisateur_school_id` dans `pg_indexes` |
| Unique `schools.code` | PASS — doublon → IntegrityError |

**Downgrade documenté :** détruit volontairement `schools` + colonne `school_id` (lien tenant perdu). Tables métier conservées.

**ON DELETE SET NULL :** supprimer une école nullifie `utilisateur.school_id` (vérifié). Acceptable Phase 1 ; durcir en Phase 2+.

**Note :** avant re-upgrade, 74 users avaient `school_id NULL` (créations post-migration / tests). Le backfill migration les réassocie ; la colonne reste nullable par design Phase 1.

### Tenant context / API / sécurité (re-exécutés)

| Check | Résultat |
|-------|----------|
| Sans JWT / JWT invalide | 401 |
| User A → AUD-A / User B → AUD-B | PASS (IDs distincts) |
| Query `?school_id=<B>` + Header `X-School-Id` | PASS — reste A (spoof inefficace) |
| POST `/current` / GET\|PATCH `/schools/<id>` | 405 / 404 |
| User sans school / école inactive | 403 |
| JWT claims | pas de `school_id` (role/email/sub) — tenant depuis User DB |
| Frontend | aucun `school_id` ; `currentSchool` via GET API seulement |

### Tests / lint / build (re-exécutés)

- `pytest -q` : **73 passed / 0 failed / 4.52s**
- `ruff check app tests` : PASS  
- `npm run lint` : 0 errors / 3 warnings hooks préexistants  
- `npm run build` : PASS

### Modèles NON isolés (Phase 2 — volontaire)

eleve, parent_tuteur, eleve_parent, inscription, classe, annee_scolaire, trimestre, niveau_etude, matiere, coefficient_matiere, evaluation, note, bulletin, programme_devoir, seance_cours, enseignant, affectation_enseignant, salle, creneau_emploi_temps, frais_scolaire, echeance_paiement, paiement, absence, incident_disciplinaire, document_administratif, notification, evenement_calendrier, etablissement (profil), journal_audit — **PHASE 2**.

### Scope vs `main`

Branche **empile PR #7** (16 commits / 41 fichiers). Commit Phase 1 seul = 15 fichiers in-scope. Recommandation ops : merger PR #7 d’abord **ou** accepter le stack (PR #7 déjà validée READY).

### P0 / P1

Aucun.

### P2

- Stack PR #7 non mergée dans `main`
- `ON DELETE SET NULL` + `school_id` nullable → users sans tenant possibles hors backfill
- Isolation métier absente (attendu Phase 2)

### Prochaine étape

**Merge PR #8** puis **Phase 2 — isolation réelle par école**.

---

## Références code (preuves)

- Schéma mono : `database/schema_v2_mono_etablissement.sql`
- RBAC : `backend/app/auth/permissions.py`
- Auth JWT/Argon2 : `backend/app/auth/jwt_handler.py`
- Moyennes backend : `backend/app/services/calcul_moyennes.py`
- Health : `GET /api/health` dans `backend/app/__init__.py`
- Deploy VPS : `deploy/DEPLOIEMENT.md`, `docker-compose.prod.yml`
- Tests P0 : `backend/tests/integration/test_teacher_idor.py`, `test_upload_reset_security.py`
- Tests P1 : `backend/tests/integration/test_p1_errors_pagination.py`
- Error handler : `backend/app/utils/errors.py`
- Pagination : `backend/app/utils/pagination.py`

---

# PR #9 — True Multi-Tenant Isolation

**Date :** 2026-09-15  
**Branche :** `cursor/saas-true-tenant-isolation-8bcc`  
**Gate 1 :** APPROVED — implementation livrée  
**Verdict :** **READY TO MERGE** (sous réserve relecture CI)

## Objectif

Isolation réelle **School A ≠ School B** sur les données métier (LIST / GET / CREATE / UPDATE / DELETE / EXPORT / SEARCH / AGGREGATION / PDF).

## Source de vérité tenant

```
JWT → Utilisateur.school_id → School
```

- Jamais de `school_id` client (query/header/body) — spoof → 400/422 ou ignoré  
- Pas de `school_id` dans le JWT (toujours DB user)  
- Helpers : `tenant_query`, `get_or_404_tenant`, `assert_same_school`, `apply_tenant_school`, `reject_client_school_id`

## Schéma

5 migrations Alembic après `add_schools_tenant` :

1. `tenant_cols_nullable` — colonnes `school_id` nullable  
2. `tenant_backfill` — backfill par code `ECOLE-EXISTANTE` ; assert NULL=0  
3. `tenant_fks_indexes` — FK RESTRICT, indexes, UNIQUE(id,school_id), FKs composites, drop trigger mono-établissement  
4. `tenant_rewrite_uniques` — UNIQUE(school_id, matricule/libelle/numero_recu)  
5. `tenant_school_id_not_null` — NOT NULL métier + utilisateur  

`etablissement.school_id` UNIQUE (1:1 School ↔ profil).  
`utilisateur.email` reste UNIQUE global.

## Isolation routes / services

Users, Établissement, Élèves, Notes/Bulletins, Finance, Absences, Documents, EDT, Pédagogie, Notifications, Audit, Dashboard, PDF/exports — filtrés tenant.  
Permissions RBAC filtrées par `user.school_id`.  
`audit_logger` exige un `school_id` résolu.

## Preuves A ≠ B

Fichier : `backend/tests/integration/test_true_tenant_isolation.py`

- LIST élèves / matières / users / classes isolées  
- GET élève cross-tenant → **404**  
- DELETE matière cross-tenant → **404**  
- Spoof `?school_id=` + `X-School-Id` → reste tenant A  
- CREATE avec `school_id` client → 400/422 ou forcé A  
- Même matricule autorisé sur A et B (UNIQUE tenant-local)  
- Dashboard stats OK par tenant  

## Regression

- `pytest` : **84 passed**  
- Alembic `downgrade add_schools_tenant` → `upgrade head` : PASS (données ECOLE-EXISTANTE préservées ; school_id NULL=0)  
- Frontend `lint` : warnings only ; `build` : PASS  

## Hors scope (volontaire)

SUPER_ADMIN, billing, onboarding multi-école UI, Mobile Money, landing marketing.

## Risques résiduels

- Downgrade UNIQUE global impossible si données multi-écoles peuplées (documenté)  
- Tables parent-only sans `school_id` : isolation via jointure parent (Trimestre, etc.) — à surveiller sur nouveaux endpoints  

---

# PR #10 — SUPER_ADMIN + School Onboarding

**Date :** 2026-09-15  
**Branche :** `cursor/saas-super-admin-onboarding-8bcc`  
**Gate 0 :** SAFE TO PLAN  
**Gate 1 :** APPROVED — implementation livrée  

## Objectif

Plateforme SaaS : `super_admin` global, gestion centralisée des écoles, onboarding atomique du premier admin, RBAC strict, écoles actives/inactives, audit hybride — **sans billing**.

## Décisions

| Sujet | Décision |
|-------|----------|
| Rôle DB | `super_admin` (`school_id IS NULL`) |
| École users | `school_id NOT NULL` + CHECK cohérence |
| Métier SUPER_ADMIN | **403** sans `acting_school_id` ; OK avec switch JWT |
| Suppression école | **Désactivation seulement** (`is_active`) |
| Onboarding | `POST /api/platform/schools/onboard` atomique (School + Etablissement 1:1 + admin) |
| Promotion `super_admin` | **Interdite** via `/api/users` ; bootstrap CLI `flask create-super-admin` |
| Billing | Hors scope |

## Schéma

Migration `platform_super_admin` (après `tenant_school_id_not_null`) :

1. `utilisateur.school_id` nullable + CHECK `(super_admin ∧ NULL) ∨ (¬super_admin ∧ NOT NULL)`  
2. Extension `utilisateur_role_check` → inclut `super_admin`  
3. `schools.created_by` (FK utilisateur SET NULL)  
4. `journal_audit.school_id` nullable (événements plateforme)

## API platform

```
POST   /api/platform/schools/onboard
GET    /api/platform/schools
GET    /api/platform/schools/<id>
PATCH  /api/platform/schools/<id>
POST   /api/platform/schools/<id>/activate
POST   /api/platform/schools/<id>/deactivate
GET    /api/platform/schools/<id>/users
POST   /api/platform/schools/<id>/admins
PUT    /api/platform/context/school
DELETE /api/platform/context/school
```

## Sécurité

- Source de vérité : DB user (+ claim `acting_school_id` **uniquement** si `role=super_admin` vérifié en DB)  
- Spoof `school_id` client → 400  
- École inactive → login users bloqué + refresh bloqué + métier 403  
- Dernier `administrateur` actif non désactivable (409)  
- Isolation PR #9 préservée (`tenant_query` / 404 cross-tenant)

## Frontend

- `/platform/schools`, `/platform/onboarding`  
- `authStore` : `enterSchoolContext` / `exitSchoolContext`  
- Navigation SUPER_ADMIN + menus école si contexte actif  

## Tests

- `backend/tests/integration/test_platform_super_admin.py`  
- Régression `test_true_tenant_isolation.py`  
- Suite : **99 passed**

## Hors scope (volontaire)

Billing, Stripe, Mobile Money, permissions granulaires table, hard delete school, soft-delete RGPD.


---

## PR #11 — Academic Foundation (étape 1 — DB + ORM)

**Branche :** `cursor/saas-academic-foundation-8bcc`  
**Statut étape 1 :** DB + modèles + migration + tests — **READY FOR STEP 2** (API `/programs` `/periodes` + FE non inclus)

### Livré

- Table `program` (school-scoped) + backfill `GENERAL` / « Général » par école (compat historique permanente)
- `trimestre` → `academic_period` (UUID conservés) — Model B : Year + Program
- `niveau_etude.id_program`, unicité `(school_id, id_program, libelle)`
- `classe.id_program` aligné niveau via FK composite `(id_niveau, id_program)`
- FK composites anti cross-tenant (period↔year/program, level↔program, class↔niveau/program)
- Alias ORM `Trimestre = AcademicPeriod` + synonym `numero` ↔ `sequence`
- Helper `app/services/academic.py`
- Migration Alembic `academic_foundation_pr11`
- Schéma CI `database/schema_v2_mono_etablissement.sql` aligné
- Compat minimale routes `/trimestres` + create niveau/classe (défaut GENERAL)
- Tests `test_academic_foundation.py` (structure, IntegrityError cas 1–4, isolation API)

### Hors scope étape 1

Routes `/programs` `/periodes`, FE config, grading, examens, Track.

### Validation live

- BEFORE/AFTER migration (DB test) : schools 45, années 528, trimestres/periods 367, evals 518, notes 76, bulletins 2, inscriptions 1345 — **identiques** ; UUID période inchangés ; 45 programs GENERAL
- `pytest` : **112 passed**
- `ruff check app tests` : **PASS**

---

## PR #11 — Academic Foundation (étape 2 — API)

**Branche :** `cursor/saas-academic-foundation-8bcc`  
**Statut :** API Programs + Periodes + façade /trimestres — **READY FOR STEP 3** (frontend)

### Livré

- `GET/POST /api/etablissement/programs` (+ pagination, search, is_active)
- `GET/PATCH /api/etablissement/programs/<id>`
- `POST /api/etablissement/programs/<id>/deactivate` (soft ; GENERAL protégé)
- `GET/POST /api/etablissement/periodes` (+ filtres program/année/type/active)
- `GET/PATCH /api/etablissement/periodes/<id>`
- `POST /api/etablissement/periodes/<id>/deactivate`
- Façade `/trimestres` → **même** `academic_service` (numero ← sequence)
- Niveaux/Classes : `id_program` validé tenant ; classe alignée sur niveau
- Audit : `PROGRAM_*` / `PERIOD_*` (+ `actor_type=platform_support` si SUPER_ADMIN)
- Tests : `test_academic_api.py` (15) + régression

### Contrats UI (étape 3)

- Programs : code, name, type, period_type_default, counts (levels/classes/periods)
- Periodes : sequence libre ≥1, types trimestre/semestre/custom/annuel
- Filtres + pagination PR#7
- Erreurs 400/403/404/409 cohérentes

### Validation

- pytest : **127 passed**
- ruff : **PASS**

---

## PR #11 — Academic Foundation (étape 3 — Frontend)

**Statut :** Structure académique UI — livrée

### Livré

- Routes `/etablissement/programmes`, `/periodes`, `/niveaux`, `/classes` (+ détail programme)
- Nav Structure académique ; sidebar Configuration mise à jour
- Legacy `/config/trimestres` sans plafond 1–3 (façade `/trimestres`)
- Labels contextuels `2nde · Programme` ; cascade Programme → Niveau → Classe
- `PUT /niveaux/<id>` pour édition
- Tests FE `academicStructure.test.jsx`

### Hors scope (conservé)

Track, GradingRuleset, moteur de notes, Class Council, IA, billing

---

## PR #11 — Academic Foundation (étape 4 — Validation)

**Verdict :** **MERGE READY WITH NON-BLOCKING RISKS**

Risques non bloquants retenus :

1. N+1 counts sur `list_programs` (MEDIUM) — follow-up perf
2. Couverture tests RBAC/SUPER_ADMIN/audit partielle (MEDIUM)
3. `BulletinList.jsx` filtre encore Trimestre 1–3 (dette notes, hors PR11)
4. Downgrade Alembic non sûr après multi-programmes (FORWARD-ONLY, documenté)

---

## PR #11 — MERGED (étape 5)

**Branche principale :** `main`  
**Merge commit :** `8aab423` — `Merge pull request #11 from khaderouedraogo8-png/cursor/saas-academic-foundation-8bcc`  
**PR :** https://github.com/khaderouedraogo8-png/gestion-scolaire/pull/11 — **MERGED**

### Modèle canonique

```
School
└── AcademicYear
    └── Program (school-scoped ; GENERAL = historique permanent)
        ├── AcademicPeriod  (Year + Program ; sequence libre ≥ 1)
        ├── NiveauEtude
        └── Classe  (alignée niveau.program via FK composite)
```

### Contrats API

- `/api/etablissement/periodes` = **API canonique**
- `/api/etablissement/trimestres` = **façade de compatibilité** (même service `academic_service` ; `numero` ↔ `sequence`)

### Post-merge

Revalidation obligatoire sur `main` après merge (pytest, ruff, vitest, eslint, Vite build, tests migration/isolation).

---

## PR #12 — Grading Rules Engine (étape 1 — DB + modèles)

**Branche :** `cursor/grading-rules-engine-8bcc`  
**Décisions (ADR intégré — pas de dossier `/docs/adr` existant)**

### 1. Ruleset séparé du calcul
`grading_ruleset` / `grading_rule_component` stockent la configuration. Aucune formule hardcodée. Le moteur de résolution/calcul arrive aux steps suivants.

### 2. Versioning
Version entière portée **sur la ligne ruleset** (`code` métier + `version` ≥ 1). Unicité `(school_id, code, version)`. Historique : v1/v2/v3 coexistent. Statuts `draft` | `active` | `archived`. Une version utilisée dans une publication future restera référencable (FK immuable côté BulletinData — hors step 1). Pas de table parent séparée (cohérent avec le style Program / AcademicPeriod du repo).

### 3. Scopes (V1 Gate 1)
Axes : `school_id` + `id_annee` (obligatoires) + `id_program?` + `id_niveau?` + `id_matiere?` (NULL = wildcard).  
Pas de Class override ni Period axis en V1 (périodes trimestre/semestre restent sur AcademicPeriod).  
CHECK : `id_niveau` exige `id_program`. Une seule table ruleset (pas 7 tables de scope).

### 4. Evaluation weight ≠ subject coefficient
`grading_rule_component.weight` (pourcentage moyenne matière) **≠** `coefficient_matiere.coefficient` (moyenne générale). `CoefficientMatiere` non modifié.

### 5. Échelle
`scale_max` Numeric, défaut produit BF `20.00`, évolutif (10/20/100). Pas de `/20` hardcodé dans le ruleset.

### 6. Arrondi
`rounding_mode` ∈ {`half_up`, `half_even`, `down`, `up`} + `rounding_precision` (défaut 2). Calcul non implémenté step 1.

### 7. Missing ≠ zero
Inchangé sur `note` (`valeur_note` nullable, `absent`). Le futur moteur ne doit jamais auto-mapper NULL→0. Statuts d’absence enrichis reportés aux steps notes.

### 8. Types d’évaluation extensibles contrôlés
Table `evaluation_type` **par école** (FK composite tenant-safe). Seed système (devoir, interrogation, composition, examen, tp, oral, projet, exam_blanc, rattrapage). Types custom école sans migration SQL.  
`Evaluation.type_evaluation` CHECK legacy (`devoir|examen|interrogation`) **conservé** — pas de conversion step 1.  
**Type ≠ contexte** : colonne `evaluation_context` (`normal|examen_blanc|rattrapage|session_2`) sur le composant ; table contexte dédiée possible plus tard.

### 9. Ruleset indépendant du bulletin
Aucun HTML/CSS/PDF/template/logo/couleur dans `grading_ruleset`. Architecture cible :
`Rules Engine → Computed Results → BulletinData → BulletinTemplateVersion → Renderer`.

### 10. Future BulletinData + TemplateVersion
Ruleset versionné référencable par un futur résultat publié. Templates multi-versions hors scope (PR14). Bindings déclaratifs whitelistés uniquement (pas d’exec Python/SQL/JS).

### 11. Tenant isolation
`school_id` NOT NULL + `UniqueConstraint(id, school_id)` + FK composites vers année/program/niveau/matière/evaluation_type/ruleset.

### 12. Poids
Convention **pourcentage** `Numeric(5,2)` : `60.00` + `40.00` = `100.00`. Somme exacte 100 validée au **service** (pas de CHECK multi-lignes). CHECK ligne : `weight > 0 AND weight <= 100`.

### Hors scope step 1
resolve_grading_rules, calcul moyennes, workflow notes, templates bulletin, PDF v2, class council, AI, billing.

### Backfill
Aucun backfill des anciennes formules. Seed catalogue `evaluation_type` système par école uniquement. Notes/évaluations/bulletins/coefficients inchangés.

---

## PR #12 — Step 2 — Rules Resolution Engine

**Branche :** `cursor/grading-rules-engine-8bcc`  
**Service :** `app/services/grading_rules.py` — `resolve_grading_rules(db, ResolutionContext)`

### Décisions

1. **Priorité des scopes (V1 réel)** — axes ruleset = Program? × Level? × Subject? (pas Class/Period en matching)  
   Scores : subject=100, level=10, program=1 → hiérarchie déterministe  
   `program+level+subject (111) > … > school/year (0)`
2. **Pas de `query.first()`** — candidats scorés ; ex-aequo → `GradingRulesConflictError`
3. **Conflit même spécificité** — y compris ACTIVE v1 + ACTIVE v2 même scope (version ≠ priorité)
4. **ACTIVE uniquement** — DRAFT/ARCHIVED exclus
5. **Tenant** — validation contexte avant matching ; IDs foreign school → `GradingContextError` (`TENANT_CONTEXT_ERROR`)
6. **Validation composants** — `validate_component_weights` (somme exacte 100.00 %) réutilisable Step 3
7. **Coefficient ≠ weight** — le moteur n’utilise pas `CoefficientMatiere`
8. **Indépendance bulletin** — résultat structuré (`ResolvedGradingRules` + trace), zéro HTML/PDF
9. **Class/Period dans le contexte** — validation de cohérence académique uniquement (matching V1 inchangé)
10. **Immuabilité** — résolution en lecture seule ; gap Step 1 (pas de trigger DB) documenté pour Step 3/4

### Hors scope Step 2
API CRUD rulesets, calcul moyennes, frontend, bulletins, cache Redis.

---

## PR #12 — Step 3 — Grading Rulesets API

**Branche :** `cursor/grading-rules-engine-8bcc`  
**Routes :** `/api/grading-rulesets*` + `/api/evaluation-types`  
**Service :** `app/services/grading_rulesets.py` (consomme `resolve_grading_rules` Step 2)

### Endpoints
| Méthode | Endpoint | Rôle |
|---------|----------|------|
| GET | `/api/evaluation-types` | catalogue tenant |
| GET | `/api/grading-rulesets` | liste paginée (sans composants) |
| POST | `/api/grading-rulesets` | crée DRAFT (+ composants optionnels) |
| GET | `/api/grading-rulesets/<id>` | détail + composants |
| PATCH | `/api/grading-rulesets/<id>` | update DRAFT uniquement |
| POST | `/api/grading-rulesets/<id>/components` | ajout composant (DRAFT) |
| PATCH/DELETE | `…/components/<cid>` | update/delete (DRAFT) |
| POST | `/api/grading-rulesets/<id>/activate` | DRAFT→ACTIVE (+ archive même code) |
| POST | `/api/grading-rulesets/<id>/archive` | DRAFT\|ACTIVE→ARCHIVED |
| POST | `/api/grading-rulesets/resolve` | résolution via moteur Step 2 (`diagnostic`) |

### Décisions
1. **school_id / status / version / created_by** — serveur uniquement ; spoof → 400
2. **Axes Class/Period** — refusés à la création (V1 modèle) ; OK en resolve (validation contexte)
3. **Somme poids 100 %** — exigée à l’activation (DRAFT peut être partiel)
4. **Activation** — `SELECT … FOR UPDATE` ; auto-archive ACTIVE même `code` ; conflit si autre ACTIVE même scope
5. **Erreurs** — enveloppe PR7 + `abort_api` codes métier (`NO_RULESET`, `RULESET_CONFLICT`, …)
6. **RBAC** — lecture admin/directeur/secrétariat/enseignant/comptable ; écriture admin/directeur
7. **Indépendance** — zéro notes / moyennes / bulletin / frontend

### Hors scope Step 3
Calcul moyennes, frontend configuration, bulletins, Excel, AI.

---

## PR #12 — Step 4 — Academic Calculation Engine

**Branche :** `cursor/grading-rules-engine-8bcc`  
**Services :**
- `app/services/academic_calculation.py` — moteur pur (Decimal, arrondi ruleset)
- `app/services/academic_calculation_service.py` — orchestration DB + `resolve_grading_rules` + cache

### Décisions
1. **Flux** — ResolutionContext → Step 2 → `ResolvedGradingRules` → `calculate_subject_result` → moyenne matière → `calculate_general_average`
2. **Agrégation** — moyenne arithmétique des notes par `evaluation_type_code`, puis × poids % du composant (jamais hardcodé)
3. **missing ≠ 0** — `absent` / `None` exclus ; `0` explicite compte ; composante **requise** manquante → moyenne matière `None`
4. **Optionnelles manquantes** — omises + renormalisation sur poids présents
5. **Coefficient matière** — appliqué **après** la moyenne matière (`weighted_score`)
6. **Arrondi** — un seul arrondi final (mode/précision du ruleset) ; pas de double rounding composante
7. **scale_max** — porté par le résultat ; notes interprétées dans l'échelle du ruleset (pas de `/20` hardcodé)
8. **Bulletin** — `_get_moyennes_eleve` utilise le moteur si ruleset ACTIVE, sinon vue matérialisée legacy
9. **Types Evaluation** — CHECK élargi aux codes catalogue (`composition`, `tp`, …) — migration `grading_calc_pr12_step4`
10. **Mentions / rangs** — inchangés (hors Rules Engine) ; toujours dans `calcul_moyennes.py`
11. **Traçabilité** — `SubjectResult` porte `ruleset_id` + `version` ; **gap** : table `bulletin` ne persiste pas encore ces IDs
12. **MV `moyenne_matiere_eleve`** — reste formule plate legacy (dashboard) ; peut diverger du moteur rules — risque non bloquant

### Hors scope Step 4
Frontend, BulletinTemplate, PDF layout, class council, mentions configurables, persistance historique ruleset sur bulletin.

---

## PR #12 — Step 5 — Frontend configuration des Rulesets

**Branche :** `cursor/grading-rules-engine-8bcc`  
**Frontend :**
- Routes `/config/regles-notation` + `/config/regles-notation/:id` (rôles CONFIG = admin/directeur/super_admin)
- Pages `GradingRulesets.jsx`, `GradingRulesetDetail.jsx`
- Client `services/api/grading.js` → APIs Step 3 uniquement
- Libellés `utils/gradingLabels.js` (statuts / arrondi / politiques moteur lecture seule)

### Décisions
1. **Source de vérité** — backend Step 3 ; aucun calcul de moyenne côté JS
2. **missing-grade policy** — pas de champ API ; panneau informatif aligné sur le moteur Step 4 (required → incomplete ; optional → renormalise ; 0 explicite ≠ missing)
3. **Versioning** — immutabilité ACTIVE/ARCHIVED ; « Nouvelle version » = POST create même `code` (version auto serveur)
4. **Historique** — liste filtrée par `code` via GET paginé (pas d’endpoint history dédié)
5. **Poids ≠ coefficients** — copy UI explicite ; page Coefficients inchangée
6. **Axes V1** — année / programme / niveau / matière ; classe & période non stockées (mention UI)
7. **RBAC UI** — masque actions write si hors admin/directeur/super_admin ; backend reste autorité
8. **Erreurs** — `apiErrorMessage` 403/404/409/… ; confirmation activate/archive/delete composante
9. **Tests** — `gradingRulesets.test.jsx` (liste, permissions, 60/40, 30/20/50, poids invalides, scale/rounding, 403, 409, activation, missing≠0)

### Hors scope Step 5
Calculation Engine FE, bulletins, PDF, Excel, AI, class council, promotion, absences, multi-tenant nouveau.

