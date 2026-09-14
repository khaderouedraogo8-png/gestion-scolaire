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
**Rôle :** Senior Backend Engineer + Security Reviewer  
**Branche :** `cursor/saas-p1-hardening-8bcc`  
**Méthode :** exécution réelle tests/lint/build + probes runtime + inspection diff (pas de confiance aveugle à l’AUDIT antérieur).

### Tests
| | |
|--|--|
| Total | **63** |
| Passed | **63** |
| Failed | **0** |
| Errors | **0** |
| Skipped | **0** |
| P0+P1 ciblés | **29 passed** (IDOR, upload, reset, errors, pagination) |

### Sécurité
- IDOR enseignant (élève / évaluation / notes / absences / discipline) : **OK**
- Upload (php, traversal, double ext, UUID serveur) : **OK**
- Reset : hash + expiry + one-time ; prod **jamais** `reset_token` (même `TESTING=True` coincé + `EXPOSE_RESET_TOKEN=1`) : **OK**
- Pas de stack/SQL/chemin/secret dans réponses client : **OK**

### API / Pagination / Frontend
- Validation Marshmallow sur routes P1 critiques : **OK** (écart P2 : `notes_medicales` hors schéma PUT)
- Pagination bornée (`page≥1`, `1≤per_page≤100`) + envelope `items` : **OK**
- FE consomme `items` / forgot-reset alignés : **OK**

### Lint / Build
- `ruff` : ✅  
- eslint : ✅ 0 erreur / 3 warnings hooks préexistants  
- `vite build` : ✅  
- Dépendances ajoutées : aucune  

### Classification
| | |
|--|--|
| **P0** | Aucun |
| **P1** | Aucun |
| **P2/P3** | Admin `mot_de_passe_temporaire` ; MIME vide soft-allow ; `notes_medicales` hors schéma ; N+1 serialize listes ; élèves sans `pagination` imbriqué ; 404/409 manuels hors envelope ; warnings hooks FE |

### Risques restants
- Mono-école (pas de `school_id`) — volontaire, hors PR  
- Temp password admin dans JSON — backlog ops  

### Statut
**READY TO MERGE**

---

## Synthèse exécutive

**P0 sécurité** + **hardening API P1 (PR #7)** : validés sur code réel (**63/63 pytest**, probes runtime OK).  
**Ne pas démarrer le multi-tenant** avant merge de cette PR.

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
