-- ============================================================================
-- PROGICIEL INTÉGRÉ DE GESTION SCOLAIRE
-- Schéma de base de données PostgreSQL 15+
-- Architecture MULTI-TENANT (base PostgreSQL partagée, isolation par school_id)
-- Référence CI / schéma cible — PR #11 Academic Foundation (Program + AcademicPeriod)
-- (voir migrations Alembic tenant_* + platform_super_admin + academic_foundation_pr11)
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 0. TENANT SaaS — racine d'isolation
-- ============================================================================

CREATE TABLE schools (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                 VARCHAR(150) NOT NULL,
    code                 VARCHAR(50) NOT NULL UNIQUE,
    email                VARCHAR(150),
    phone                VARCHAR(30),
    address              TEXT,
    city                 VARCHAR(80),
    country              VARCHAR(80),
    logo                 TEXT,
    is_active            BOOLEAN NOT NULL DEFAULT true,
    created_at           TIMESTAMPTZ DEFAULT now(),
    updated_at           TIMESTAMPTZ DEFAULT now()
    -- created_by ajouté après utilisateur (FK circulaire)
);

-- ============================================================================
-- 1. CONFIGURATION DE L'ÉTABLISSEMENT (1 profil école par tenant)
-- ============================================================================

CREATE TABLE etablissement (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    nom                  VARCHAR(150) NOT NULL,
    sigle                VARCHAR(20),
    adresse              TEXT,
    telephone            VARCHAR(30),
    email                VARCHAR(150),
    logo_url             TEXT,
    type_etablissement   VARCHAR(50),        -- Primaire, Collège, Lycée, Complexe
    pays                 VARCHAR(80),
    ville                VARCHAR(80),
    format_matricule     VARCHAR(50) DEFAULT '{ANNEE}M-{SEQ}',
    devise               VARCHAR(10) DEFAULT 'XOF',
    bulletin_template    VARCHAR(20) NOT NULL DEFAULT 'BF',
    created_at           TIMESTAMPTZ DEFAULT now(),
    updated_at           TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_etablissement_school_id UNIQUE (school_id)
);

CREATE TABLE annee_scolaire (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    libelle              VARCHAR(20) NOT NULL,   -- ex: 2025-2026
    date_debut           DATE NOT NULL,
    date_fin             DATE NOT NULL,
    est_active           BOOLEAN DEFAULT false,
    CONSTRAINT uq_annee_scolaire_school_libelle UNIQUE (school_id, libelle),
    CONSTRAINT uq_annee_scolaire_id_school UNIQUE (id, school_id)
);

-- Program / filière — school-scoped (GENERAL = compatibilité historique permanente)
CREATE TABLE program (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    code                 VARCHAR(40) NOT NULL,
    name                 VARCHAR(150) NOT NULL,
    description          TEXT,
    program_type         VARCHAR(40) NOT NULL DEFAULT 'general',
    period_type_default  VARCHAR(20) NOT NULL DEFAULT 'trimestre',
    is_active            BOOLEAN NOT NULL DEFAULT true,
    created_at           TIMESTAMPTZ DEFAULT now(),
    updated_at           TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_program_school_code UNIQUE (school_id, code),
    CONSTRAINT uq_program_id_school UNIQUE (id, school_id)
);

-- AcademicPeriod (évolution de trimestre) — Model B : Year + Program
-- Les UUID historiques trimestre sont conservés via migration Alembic.
CREATE TABLE academic_period (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    id_annee             UUID NOT NULL,
    id_program           UUID NOT NULL,
    sequence             SMALLINT NOT NULL CHECK (sequence >= 1),
    code                 VARCHAR(20) NOT NULL,
    label                VARCHAR(80) NOT NULL,
    period_type          VARCHAR(20) NOT NULL
        CHECK (period_type IN ('trimestre', 'semestre', 'custom', 'annuel')),
    date_debut           DATE NOT NULL,
    date_fin             DATE NOT NULL,
    is_active            BOOLEAN NOT NULL DEFAULT true,
    created_at           TIMESTAMPTZ DEFAULT now(),
    updated_at           TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_academic_period_id_school UNIQUE (id, school_id),
    CONSTRAINT uq_academic_period_year_program_sequence UNIQUE (id_annee, id_program, sequence),
    CONSTRAINT uq_academic_period_year_program_code UNIQUE (id_annee, id_program, code),
    CONSTRAINT ck_academic_period_dates CHECK (date_fin >= date_debut),
    CONSTRAINT fk_academic_period_annee_school FOREIGN KEY (id_annee, school_id)
        REFERENCES annee_scolaire(id, school_id) ON DELETE CASCADE,
    CONSTRAINT fk_academic_period_program_school FOREIGN KEY (id_program, school_id)
        REFERENCES program(id, school_id) ON DELETE RESTRICT
);

-- ============================================================================
-- 2. UTILISATEURS, RÔLES & SÉCURITÉ (RBAC)
-- ============================================================================

CREATE TABLE utilisateur (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nom                  VARCHAR(100) NOT NULL,
    prenom               VARCHAR(100) NOT NULL,
    email                VARCHAR(150) NOT NULL UNIQUE,
    telephone            VARCHAR(30),
    mot_de_passe_hash    TEXT NOT NULL,               -- Argon2id
    role                 VARCHAR(30) NOT NULL CHECK (role IN
                            ('administrateur', 'directeur', 'enseignant', 'agent_comptable',
                             'secretariat', 'parent', 'super_admin')),
    actif                BOOLEAN DEFAULT true,
    doit_changer_mdp     BOOLEAN DEFAULT true,        -- forcer changement au 1er login
    derniere_connexion   TIMESTAMPTZ,
    tentatives_echouees  SMALLINT DEFAULT 0,          -- verrouillage après N échecs
    verrouille_jusqu_a   TIMESTAMPTZ,
    -- NULL uniquement pour super_admin (PR #10)
    school_id            UUID REFERENCES schools(id) ON DELETE RESTRICT,
    created_at           TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT ck_utilisateur_super_admin_school CHECK (
        (role = 'super_admin' AND school_id IS NULL)
        OR (role <> 'super_admin' AND school_id IS NOT NULL)
    )
);

-- schools.created_by (après utilisateur — FK circulaire)
ALTER TABLE schools
    ADD COLUMN created_by UUID REFERENCES utilisateur(id) ON DELETE SET NULL;
CREATE INDEX ix_schools_created_by ON schools (created_by);

-- Parent-only : isolation via utilisateur.school_id
CREATE TABLE refresh_token (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_utilisateur       UUID NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
    token_hash           TEXT NOT NULL,
    user_agent           TEXT,
    ip_creation          INET,
    expire_at            TIMESTAMPTZ NOT NULL,
    revoque              BOOLEAN DEFAULT false,
    created_at           TIMESTAMPTZ DEFAULT now()
);

-- Parent-only : isolation via utilisateur.school_id
CREATE TABLE reinitialisation_mdp (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_utilisateur       UUID NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
    token_hash           TEXT NOT NULL,
    expire_at            TIMESTAMPTZ NOT NULL,
    utilise              BOOLEAN DEFAULT false,
    created_at           TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- 3. MODULE 1 : ÉLÈVES & INSCRIPTIONS
-- ============================================================================

CREATE TABLE parent_tuteur (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    id_utilisateur       UUID REFERENCES utilisateur(id) ON DELETE SET NULL,  -- si compte portail parent
    nom                  VARCHAR(100) NOT NULL,
    prenom               VARCHAR(100) NOT NULL,
    lien_parente         VARCHAR(30),
    telephone            VARCHAR(30),
    email                VARCHAR(150),
    profession           VARCHAR(100),
    adresse              TEXT
);

CREATE TABLE eleve (
    id                        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id                 UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    matricule                 VARCHAR(30) NOT NULL,
    nom                       VARCHAR(100) NOT NULL,
    prenom                    VARCHAR(100) NOT NULL,
    sexe                      CHAR(1) CHECK (sexe IN ('M', 'F')),
    date_naissance            DATE,
    lieu_naissance            VARCHAR(100),
    adresse                   TEXT,
    photo_url                 TEXT,
    notes_medicales_chiffrees BYTEA,          -- chiffré via pgcrypto (pgp_sym_encrypt), jamais en clair
    pieces_justificatives     JSONB,          -- [{type, url, date_upload}]
    created_at                TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_eleve_school_matricule UNIQUE (school_id, matricule),
    CONSTRAINT uq_eleve_id_school UNIQUE (id, school_id)
);

-- Parent-only : isolation via eleve / parent_tuteur.school_id
CREATE TABLE eleve_parent (
    id_eleve             UUID NOT NULL REFERENCES eleve(id) ON DELETE CASCADE,
    id_parent            UUID NOT NULL REFERENCES parent_tuteur(id) ON DELETE CASCADE,
    tuteur_legal         BOOLEAN DEFAULT false,
    PRIMARY KEY (id_eleve, id_parent)
);

CREATE TABLE niveau_etude (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    id_program           UUID NOT NULL,
    libelle              VARCHAR(50) NOT NULL,   -- ex: 6ème, Terminale
    ordre                SMALLINT,
    cycle                VARCHAR(20) NOT NULL DEFAULT 'premier'
        CHECK (cycle IN ('premier', 'second')),
    CONSTRAINT uq_niveau_etude_school_program_libelle UNIQUE (school_id, id_program, libelle),
    CONSTRAINT uq_niveau_etude_id_school UNIQUE (id, school_id),
    CONSTRAINT uq_niveau_etude_id_program UNIQUE (id, id_program),
    CONSTRAINT fk_niveau_etude_program_school FOREIGN KEY (id_program, school_id)
        REFERENCES program(id, school_id) ON DELETE RESTRICT
);

CREATE TABLE classe (
    id                        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id                 UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    id_niveau                 UUID NOT NULL,
    id_annee                  UUID NOT NULL,
    id_program                UUID NOT NULL,
    libelle                   VARCHAR(50) NOT NULL,        -- ex: 6ème A
    id_professeur_principal   UUID,                        -- FK ajoutée après création de enseignant
    capacite_max              INTEGER DEFAULT 50,
    CONSTRAINT uq_classe_id_school UNIQUE (id, school_id),
    CONSTRAINT fk_classe_niveau_school FOREIGN KEY (id_niveau, school_id)
        REFERENCES niveau_etude(id, school_id) ON DELETE RESTRICT,
    CONSTRAINT fk_classe_annee_school FOREIGN KEY (id_annee, school_id)
        REFERENCES annee_scolaire(id, school_id) ON DELETE CASCADE,
    CONSTRAINT fk_classe_program_school FOREIGN KEY (id_program, school_id)
        REFERENCES program(id, school_id) ON DELETE RESTRICT,
    CONSTRAINT fk_classe_niveau_program FOREIGN KEY (id_niveau, id_program)
        REFERENCES niveau_etude(id, id_program) ON DELETE RESTRICT,
    UNIQUE (id_annee, libelle)
);

CREATE TABLE inscription (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    id_eleve             UUID NOT NULL,
    id_classe            UUID NOT NULL,
    id_annee             UUID NOT NULL,
    statut               VARCHAR(20) NOT NULL DEFAULT 'inscrit'
                            CHECK (statut IN ('inscrit', 'abandon', 'suspendu', 'reinscrit', 'diplome')),
    est_boursier         BOOLEAN DEFAULT false,
    taux_reduction       NUMERIC(5,2) DEFAULT 0,
    date_inscription     DATE DEFAULT CURRENT_DATE,
    date_statut_maj      DATE,
    CONSTRAINT fk_inscription_eleve_school FOREIGN KEY (id_eleve, school_id)
        REFERENCES eleve(id, school_id) ON DELETE CASCADE,
    CONSTRAINT fk_inscription_classe_school FOREIGN KEY (id_classe, school_id)
        REFERENCES classe(id, school_id) ON DELETE RESTRICT,
    CONSTRAINT fk_inscription_annee_school FOREIGN KEY (id_annee, school_id)
        REFERENCES annee_scolaire(id, school_id) ON DELETE CASCADE,
    UNIQUE (id_eleve, id_annee)
);

-- ============================================================================
-- 4. PERSONNEL ENSEIGNANT & AFFECTATIONS
-- ============================================================================

CREATE TABLE enseignant (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    id_utilisateur       UUID REFERENCES utilisateur(id) ON DELETE SET NULL,
    nom                  VARCHAR(100) NOT NULL,
    prenom               VARCHAR(100) NOT NULL,
    specialite           VARCHAR(100),
    type_contrat         VARCHAR(30),
    taux_horaire         NUMERIC(10,2),
    telephone            VARCHAR(30),
    email                VARCHAR(150),
    CONSTRAINT uq_enseignant_id_school UNIQUE (id, school_id)
);

ALTER TABLE classe
    ADD CONSTRAINT fk_classe_prof_principal
    FOREIGN KEY (id_professeur_principal) REFERENCES enseignant(id) ON DELETE SET NULL;

CREATE TABLE matiere (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    libelle              VARCHAR(80) NOT NULL,
    code                 VARCHAR(20),
    CONSTRAINT uq_matiere_id_school UNIQUE (id, school_id)
);

-- Parent-only : isolation via matiere / niveau_etude.school_id
CREATE TABLE coefficient_matiere (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_matiere           UUID NOT NULL REFERENCES matiere(id) ON DELETE CASCADE,
    id_niveau            UUID NOT NULL REFERENCES niveau_etude(id) ON DELETE CASCADE,
    coefficient          NUMERIC(4,2) NOT NULL,
    UNIQUE (id_matiere, id_niveau)
);

-- ============================================================================
-- 4b. GRADING RULES ENGINE (PR #12) — indépendant du design bulletin
-- Poids d'évaluation (composants) ≠ coefficient matière (ci-dessus).
-- ============================================================================

CREATE TABLE evaluation_type (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    code                 VARCHAR(40) NOT NULL,
    label                VARCHAR(100) NOT NULL,
    is_system            BOOLEAN NOT NULL DEFAULT false,
    is_active            BOOLEAN NOT NULL DEFAULT true,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_evaluation_type_school_code UNIQUE (school_id, code),
    CONSTRAINT uq_evaluation_type_id_school UNIQUE (id, school_id)
);
CREATE INDEX ix_evaluation_type_school_id ON evaluation_type (school_id);
CREATE INDEX ix_evaluation_type_school_active ON evaluation_type (school_id, is_active);

CREATE TABLE grading_ruleset (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    code                 VARCHAR(40) NOT NULL,
    name                 VARCHAR(150) NOT NULL,
    description          TEXT,
    status               VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'active', 'archived')),
    version              INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
    id_annee             UUID NOT NULL,
    id_program           UUID,
    id_niveau            UUID,
    id_matiere           UUID,
    scale_max            NUMERIC(6,2) NOT NULL DEFAULT 20.00 CHECK (scale_max > 0),
    rounding_mode        VARCHAR(20) NOT NULL DEFAULT 'half_up'
        CHECK (rounding_mode IN ('half_up', 'half_even', 'down', 'up')),
    rounding_precision   SMALLINT NOT NULL DEFAULT 2 CHECK (rounding_precision >= 0),
    created_by           UUID REFERENCES utilisateur(id) ON DELETE SET NULL,
    activated_at         TIMESTAMPTZ,
    archived_at          TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_grading_ruleset_school_code_version UNIQUE (school_id, code, version),
    CONSTRAINT uq_grading_ruleset_id_school UNIQUE (id, school_id),
    CONSTRAINT ck_grading_ruleset_niveau_requires_program
        CHECK ((id_niveau IS NULL) OR (id_program IS NOT NULL)),
    CONSTRAINT fk_grading_ruleset_annee_school FOREIGN KEY (id_annee, school_id)
        REFERENCES annee_scolaire(id, school_id) ON DELETE RESTRICT,
    CONSTRAINT fk_grading_ruleset_program_school FOREIGN KEY (id_program, school_id)
        REFERENCES program(id, school_id) ON DELETE RESTRICT,
    CONSTRAINT fk_grading_ruleset_niveau_school FOREIGN KEY (id_niveau, school_id)
        REFERENCES niveau_etude(id, school_id) ON DELETE RESTRICT,
    CONSTRAINT fk_grading_ruleset_matiere_school FOREIGN KEY (id_matiere, school_id)
        REFERENCES matiere(id, school_id) ON DELETE RESTRICT
);
CREATE INDEX ix_grading_ruleset_school_id ON grading_ruleset (school_id);
CREATE INDEX ix_grading_ruleset_resolve ON grading_ruleset
    (school_id, id_annee, status, id_program, id_niveau, id_matiere);
CREATE INDEX ix_grading_ruleset_school_code_status ON grading_ruleset (school_id, code, status);

CREATE TABLE grading_rule_component (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    ruleset_id           UUID NOT NULL,
    code                 VARCHAR(40) NOT NULL,
    label                VARCHAR(100) NOT NULL,
    id_evaluation_type   UUID NOT NULL,
    evaluation_context   VARCHAR(40) NOT NULL DEFAULT 'normal'
        CHECK (evaluation_context IN ('normal', 'examen_blanc', 'rattrapage', 'session_2')),
    weight               NUMERIC(5,2) NOT NULL CHECK (weight > 0 AND weight <= 100),
    sequence             SMALLINT NOT NULL CHECK (sequence >= 1),
    is_required          BOOLEAN NOT NULL DEFAULT true,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_grading_rule_component_ruleset_code UNIQUE (ruleset_id, code),
    CONSTRAINT uq_grading_rule_component_ruleset_sequence UNIQUE (ruleset_id, sequence),
    CONSTRAINT uq_grading_rule_component_id_school UNIQUE (id, school_id),
    CONSTRAINT fk_grading_rule_component_ruleset_school FOREIGN KEY (ruleset_id, school_id)
        REFERENCES grading_ruleset(id, school_id) ON DELETE CASCADE,
    CONSTRAINT fk_grading_rule_component_eval_type_school FOREIGN KEY (id_evaluation_type, school_id)
        REFERENCES evaluation_type(id, school_id) ON DELETE RESTRICT
);
CREATE INDEX ix_grading_rule_component_school_id ON grading_rule_component (school_id);
CREATE INDEX ix_grading_rule_component_ruleset_id ON grading_rule_component (ruleset_id);
CREATE INDEX ix_grading_rule_component_ruleset_seq ON grading_rule_component (ruleset_id, sequence);

CREATE TABLE affectation_enseignant (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id              UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    id_enseignant          UUID NOT NULL,
    id_classe              UUID NOT NULL,
    id_matiere             UUID NOT NULL,
    id_annee               UUID NOT NULL,
    volume_horaire_hebdo   NUMERIC(5,2),
    CONSTRAINT fk_affectation_enseignant_school FOREIGN KEY (id_enseignant, school_id)
        REFERENCES enseignant(id, school_id) ON DELETE CASCADE,
    CONSTRAINT fk_affectation_classe_school FOREIGN KEY (id_classe, school_id)
        REFERENCES classe(id, school_id) ON DELETE CASCADE,
    CONSTRAINT fk_affectation_matiere_school FOREIGN KEY (id_matiere, school_id)
        REFERENCES matiere(id, school_id) ON DELETE CASCADE,
    CONSTRAINT fk_affectation_annee_school FOREIGN KEY (id_annee, school_id)
        REFERENCES annee_scolaire(id, school_id) ON DELETE CASCADE,
    UNIQUE (id_enseignant, id_classe, id_matiere, id_annee)
);

-- ============================================================================
-- 5. EMPLOI DU TEMPS
-- ============================================================================

CREATE TABLE salle (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    libelle              VARCHAR(50) NOT NULL,
    capacite             INTEGER
);

CREATE EXTENSION IF NOT EXISTS btree_gist;

-- Parent-only : isolation via affectation_enseignant / salle.school_id
CREATE TABLE creneau_emploi_temps (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_affectation       UUID NOT NULL REFERENCES affectation_enseignant(id) ON DELETE CASCADE,
    id_salle             UUID REFERENCES salle(id) ON DELETE SET NULL,
    jour_semaine         SMALLINT NOT NULL CHECK (jour_semaine BETWEEN 1 AND 7),
    heure_debut          TIME NOT NULL,
    heure_fin            TIME NOT NULL,
    CHECK (heure_fin > heure_debut)
);

-- Empêche deux cours dans la même salle en même temps (expression directe, sans colonne GENERATED)
ALTER TABLE creneau_emploi_temps
    ADD CONSTRAINT no_chevauchement_salle
    EXCLUDE USING gist (
        id_salle WITH =,
        tsrange(
            (DATE '2000-01-03' + (jour_semaine - 1) * INTERVAL '1 day' + heure_debut)::timestamp,
            (DATE '2000-01-03' + (jour_semaine - 1) * INTERVAL '1 day' + heure_fin)::timestamp,
            '[)'
        ) WITH &&
    ) WHERE (id_salle IS NOT NULL);


-- ============================================================================
-- 6. MODULE 2 : ÉVALUATIONS, NOTES & BULLETINS
-- ============================================================================

CREATE TABLE evaluation (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    id_classe            UUID NOT NULL,
    id_matiere           UUID NOT NULL,
    id_trimestre         UUID NOT NULL REFERENCES academic_period(id) ON DELETE CASCADE,
    id_enseignant        UUID NOT NULL,
    type_evaluation      VARCHAR(20) NOT NULL,
    coefficient          NUMERIC(4,2) NOT NULL DEFAULT 1,
    date_evaluation      DATE NOT NULL,
    libelle              VARCHAR(150),
    statut_publication   VARCHAR(20) NOT NULL DEFAULT 'brouillon'
        CHECK (statut_publication IN ('brouillon', 'publie')),
    statut_saisie        VARCHAR(20) NOT NULL DEFAULT 'en_cours'
        CHECK (statut_saisie IN ('en_cours', 'cloturee')),
    CONSTRAINT uq_evaluation_id_school UNIQUE (id, school_id),
    CONSTRAINT fk_evaluation_classe_school FOREIGN KEY (id_classe, school_id)
        REFERENCES classe(id, school_id) ON DELETE CASCADE,
    CONSTRAINT fk_evaluation_matiere_school FOREIGN KEY (id_matiere, school_id)
        REFERENCES matiere(id, school_id) ON DELETE CASCADE,
    CONSTRAINT fk_evaluation_enseignant_school FOREIGN KEY (id_enseignant, school_id)
        REFERENCES enseignant(id, school_id) ON DELETE RESTRICT
);

-- Parent-only : isolation via classe / matiere.school_id
CREATE TABLE programme_devoir (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_classe            UUID NOT NULL REFERENCES classe(id) ON DELETE CASCADE,
    id_matiere           UUID NOT NULL REFERENCES matiere(id) ON DELETE CASCADE,
    jour_semaine         SMALLINT NOT NULL CHECK (jour_semaine BETWEEN 1 AND 7),
    frequence            VARCHAR(20) NOT NULL DEFAULT 'hebdomadaire'
        CHECK (frequence IN ('hebdomadaire', 'quinzomadaire')),
    note                 VARCHAR(255),
    id_annee             UUID NOT NULL REFERENCES annee_scolaire(id) ON DELETE CASCADE,
    UNIQUE (id_classe, id_matiere, jour_semaine, id_annee)
);

-- Parent-only : isolation via annee_scolaire.school_id
CREATE TABLE evenement_calendrier (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_annee             UUID NOT NULL REFERENCES annee_scolaire(id) ON DELETE CASCADE,
    type_evenement       VARCHAR(30) NOT NULL
        CHECK (type_evenement IN ('ferie', 'vacances', 'rentree', 'examen_officiel', 'autre')),
    libelle              VARCHAR(150) NOT NULL,
    date_debut           DATE NOT NULL,
    date_fin             DATE NOT NULL,
    bloque_programmation BOOLEAN NOT NULL DEFAULT true
);

-- Parent-only : isolation via classe / matiere / enseignant.school_id
CREATE TABLE seance_cours (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_classe            UUID NOT NULL REFERENCES classe(id) ON DELETE CASCADE,
    id_matiere           UUID NOT NULL REFERENCES matiere(id) ON DELETE CASCADE,
    id_enseignant        UUID NOT NULL REFERENCES enseignant(id) ON DELETE RESTRICT,
    id_annee             UUID NOT NULL REFERENCES annee_scolaire(id) ON DELETE CASCADE,
    date_seance          DATE NOT NULL,
    contenu              TEXT NOT NULL,
    UNIQUE (id_classe, id_matiere, date_seance)
);

CREATE TABLE note (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    id_evaluation        UUID NOT NULL,
    id_eleve             UUID NOT NULL,
    valeur_note          NUMERIC(6,2) CHECK (valeur_note IS NULL OR valeur_note >= 0),
    absent               BOOLEAN DEFAULT false,     -- distinct d'une note à 0
    appreciation         VARCHAR(255),
    saisi_par            UUID REFERENCES utilisateur(id),
    modifie_par          UUID REFERENCES utilisateur(id),
    saisi_le             TIMESTAMPTZ DEFAULT now(),
    modifie_le           TIMESTAMPTZ,
    CONSTRAINT fk_note_evaluation_school FOREIGN KEY (id_evaluation, school_id)
        REFERENCES evaluation(id, school_id) ON DELETE CASCADE,
    CONSTRAINT fk_note_eleve_school FOREIGN KEY (id_eleve, school_id)
        REFERENCES eleve(id, school_id) ON DELETE CASCADE,
    UNIQUE (id_evaluation, id_eleve)
);

CREATE MATERIALIZED VIEW moyenne_matiere_eleve AS
SELECT
    n.id_eleve,
    e.id_classe,
    e.id_matiere,
    e.id_trimestre,
    ROUND(
        SUM(n.valeur_note * e.coefficient) FILTER (WHERE n.absent = false)
        / NULLIF(SUM(e.coefficient) FILTER (WHERE n.absent = false), 0)
    , 2) AS moyenne
FROM note n
JOIN evaluation e ON e.id = n.id_evaluation
GROUP BY n.id_eleve, e.id_classe, e.id_matiere, e.id_trimestre;

CREATE UNIQUE INDEX idx_moyenne_unique ON moyenne_matiere_eleve(id_eleve, id_classe, id_matiere, id_trimestre);

CREATE TABLE academic_subject_result (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    id_eleve             UUID NOT NULL,
    id_classe            UUID NOT NULL,
    id_matiere           UUID NOT NULL,
    id_period            UUID NOT NULL,
    moyenne              NUMERIC(6,2),
    coefficient          NUMERIC(4,2) NOT NULL DEFAULT 1,
    scale_max            NUMERIC(6,2),
    ruleset_id           UUID,
    ruleset_version      INTEGER,
    ruleset_code         VARCHAR(40),
    incomplete           BOOLEAN NOT NULL DEFAULT false,
    incomplete_reason    VARCHAR(255),
    source               VARCHAR(20) NOT NULL DEFAULT 'rules_engine'
                         CHECK (source IN ('rules_engine', 'legacy')),
    is_stale             BOOLEAN NOT NULL DEFAULT false,
    calculation_trace    JSONB,
    calculated_at        TIMESTAMPTZ DEFAULT now(),
    created_at           TIMESTAMPTZ DEFAULT now(),
    updated_at           TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_academic_subject_result_scope
        UNIQUE (school_id, id_eleve, id_classe, id_matiere, id_period),
    CONSTRAINT uq_academic_subject_result_id_school UNIQUE (id, school_id),
    CONSTRAINT fk_academic_subject_result_eleve_school FOREIGN KEY (id_eleve, school_id)
        REFERENCES eleve(id, school_id) ON DELETE CASCADE,
    CONSTRAINT fk_academic_subject_result_classe_school FOREIGN KEY (id_classe, school_id)
        REFERENCES classe(id, school_id) ON DELETE CASCADE,
    CONSTRAINT fk_academic_subject_result_matiere_school FOREIGN KEY (id_matiere, school_id)
        REFERENCES matiere(id, school_id) ON DELETE CASCADE,
    CONSTRAINT fk_academic_subject_result_period_school FOREIGN KEY (id_period, school_id)
        REFERENCES academic_period(id, school_id) ON DELETE CASCADE,
    CONSTRAINT fk_academic_subject_result_ruleset_school FOREIGN KEY (ruleset_id, school_id)
        REFERENCES grading_ruleset(id, school_id) ON DELETE SET NULL
);
CREATE INDEX ix_academic_subject_result_school_id ON academic_subject_result (school_id);
CREATE INDEX ix_academic_subject_result_id_eleve ON academic_subject_result (id_eleve);
CREATE INDEX ix_academic_subject_result_id_classe ON academic_subject_result (id_classe);
CREATE INDEX ix_academic_subject_result_id_matiere ON academic_subject_result (id_matiere);
CREATE INDEX ix_academic_subject_result_id_period ON academic_subject_result (id_period);
CREATE INDEX ix_academic_subject_result_stale ON academic_subject_result (school_id, is_stale);

CREATE TABLE bulletin (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id              UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    id_eleve               UUID NOT NULL,
    id_trimestre           UUID NOT NULL REFERENCES academic_period(id) ON DELETE CASCADE,
    moyenne_generale       NUMERIC(6,2),
    rang                   INTEGER,
    effectif_classe        INTEGER,
    moyenne_classe         NUMERIC(6,2),
    mention                VARCHAR(50),
    appreciation_generale  TEXT,
    statut                 VARCHAR(20) DEFAULT 'brouillon' CHECK (statut IN ('brouillon', 'valide', 'publie')),
    valide_par             UUID REFERENCES utilisateur(id),
    date_generation        TIMESTAMPTZ DEFAULT now(),
    pdf_url                TEXT,
    rulesets_snapshot      JSONB,
    results_calculated_at  TIMESTAMPTZ,
    CONSTRAINT fk_bulletin_eleve_school FOREIGN KEY (id_eleve, school_id)
        REFERENCES eleve(id, school_id) ON DELETE CASCADE,
    UNIQUE (id_eleve, id_trimestre)
);

-- ============================================================================
-- 7. MODULE 3 : FINANCE & COMPTABILITÉ
-- ============================================================================

CREATE TABLE frais_scolaire (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    id_niveau            UUID NOT NULL,
    id_annee             UUID NOT NULL,
    motif                VARCHAR(50) NOT NULL,   -- Scolarité, Cantine, Transport, Inscription
    montant_total        NUMERIC(12,2) NOT NULL,
    CONSTRAINT fk_frais_niveau_school FOREIGN KEY (id_niveau, school_id)
        REFERENCES niveau_etude(id, school_id) ON DELETE RESTRICT,
    CONSTRAINT fk_frais_annee_school FOREIGN KEY (id_annee, school_id)
        REFERENCES annee_scolaire(id, school_id) ON DELETE CASCADE,
    CONSTRAINT uq_frais_school_niveau_annee_motif UNIQUE (school_id, id_niveau, id_annee, motif)
);

-- Parent-only : isolation via frais_scolaire.school_id
CREATE TABLE echeance_paiement (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_frais             UUID NOT NULL REFERENCES frais_scolaire(id) ON DELETE CASCADE,
    libelle              VARCHAR(50),
    montant              NUMERIC(12,2) NOT NULL,
    date_echeance        DATE NOT NULL
);
CREATE UNIQUE INDEX uq_echeance_frais_libelle_date
    ON echeance_paiement (id_frais, COALESCE(libelle, ''), date_echeance);

CREATE SEQUENCE seq_numero_recu START 1;

CREATE TABLE paiement (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    id_eleve             UUID NOT NULL,
    id_annee             UUID NOT NULL,
    id_echeance          UUID REFERENCES echeance_paiement(id) ON DELETE SET NULL,
    motif                VARCHAR(50) NOT NULL,
    montant_verse        NUMERIC(12,2) NOT NULL CHECK (montant_verse > 0),
    mode_paiement        VARCHAR(30),            -- Espèces, Mobile Money, Virement
    numero_recu          VARCHAR(30) NOT NULL DEFAULT ('REC-' || nextval('seq_numero_recu')),
    encaisse_par         UUID REFERENCES utilisateur(id),
    annule               BOOLEAN DEFAULT false,  -- annulation traçable, jamais de DELETE sur un paiement
    motif_annulation     TEXT,
    date_paiement        TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_paiement_school_numero_recu UNIQUE (school_id, numero_recu),
    CONSTRAINT fk_paiement_eleve_school FOREIGN KEY (id_eleve, school_id)
        REFERENCES eleve(id, school_id) ON DELETE CASCADE,
    CONSTRAINT fk_paiement_annee_school FOREIGN KEY (id_annee, school_id)
        REFERENCES annee_scolaire(id, school_id) ON DELETE CASCADE
);

CREATE TABLE school_setup_progress (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL UNIQUE REFERENCES schools(id) ON DELETE CASCADE,
    niveaux_ok           BOOLEAN NOT NULL DEFAULT false,
    classes_ok           BOOLEAN NOT NULL DEFAULT false,
    frais_ok             BOOLEAN NOT NULL DEFAULT false,
    eleves_ok            BOOLEAN NOT NULL DEFAULT false,
    enseignants_ok       BOOLEAN NOT NULL DEFAULT false,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE plan_comptable_syscohada (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    compte               VARCHAR(16) NOT NULL,
    libelle              VARCHAR(120) NOT NULL,
    classe               VARCHAR(8) NOT NULL,
    actif                BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT uq_plan_comptable_school_compte UNIQUE (school_id, compte)
);

-- ============================================================================
-- 8. MODULE 5 : ABSENCES, RETARDS & DISCIPLINE
-- ============================================================================

CREATE TABLE absence (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    id_eleve             UUID NOT NULL,
    id_creneau           UUID REFERENCES creneau_emploi_temps(id) ON DELETE SET NULL,  -- NULL = journée entière
    date_absence         DATE NOT NULL,
    type_absence         VARCHAR(20) CHECK (type_absence IN ('absence', 'retard')),
    justifiee            BOOLEAN DEFAULT false,
    motif                TEXT,
    signale_par          UUID REFERENCES utilisateur(id),
    created_at           TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT fk_absence_eleve_school FOREIGN KEY (id_eleve, school_id)
        REFERENCES eleve(id, school_id) ON DELETE CASCADE
);

CREATE TABLE incident_disciplinaire (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    id_eleve             UUID NOT NULL,
    id_trimestre         UUID REFERENCES academic_period(id) ON DELETE SET NULL,
    type_incident        VARCHAR(30) CHECK (type_incident IN ('avertissement', 'blame', 'exclusion_temporaire')),
    description          TEXT,
    date_incident         DATE NOT NULL,
    declare_par           UUID REFERENCES utilisateur(id),
    CONSTRAINT fk_incident_disciplinaire_eleve_school FOREIGN KEY (id_eleve, school_id)
        REFERENCES eleve(id, school_id) ON DELETE CASCADE
);

-- ============================================================================
-- 9. MODULE 6 : DOCUMENTS ADMINISTRATIFS
-- ============================================================================

CREATE TABLE document_administratif (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    id_eleve             UUID NOT NULL,
    type_document        VARCHAR(30) CHECK (type_document IN
                            ('carte_scolaire', 'attestation_scolarite', 'certificat', 'diplome')),
    qr_code_data         TEXT,
    date_emission        DATE DEFAULT CURRENT_DATE,
    date_expiration      DATE,
    pdf_url              TEXT,
    genere_par           UUID REFERENCES utilisateur(id),
    CONSTRAINT fk_document_administratif_eleve_school FOREIGN KEY (id_eleve, school_id)
        REFERENCES eleve(id, school_id) ON DELETE CASCADE
);

-- ============================================================================
-- 10. MODULE 7 : COMMUNICATION & NOTIFICATIONS
-- ============================================================================

CREATE TABLE notification (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE RESTRICT,
    id_eleve             UUID,
    id_parent            UUID REFERENCES parent_tuteur(id) ON DELETE CASCADE,
    canal                VARCHAR(10) CHECK (canal IS NULL OR canal IN ('sms', 'email', 'interne')),
    type_notification    VARCHAR(30),   -- absence, bulletin, paiement, relance, digest_absences
    contenu              TEXT,
    statut               VARCHAR(20) DEFAULT 'en_attente' CHECK (statut IN ('en_attente', 'envoye', 'echec')),
    tentative_count       SMALLINT DEFAULT 0,
    envoye_le            TIMESTAMPTZ,
    lu_le                TIMESTAMPTZ,           -- inbox parent : marquage lu
    idempotency_key      VARCHAR(120),          -- digest / jobs idempotents
    created_at            TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT fk_notification_eleve_school FOREIGN KEY (id_eleve, school_id)
        REFERENCES eleve(id, school_id) ON DELETE CASCADE
);

-- ============================================================================
-- 11. AUDIT — traçabilité obligatoire sur les actions sensibles
-- ============================================================================

CREATE TABLE journal_audit (
    id                       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- Nullable pour événements plateforme purs (bootstrap SUPER_ADMIN, etc.)
    school_id                UUID REFERENCES schools(id) ON DELETE RESTRICT,
    id_utilisateur           UUID REFERENCES utilisateur(id) ON DELETE SET NULL,
    action                   VARCHAR(50) NOT NULL,  -- MODIFICATION_NOTE, VALIDATION_BULLETIN, PAIEMENT_ENCAISSE, PAIEMENT_ANNULE, CONNEXION, ECHEC_CONNEXION...
    table_cible              VARCHAR(50),
    id_enregistrement_cible  UUID,
    ip_origine               INET,
    details                  JSONB,
    created_at               TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- INDEX DE PERFORMANCE
-- ============================================================================

CREATE INDEX ix_utilisateur_school_id ON utilisateur (school_id);
CREATE INDEX ix_etablissement_school_id ON etablissement (school_id);
CREATE INDEX ix_annee_scolaire_school_id ON annee_scolaire (school_id);
CREATE INDEX ix_program_school_id ON program (school_id);
CREATE INDEX ix_program_school_active ON program (school_id, is_active);
CREATE INDEX ix_academic_period_school_id ON academic_period (school_id);
CREATE INDEX ix_academic_period_year_program ON academic_period (id_annee, id_program);
CREATE INDEX ix_niveau_etude_school_id ON niveau_etude (school_id);
CREATE INDEX ix_niveau_etude_id_program ON niveau_etude (id_program);
CREATE INDEX ix_eleve_school_id ON eleve (school_id);
CREATE INDEX ix_parent_tuteur_school_id ON parent_tuteur (school_id);
CREATE INDEX ix_enseignant_school_id ON enseignant (school_id);
CREATE INDEX ix_matiere_school_id ON matiere (school_id);
CREATE INDEX ix_salle_school_id ON salle (school_id);
CREATE INDEX ix_frais_scolaire_school_id ON frais_scolaire (school_id);
CREATE INDEX ix_classe_school_id ON classe (school_id);
CREATE INDEX ix_classe_id_program ON classe (id_program);
CREATE INDEX ix_evaluation_school_id ON evaluation (school_id);
CREATE INDEX ix_paiement_school_id ON paiement (school_id);
CREATE INDEX ix_absence_school_id ON absence (school_id);
CREATE INDEX ix_incident_disciplinaire_school_id ON incident_disciplinaire (school_id);
CREATE INDEX ix_document_administratif_school_id ON document_administratif (school_id);
CREATE INDEX ix_notification_school_id ON notification (school_id);
CREATE UNIQUE INDEX ix_notification_idempotency_key ON notification (school_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
CREATE INDEX ix_notification_id_parent_created ON notification (id_parent, created_at);
CREATE INDEX ix_journal_audit_school_id ON journal_audit (school_id);
CREATE INDEX ix_bulletin_school_id ON bulletin (school_id);
CREATE INDEX ix_inscription_school_id ON inscription (school_id);
CREATE INDEX ix_note_school_id ON note (school_id);
CREATE INDEX ix_affectation_enseignant_school_id ON affectation_enseignant (school_id);

CREATE INDEX idx_inscription_classe ON inscription(id_classe);
CREATE INDEX idx_note_eleve ON note(id_eleve);
CREATE INDEX idx_paiement_eleve_annee ON paiement(id_eleve, id_annee);
CREATE INDEX idx_absence_eleve_date ON absence(id_eleve, date_absence);
CREATE INDEX idx_evaluation_classe_trimestre ON evaluation(id_classe, id_trimestre);
CREATE INDEX idx_journal_audit_utilisateur ON journal_audit(id_utilisateur, created_at);
CREATE INDEX idx_eleve_nom_prenom ON eleve(nom, prenom);

-- ============================================================================
-- 12. DEERFLOW FULL DELIVERY — modules A/B foundation
-- ============================================================================

ALTER TABLE etablissement
    ADD COLUMN IF NOT EXISTS matricule_sequence INTEGER NOT NULL DEFAULT 0;

CREATE TABLE admission_dossier (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_annee             UUID,
    nom                  VARCHAR(100) NOT NULL,
    prenom               VARCHAR(100) NOT NULL,
    sexe                 VARCHAR(1),
    date_naissance       DATE,
    lieu_naissance       VARCHAR(100),
    telephone_parent     VARCHAR(30),
    email_parent         VARCHAR(150),
    niveau_demande       VARCHAR(50),
    statut               VARCHAR(30) NOT NULL DEFAULT 'brouillon',
    pieces               JSONB,
    id_eleve             UUID,
    notes                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_admission_dossier_school_id ON admission_dossier (school_id);
CREATE INDEX ix_admission_dossier_school_statut ON admission_dossier (school_id, statut);

CREATE TABLE fratrie (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    libelle              VARCHAR(120),
    id_parent_principal  UUID,
    notes                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_fratrie_school_id ON fratrie (school_id);

CREATE TABLE eleve_fratrie (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_eleve             UUID NOT NULL,
    id_fratrie           UUID NOT NULL REFERENCES fratrie(id) ON DELETE CASCADE,
    CONSTRAINT uq_eleve_fratrie_pair UNIQUE (id_eleve, id_fratrie)
);
CREATE INDEX ix_eleve_fratrie_school_id ON eleve_fratrie (school_id);
CREATE INDEX ix_eleve_fratrie_id_eleve ON eleve_fratrie (id_eleve);
CREATE INDEX ix_eleve_fratrie_id_fratrie ON eleve_fratrie (id_fratrie);

CREATE TABLE remise_regle (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    code                 VARCHAR(40) NOT NULL,
    libelle              VARCHAR(120) NOT NULL,
    type_remise          VARCHAR(20) NOT NULL DEFAULT 'pourcent',
    valeur               NUMERIC(12, 2) NOT NULL,
    condition_type       VARCHAR(40),
    condition_valeur     VARCHAR(80),
    actif                BOOLEAN NOT NULL DEFAULT true,
    priorite             INTEGER NOT NULL DEFAULT 0,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_remise_regle_school_code UNIQUE (school_id, code)
);
CREATE INDEX ix_remise_regle_school_id ON remise_regle (school_id);

CREATE TABLE conseil_classe_session (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_classe            UUID NOT NULL,
    id_trimestre         UUID,
    id_annee             UUID,
    date_session         DATE NOT NULL,
    statut               VARCHAR(30) NOT NULL DEFAULT 'planifie',
    pv_url               TEXT,
    notes                TEXT,
    anime_par            UUID,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_conseil_classe_session_school_id ON conseil_classe_session (school_id);
CREATE INDEX ix_conseil_classe_session_classe ON conseil_classe_session (school_id, id_classe);

CREATE TABLE decision_passage (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_eleve             UUID NOT NULL,
    id_annee             UUID NOT NULL,
    id_session           UUID REFERENCES conseil_classe_session(id) ON DELETE SET NULL,
    decision             VARCHAR(30) NOT NULL,
    mention              VARCHAR(40),
    commentaire          TEXT,
    valide_par           UUID,
    valide_le            TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_decision_passage_eleve_annee UNIQUE (school_id, id_eleve, id_annee)
);
CREATE INDEX ix_decision_passage_school_id ON decision_passage (school_id);
CREATE INDEX ix_decision_passage_id_eleve ON decision_passage (id_eleve);

CREATE TABLE absence_justificatif (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_absence           UUID NOT NULL,
    fichier_url          TEXT,
    motif                TEXT,
    valide               BOOLEAN NOT NULL DEFAULT false,
    valide_par           UUID,
    date_depot           TIMESTAMPTZ NOT NULL DEFAULT now(),
    valide_le            TIMESTAMPTZ
);
CREATE INDEX ix_absence_justificatif_school_id ON absence_justificatif (school_id);
CREATE INDEX ix_absence_justificatif_id_absence ON absence_justificatif (id_absence);

CREATE TABLE alerte_decrochage (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_eleve             UUID NOT NULL,
    type_alerte          VARCHAR(40) NOT NULL,
    niveau               VARCHAR(20) NOT NULL DEFAULT 'moyen',
    score                NUMERIC(8, 2),
    statut               VARCHAR(30) NOT NULL DEFAULT 'ouverte',
    details              JSONB,
    traite_par           UUID,
    traite_le            TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_alerte_decrochage_school_id ON alerte_decrochage (school_id);
CREATE INDEX ix_alerte_decrochage_eleve_statut ON alerte_decrochage (school_id, id_eleve, statut);

CREATE TABLE edt_publication (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_annee             UUID NOT NULL,
    libelle              VARCHAR(80),
    semaine              INTEGER,
    date_debut           DATE,
    date_fin             DATE,
    version              INTEGER NOT NULL DEFAULT 1,
    publie_le            TIMESTAMPTZ NOT NULL DEFAULT now(),
    publie_par           UUID,
    actif                BOOLEAN NOT NULL DEFAULT true
);
CREATE INDEX ix_edt_publication_school_id ON edt_publication (school_id);
CREATE INDEX ix_edt_publication_annee ON edt_publication (school_id, id_annee);

CREATE TABLE remplacement_enseignant (
    id                        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id                 UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_enseignant_absent      UUID NOT NULL,
    id_enseignant_remplacant  UUID,
    id_creneau                UUID,
    date_remplacement         DATE NOT NULL,
    motif                     TEXT,
    statut                    VARCHAR(30) NOT NULL DEFAULT 'planifie',
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_remplacement_enseignant_school_id ON remplacement_enseignant (school_id);
CREATE INDEX ix_remplacement_enseignant_date ON remplacement_enseignant (school_id, date_remplacement);

CREATE TABLE ecriture_comptable (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    date_ecriture        DATE NOT NULL,
    libelle              VARCHAR(200) NOT NULL,
    compte_debit         VARCHAR(16) NOT NULL,
    compte_credit        VARCHAR(16) NOT NULL,
    montant              NUMERIC(14, 2) NOT NULL,
    reference            VARCHAR(60),
    id_paiement          UUID,
    journal              VARCHAR(20),
    piece_url            TEXT,
    saisi_par            UUID,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_ecriture_comptable_school_id ON ecriture_comptable (school_id);
CREATE INDEX ix_ecriture_comptable_date ON ecriture_comptable (school_id, date_ecriture);

CREATE TABLE paie_periode (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    libelle              VARCHAR(80) NOT NULL,
    date_debut           DATE NOT NULL,
    date_fin             DATE NOT NULL,
    statut               VARCHAR(30) NOT NULL DEFAULT 'ouverte',
    cloture_le           TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_paie_periode_school_id ON paie_periode (school_id);

CREATE TABLE paie_ligne (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_periode           UUID NOT NULL REFERENCES paie_periode(id) ON DELETE CASCADE,
    id_utilisateur       UUID,
    id_enseignant        UUID,
    matricule            VARCHAR(40),
    brut                 NUMERIC(14, 2) NOT NULL DEFAULT 0,
    retenues             NUMERIC(14, 2) NOT NULL DEFAULT 0,
    net                  NUMERIC(14, 2) NOT NULL DEFAULT 0,
    details              JSONB,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_paie_ligne_school_id ON paie_ligne (school_id);
CREATE INDEX ix_paie_ligne_id_periode ON paie_ligne (id_periode);

CREATE TABLE cantine_abonnement (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_eleve             UUID NOT NULL,
    id_annee             UUID,
    formule              VARCHAR(40) NOT NULL DEFAULT 'standard',
    montant              NUMERIC(12, 2),
    date_debut           DATE NOT NULL,
    date_fin             DATE,
    actif                BOOLEAN NOT NULL DEFAULT true,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_cantine_abonnement_school_id ON cantine_abonnement (school_id);
CREATE INDEX ix_cantine_abonnement_id_eleve ON cantine_abonnement (id_eleve);

CREATE TABLE cantine_presence (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_eleve             UUID NOT NULL,
    date_presence        DATE NOT NULL,
    repas                VARCHAR(20) NOT NULL DEFAULT 'midi',
    present              BOOLEAN NOT NULL DEFAULT true,
    notes                TEXT,
    CONSTRAINT uq_cantine_presence_eleve_date_repas UNIQUE (school_id, id_eleve, date_presence, repas)
);
CREATE INDEX ix_cantine_presence_school_id ON cantine_presence (school_id);
CREATE INDEX ix_cantine_presence_date ON cantine_presence (school_id, date_presence);

CREATE TABLE transport_itineraire (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    libelle              VARCHAR(120) NOT NULL,
    description          TEXT,
    actif                BOOLEAN NOT NULL DEFAULT true,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_transport_itineraire_school_id ON transport_itineraire (school_id);

CREATE TABLE transport_arret (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_itineraire        UUID NOT NULL REFERENCES transport_itineraire(id) ON DELETE CASCADE,
    libelle              VARCHAR(120) NOT NULL,
    ordre                INTEGER NOT NULL DEFAULT 0,
    heure_passage        VARCHAR(10),
    latitude             NUMERIC(10, 7),
    longitude            NUMERIC(10, 7)
);
CREATE INDEX ix_transport_arret_school_id ON transport_arret (school_id);
CREATE INDEX ix_transport_arret_itineraire ON transport_arret (id_itineraire);

CREATE TABLE transport_eleve (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_eleve             UUID NOT NULL,
    id_itineraire        UUID NOT NULL REFERENCES transport_itineraire(id) ON DELETE CASCADE,
    id_arret             UUID REFERENCES transport_arret(id) ON DELETE SET NULL,
    id_annee             UUID,
    actif                BOOLEAN NOT NULL DEFAULT true,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_transport_eleve_school_id ON transport_eleve (school_id);
CREATE INDEX ix_transport_eleve_id_eleve ON transport_eleve (id_eleve);

CREATE TABLE internat_chambre (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    batiment             VARCHAR(60),
    numero               VARCHAR(30) NOT NULL,
    capacite             INTEGER NOT NULL DEFAULT 1,
    genre                VARCHAR(10),
    actif                BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT uq_internat_chambre_batiment_numero UNIQUE (school_id, batiment, numero)
);
CREATE INDEX ix_internat_chambre_school_id ON internat_chambre (school_id);

CREATE TABLE internat_affectation (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_chambre           UUID NOT NULL REFERENCES internat_chambre(id) ON DELETE CASCADE,
    id_eleve             UUID NOT NULL,
    id_annee             UUID,
    date_debut           DATE NOT NULL,
    date_fin             DATE,
    actif                BOOLEAN NOT NULL DEFAULT true,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_internat_affectation_school_id ON internat_affectation (school_id);
CREATE INDEX ix_internat_affectation_id_eleve ON internat_affectation (id_eleve);

CREATE TABLE infirmiere_soin (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_eleve             UUID NOT NULL,
    date_soin            TIMESTAMPTZ NOT NULL DEFAULT now(),
    motif                TEXT NOT NULL,
    traitement           TEXT,
    soigne_par           UUID,
    notes                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_infirmiere_soin_school_id ON infirmiere_soin (school_id);
CREATE INDEX ix_infirmiere_soin_id_eleve ON infirmiere_soin (id_eleve);

CREATE TABLE bibliotheque_livre (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    isbn                 VARCHAR(20),
    titre                VARCHAR(200) NOT NULL,
    auteur               VARCHAR(150),
    categorie            VARCHAR(60),
    exemplaires          INTEGER NOT NULL DEFAULT 1,
    disponibles          INTEGER NOT NULL DEFAULT 1,
    actif                BOOLEAN NOT NULL DEFAULT true,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_bibliotheque_livre_school_id ON bibliotheque_livre (school_id);
CREATE INDEX ix_bibliotheque_livre_titre ON bibliotheque_livre (school_id, titre);

CREATE TABLE bibliotheque_pret (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id               UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_livre                UUID NOT NULL REFERENCES bibliotheque_livre(id) ON DELETE CASCADE,
    id_eleve                UUID NOT NULL,
    date_pret               DATE NOT NULL,
    date_retour_prevue      DATE,
    date_retour_effective   DATE,
    statut                  VARCHAR(20) NOT NULL DEFAULT 'en_cours',
    notes                   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_bibliotheque_pret_school_id ON bibliotheque_pret (school_id);
CREATE INDEX ix_bibliotheque_pret_id_eleve ON bibliotheque_pret (id_eleve);
CREATE INDEX ix_bibliotheque_pret_id_livre ON bibliotheque_pret (id_livre);

CREATE TABLE rh_contrat (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_utilisateur       UUID,
    id_enseignant        UUID,
    type_contrat         VARCHAR(40) NOT NULL,
    date_debut           DATE NOT NULL,
    date_fin             DATE,
    salaire_base         NUMERIC(14, 2),
    statut               VARCHAR(30) NOT NULL DEFAULT 'actif',
    poste                VARCHAR(80),
    notes                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_rh_contrat_school_id ON rh_contrat (school_id);
CREATE INDEX ix_rh_contrat_id_utilisateur ON rh_contrat (id_utilisateur);

CREATE TABLE rh_conge (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_utilisateur       UUID NOT NULL,
    type_conge           VARCHAR(40) NOT NULL,
    date_debut           DATE NOT NULL,
    date_fin             DATE NOT NULL,
    statut               VARCHAR(30) NOT NULL DEFAULT 'demande',
    motif                TEXT,
    valide_par           UUID,
    valide_le            TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_rh_conge_school_id ON rh_conge (school_id);
CREATE INDEX ix_rh_conge_id_utilisateur ON rh_conge (id_utilisateur);

CREATE TABLE visiteur (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    nom                  VARCHAR(100) NOT NULL,
    prenom               VARCHAR(100),
    motif                TEXT,
    piece_identite       VARCHAR(60),
    telephone            VARCHAR(30),
    heure_entree         TIMESTAMPTZ NOT NULL DEFAULT now(),
    heure_sortie         TIMESTAMPTZ,
    accueilli_par        UUID,
    id_eleve_visite      UUID
);
CREATE INDEX ix_visiteur_school_id ON visiteur (school_id);
CREATE INDEX ix_visiteur_heure_entree ON visiteur (school_id, heure_entree);

CREATE TABLE sortie_eleve (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_eleve             UUID NOT NULL,
    date_sortie          TIMESTAMPTZ NOT NULL DEFAULT now(),
    motif                TEXT,
    autorise_par         UUID,
    recupere_par         VARCHAR(150),
    heure_retour         TIMESTAMPTZ,
    statut               VARCHAR(20) NOT NULL DEFAULT 'sorti'
);
CREATE INDEX ix_sortie_eleve_school_id ON sortie_eleve (school_id);
CREATE INDEX ix_sortie_eleve_id_eleve ON sortie_eleve (id_eleve);

CREATE TABLE inventaire_article (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    code                 VARCHAR(40) NOT NULL,
    libelle              VARCHAR(150) NOT NULL,
    categorie            VARCHAR(60),
    quantite             INTEGER NOT NULL DEFAULT 0,
    seuil_alerte         INTEGER NOT NULL DEFAULT 0,
    unite                VARCHAR(20),
    actif                BOOLEAN NOT NULL DEFAULT true,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_inventaire_article_school_code UNIQUE (school_id, code)
);
CREATE INDEX ix_inventaire_article_school_id ON inventaire_article (school_id);

CREATE TABLE inventaire_mouvement (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_article           UUID NOT NULL REFERENCES inventaire_article(id) ON DELETE CASCADE,
    type_mouvement       VARCHAR(20) NOT NULL,
    quantite             INTEGER NOT NULL,
    motif                TEXT,
    date_mouvement       TIMESTAMPTZ NOT NULL DEFAULT now(),
    effectue_par         UUID
);
CREATE INDEX ix_inventaire_mouvement_school_id ON inventaire_mouvement (school_id);
CREATE INDEX ix_inventaire_mouvement_id_article ON inventaire_mouvement (id_article);

CREATE TABLE elearning_devoir (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_classe            UUID,
    id_matiere           UUID,
    titre                VARCHAR(200) NOT NULL,
    consignes            TEXT,
    date_limite          TIMESTAMPTZ,
    cree_par             UUID,
    publie               BOOLEAN NOT NULL DEFAULT true,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_elearning_devoir_school_id ON elearning_devoir (school_id);
CREATE INDEX ix_elearning_devoir_id_classe ON elearning_devoir (id_classe);

CREATE TABLE elearning_remise (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_devoir            UUID NOT NULL REFERENCES elearning_devoir(id) ON DELETE CASCADE,
    id_eleve             UUID NOT NULL,
    fichier_url          TEXT,
    contenu              TEXT,
    date_remise          TIMESTAMPTZ NOT NULL DEFAULT now(),
    note                 NUMERIC(6, 2),
    commentaire          TEXT,
    CONSTRAINT uq_elearning_remise_devoir_eleve UNIQUE (id_devoir, id_eleve)
);
CREATE INDEX ix_elearning_remise_school_id ON elearning_remise (school_id);
CREATE INDEX ix_elearning_remise_id_devoir ON elearning_remise (id_devoir);
CREATE INDEX ix_elearning_remise_id_eleve ON elearning_remise (id_eleve);

CREATE TABLE elearning_quiz (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    id_classe            UUID,
    id_matiere           UUID,
    titre                VARCHAR(200) NOT NULL,
    questions            JSONB,
    duree_minutes        INTEGER,
    publie               BOOLEAN NOT NULL DEFAULT false,
    cree_par             UUID,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_elearning_quiz_school_id ON elearning_quiz (school_id);

CREATE TABLE otp_challenge (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id            UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    canal                VARCHAR(20) NOT NULL,
    destinataire         VARCHAR(150) NOT NULL,
    code_hash            VARCHAR(128) NOT NULL,
    purpose              VARCHAR(40) NOT NULL DEFAULT 'login',
    attempts             INTEGER NOT NULL DEFAULT 0,
    max_attempts         INTEGER NOT NULL DEFAULT 5,
    expires_at           TIMESTAMPTZ NOT NULL,
    consumed_at          TIMESTAMPTZ,
    id_utilisateur       UUID,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_otp_challenge_school_id ON otp_challenge (school_id);
CREATE INDEX ix_otp_challenge_destinataire ON otp_challenge (school_id, destinataire, purpose);
CREATE INDEX ix_otp_challenge_expires_at ON otp_challenge (expires_at);
