# PROGICIEL DE GESTION SCOLAIRE — DOSSIER TECHNIQUE COMPLET
### Établissement unique — Version de référence pour développement (à transmettre à Cursor)

---

## 1. VISION & CADRAGE DU PROJET

- **Cible** : un seul établissement scolaire dans un premier temps. Le code est conçu pour être **cloné et redéployé** tel quel pour un nouvel établissement client (nouvelle base de données, configuration dans la table `etablissement`), sans architecture multi-tenant partagée.
- **Objectif produit** : remplacer entièrement la gestion papier — élèves, notes/bulletins, finances, absences, discipline, documents administratifs, communication, tableau de bord.
- **Plateforme** : **application web responsive** (voir §4), accessible depuis navigateur PC et mobile, avec possibilité d'installation en PWA sur téléphone. Pas de développement natif iOS/Android séparé, pas d'application desktop séparée — une seule base de code.

---

## 2. ARCHITECTURE TECHNIQUE

### 2.1 Stack

| Couche | Techno | Notes |
|---|---|---|
| Frontend | React 18 + Vite + Tailwind CSS | SPA, build rapide |
| État global | Zustand | plus léger que Redux pour ce périmètre |
| Backend | Flask 3 + Flask-Smorest (validation + doc OpenAPI auto) | tu connais déjà Flask |
| ORM | SQLAlchemy 2.x + Alembic | migrations versionnées obligatoires dès le 1er commit |
| Base de données | PostgreSQL 15+ | voir `schema_v2_mono_etablissement.sql` |
| Auth | JWT access (15 min) + refresh token (7 jours, rotation) | voir §5 |
| PDF | WeasyPrint (gabarits HTML/Jinja2) | bulletins, reçus, attestations, cartes |
| Excel | openpyxl | exports côté serveur |
| SMS | Passerelle locale à choisir selon pays (ex: orange/moov API Burkina, ou agrégateur Maroc) | prévoir une interface abstraite `NotificationProvider` pour changer de fournisseur sans réécrire le code métier |
| Email | SMTP (ex: Mailgun, SendGrid, ou SMTP direct) | |
| Conteneurisation | Docker + Docker Compose | 1 conteneur backend, 1 frontend (ou servi statique par nginx), 1 postgres |
| CI/CD | GitHub Actions | lint + tests + build à chaque push |
| Hébergement | VPS (ex: OVH, Contabo) ou service managé (Railway, Render) | le mono-tenant simplifie énormément le choix — pas besoin d'infra complexe |

### 2.2 Structure du repo

```
gestion-scolaire/
├── backend/
│   ├── app/
│   │   ├── __init__.py              # factory Flask
│   │   ├── config.py                 # config par environnement (dev/prod), lue depuis .env
│   │   ├── extensions.py             # init SQLAlchemy, JWT, etc.
│   │   ├── models/
│   │   │   ├── utilisateur.py
│   │   │   ├── eleve.py
│   │   │   ├── pedagogie.py          # matiere, evaluation, note, bulletin
│   │   │   ├── finance.py
│   │   │   ├── absence_discipline.py
│   │   │   ├── emploi_temps.py
│   │   │   ├── document.py
│   │   │   ├── notification.py
│   │   │   └── audit.py
│   │   ├── routes/                   # 1 blueprint par module
│   │   │   ├── auth.py
│   │   │   ├── eleves.py
│   │   │   ├── notes.py
│   │   │   ├── finance.py
│   │   │   ├── emploi_temps.py
│   │   │   ├── absences.py
│   │   │   ├── documents.py
│   │   │   ├── notifications.py
│   │   │   └── dashboard.py
│   │   ├── services/                 # logique métier pure, testable sans HTTP
│   │   │   ├── calcul_moyennes.py
│   │   │   ├── generation_bulletin.py
│   │   │   ├── generation_recu.py
│   │   │   ├── generation_carte_qr.py
│   │   │   └── envoi_notification.py
│   │   ├── schemas/                  # sérialisation/validation marshmallow
│   │   ├── auth/
│   │   │   ├── jwt_handler.py
│   │   │   └── permissions.py        # décorateurs @require_role(...)
│   │   ├── utils/
│   │   │   ├── audit_logger.py
│   │   │   └── chiffrement.py        # notes médicales
│   │   └── templates_pdf/            # gabarits Jinja2 pour WeasyPrint
│   ├── migrations/                   # Alembic
│   ├── tests/
│   │   ├── unit/                     # tests services (calcul moyenne, etc.)
│   │   ├── integration/              # tests routes API avec DB de test
│   │   └── conftest.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/                    # 1 dossier par module
│   │   ├── components/               # composants réutilisables (Table, Modal, FormField...)
│   │   ├── services/api/             # client axios centralisé, intercepteur refresh token
│   │   ├── store/                    # Zustand : auth, ui
│   │   ├── hooks/
│   │   ├── routes.jsx                # routes protégées par rôle
│   │   └── App.jsx
│   ├── public/
│   │   └── manifest.json             # config PWA
│   ├── tests/                        # Vitest + React Testing Library
│   ├── e2e/                          # Playwright
│   ├── package.json
│   └── Dockerfile
├── database/
│   └── schema_v2_mono_etablissement.sql
├── docs/
│   └── (ce document)
├── docker-compose.yml
├── docker-compose.prod.yml
└── .github/workflows/ci.yml
```

---

## 3. SPÉCIFICATIONS FONCTIONNELLES — LES 8 MODULES

*(Détail complet des règles métier ; le schéma de données correspondant est dans `schema_v2_mono_etablissement.sql`)*

### Module 1 — Élèves & Inscriptions
- Immatriculation automatique : format configurable dans `etablissement.format_matricule` (ex: `2025M-709`), génération via compteur séquentiel par année.
- Fiche élève 360° : identité, photo, parents/tuteurs (relation many-to-many via `eleve_parent`), pièces justificatives (upload avec type + date), notes médicales **chiffrées** (jamais en clair, jamais exposées dans une liste — uniquement sur la fiche détail avec permission explicite).
- Inscription/réinscription : un élève a au plus une inscription active par année (contrainte `UNIQUE(id_eleve, id_annee)`), changement de statut tracé avec date (`date_statut_maj`).
- Filtres : inscrits / abandons / suspendus / boursiers — requêtes indexées sur `inscription.statut`.

### Module 2 — Évaluations, Moyennes & Bulletins
- Saisie des notes par évaluation, validation 0–20 au niveau base de données (`CHECK`) ET frontend (feedback immédiat).
- Distinction **absent** vs **note à 0** — critique pour ne pas fausser les moyennes (`note.absent`).
- Moteur de calcul :
  - Moyenne matière = Σ(note × coef) / Σ(coef) — calculée via vue matérialisée `moyenne_matiere_eleve`, rafraîchie (`REFRESH MATERIALIZED VIEW CONCURRENTLY`) après chaque campagne de saisie validée par l'enseignant (pas à chaque note individuelle, pour la performance).
  - Moyenne générale = Σ(moyenne matière × coef matière) / Σ(coef matière).
  - Rang calculé par classe et trimestre au moment de la génération du bulletin (pas stocké en continu, car dépend de tous les élèves de la classe).
- Workflow bulletin : `brouillon` → `valide` (par le directeur) → `publie` (visible parents). Un bulletin publié devient en lecture seule ; toute correction après publication passe par une réédition tracée dans `journal_audit`.
- Génération PDF 1-clic via WeasyPrint, gabarit incluant rang, moyenne de classe, mentions, visa numérique du chef d'établissement.

### Module 3 — Finance & Comptabilité
- Frais paramétrables par niveau et année (`frais_scolaire`), découpés en échéances (`echeance_paiement`).
- Encaissement : génère un reçu numéroté séquentiellement (`seq_numero_recu`, format `REC-{n}`), jamais réutilisable.
- **Aucune suppression physique d'un paiement** — annulation uniquement via le champ `annule` + `motif_annulation`, conservant l'historique complet (exigence comptable).
- Suivi arriérés : vue calculée = Σ(échéances dues) − Σ(paiements non annulés) par élève, exposée au tableau de bord et exportable Excel.
- Relances : génération automatique de la liste des débiteurs + déclenchement de notifications (Module 7).

### Module 4 — Emploi du temps & Personnel
- Affectation enseignant/classe/matière par année (`affectation_enseignant`).
- Créneaux avec **contrainte d'exclusion PostgreSQL** (`EXCLUDE USING gist`) empêchant physiquement deux cours dans la même salle au même horaire — pas seulement une vérification applicative contournable.
- Suivi personnel : volume horaire, type de contrat, spécialité.

### Module 5 — Absences, Retards & Discipline
- Pointage par créneau (absence à un cours) ou journée entière (`id_creneau` nullable).
- Justification avec motif, traçabilité de qui a signalé.
- Incidents disciplinaires liés au trimestre, remontant automatiquement dans l'appréciation générale du bulletin.

### Module 6 — Documents Administratifs
- Cartes scolaires avec QR code (payload signé cryptographiquement pour éviter la falsification — voir §5.4).
- Attestations, certificats, diplômes générés depuis gabarits PDF, numérotés et tracés (`genere_par`, `date_emission`).

### Module 7 — Communication
- Interface abstraite `NotificationProvider` (pattern adaptateur) pour découpler le code métier du fournisseur SMS/email choisi — permet de changer de prestataire sans toucher au reste du code.
- File d'attente (`notification.statut`) avec retry (`tentative_count`) en cas d'échec d'envoi.
- Déclencheurs : absence du jour, publication de bulletin, retard de paiement.

### Module 8 — Tableau de Bord & BI
- Effectifs par niveau/sexe, taux de réussite par matière, taux de recouvrement financier, trésorerie.
- Calculs agrégés en base (vues SQL dédiées), pas en frontend — évite de transférer des données brutes inutilement et garantit la cohérence des chiffres affichés.

---

## 4. DÉCISION PLATEFORME — WEB RESPONSIVE + PWA

**Recommandation : une seule application web responsive, pas de version native séparée.**

Justification :
- Le personnel administratif travaille majoritairement sur ordinateur (saisie de notes, comptabilité) → le web répond déjà à ce besoin sans rien de plus.
- Les parents et enseignants en déplacement veulent consulter sur téléphone → une PWA (manifest.json + service worker minimal pour le cache statique) permet l'installation sur écran d'accueil, avec icône et plein écran, **sans** développement natif séparé ni publication sur les stores.
- Développer 3 bases de code (web, iOS, Android natif) pour un projet solo est un risque d'abandon du projet avant la fin — la contrainte de ressources doit primer sur l'exhaustivité des plateformes.
- Si un besoin réel de mode hors-ligne strict apparaît plus tard (zone sans réseau), c'est un chantier à part entière (service worker + IndexedDB + synchronisation) à traiter en v2, pas à complexifier dès le départ.

---

## 5. SÉCURITÉ & AUTHENTIFICATION — DÉTAIL COMPLET

### 5.1 Authentification
- Mots de passe hashés avec **Argon2id** (paramètres recommandés OWASP : mémoire ≥ 19 MiB, itérations ≥ 2).
- **JWT access token** courte durée (15 min) + **refresh token** longue durée (7 jours), stocké côté client en cookie `httpOnly`, `secure`, `sameSite=strict` (jamais en `localStorage`, vulnérable au XSS).
- Rotation du refresh token à chaque utilisation (`refresh_token.revoque`), révocation immédiate possible (déconnexion à distance).
- Verrouillage de compte après 5 tentatives échouées (`utilisateur.tentatives_echouees`, `verrouille_jusqu_a`).
- Changement de mot de passe obligatoire à la première connexion (`doit_changer_mdp`).
- Réinitialisation de mot de passe par lien à usage unique et expirant (`reinitialisation_mdp`), jamais par envoi du mot de passe en clair.

### 5.2 RBAC (contrôle d'accès par rôle)
| Rôle | Élèves | Notes | Validation bulletins | Finance | Config système |
|---|---|---|---|---|---|
| Administrateur/Directeur | Total | Total | Total | Total | Total |
| Enseignant | Lecture seule | Ses classes uniquement | Aucun | Aucun | Aucun |
| Agent comptable | Lecture seule | Aucun | Aucun | Total | Aucun |
| Secrétariat | Total | Aucun | Lecture seule | Lecture seule | Aucun |
| Parent (portail) | Ses enfants uniquement | Ses enfants (lecture) | — | Ses enfants (lecture) | Aucun |

Implémentation : décorateur `@require_role('directeur', 'administrateur')` sur chaque route Flask **et** vérification de propriété des données (un enseignant ne peut lire/modifier que les notes de ses classes affectées — vérifié via `affectation_enseignant`, pas seulement le rôle générique).

### 5.3 Protection des données sensibles
- Notes médicales : chiffrées en base via `pgcrypto` (`pgp_sym_encrypt`), déchiffrées uniquement à l'affichage de la fiche détail par un rôle autorisé, jamais incluses dans un export en masse.
- HTTPS obligatoire (TLS 1.2+) en production, redirection forcée HTTP→HTTPS.
- Variables sensibles (clés JWT, mot de passe DB, clés API SMS) en variables d'environnement, jamais commitées — `.env` dans `.gitignore` dès le premier commit.

### 5.4 Intégrité & traçabilité
- Table `journal_audit` : toute modification de note après saisie initiale, toute validation/republication de bulletin, tout encaissement ou annulation de paiement, toute connexion échouée — avec IP d'origine.
- QR codes des cartes scolaires signés (HMAC) pour empêcher la falsification d'une carte scannée.
- Rate limiting sur `/auth/login` (ex: Flask-Limiter, 5 req/min/IP) pour limiter le brute-force.

### 5.5 Sauvegardes
- Sauvegarde automatique quotidienne de la base PostgreSQL (`pg_dump`), rétention 30 jours minimum, stockage externalisé (pas seulement sur le même serveur).
- Test de restauration trimestriel — une sauvegarde jamais testée n'est pas une garantie.

---

## 6. STRATÉGIE DE TESTS

| Niveau | Outil | Ce qui est couvert |
|---|---|---|
| Tests unitaires backend | Pytest | Logique métier pure : calcul de moyennes, génération de numéro de reçu, règles de validation — sans dépendance HTTP ni DB réelle (mocks) |
| Tests d'intégration backend | Pytest + base de test PostgreSQL éphémère (Docker) | Routes API complètes : auth, permissions par rôle, contraintes DB (ex: chevauchement de créneaux, unicité inscription) |
| Tests unitaires frontend | Vitest + React Testing Library | Composants isolés (formulaires, tableaux, calculs d'affichage) |
| Tests end-to-end | Playwright | Parcours critiques complets : connexion → saisie note → génération bulletin ; encaissement → génération reçu ; inscription élève → affectation classe |
| Tests de sécurité | Manuel + `bandit` (analyse statique Python) | Injection SQL (mitigée par l'ORM, mais à vérifier sur toute requête brute), vérification qu'un enseignant ne peut pas accéder aux notes d'une autre classe via l'API directement |
| Tests de charge | Locust (optionnel, avant mise en prod avec volume réel) | Simulation de saisie de notes en fin de trimestre (pic d'usage concentré) |

**Priorité pratique pour un solo dev** : commence par les tests d'intégration sur les routes sensibles (auth, notes, finance) — c'est là que les bugs coûtent le plus cher (une note mal enregistrée, un paiement dupliqué). Les tests unitaires frontend et E2E peuvent suivre une fois le backend stable.

---

## 7. DÉPLOIEMENT

1. **Développement** : `docker-compose up` — Postgres + backend Flask (reload auto) + frontend Vite (HMR).
2. **CI** (GitHub Actions, à chaque push) : lint (`ruff`/`eslint`) → tests unitaires + intégration → build frontend.
3. **Production** :
   - Backend : Gunicorn derrière Nginx (reverse proxy, TLS via Let's Encrypt/Certbot).
   - Frontend : build statique servi par Nginx (ou CDN).
   - Base de données : instance PostgreSQL managée si possible (sauvegardes automatiques gérées), sinon VPS dédié avec `pg_dump` planifié (cron).
4. **Variables d'environnement de prod** : jamais dans le repo — via secrets GitHub Actions ou fichier `.env` déployé manuellement hors Git.

---

## 8. PLAN DE DÉVELOPPEMENT (ORDRE RÉALISTE)

1. Socle : Docker Compose, schéma DB appliqué, auth JWT + RBAC, CRUD établissement/année/classe
2. Module 1 complet : élèves, inscriptions, upload documents
3. Module 2 complet : matières, coefficients, saisie notes, calcul moyennes, génération bulletin PDF
4. Module 3 complet : frais, échéances, encaissement, reçus, arriérés
5. Module 4 : enseignants, affectations, emploi du temps
6. Module 5 : absences, discipline
7. Module 6 : documents administratifs, QR codes
8. Module 7 : notifications SMS/email
9. Module 8 : tableau de bord BI
10. Durcissement final : audit sécurité complet, tests de charge, backups testés, PWA finalisée

Chaque étape doit être testée (voir §6) et démontrable seule avant de passer à la suivante.
