-- ============================================================================
-- PROGICIEL INTÉGRÉ DE GESTION SCOLAIRE
-- Schéma de base de données PostgreSQL 15+
-- Architecture MONO-ÉTABLISSEMENT
-- (pour un nouvel établissement client : cloner le repo + réinitialiser cette base)
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. CONFIGURATION DE L'ÉTABLISSEMENT (table à une seule ligne)
-- ============================================================================

CREATE TABLE etablissement (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    created_at           TIMESTAMPTZ DEFAULT now(),
    updated_at           TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT une_seule_ligne CHECK (true) -- appliqué au niveau applicatif : jamais plus d'une ligne
);

CREATE TABLE annee_scolaire (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    libelle              VARCHAR(20) NOT NULL UNIQUE,   -- ex: 2025-2026
    date_debut           DATE NOT NULL,
    date_fin             DATE NOT NULL,
    est_active           BOOLEAN DEFAULT false
);

CREATE TABLE trimestre (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_annee             UUID NOT NULL REFERENCES annee_scolaire(id) ON DELETE CASCADE,
    numero               SMALLINT NOT NULL CHECK (numero IN (1, 2, 3)),
    date_debut           DATE NOT NULL,
    date_fin             DATE NOT NULL,
    UNIQUE (id_annee, numero)
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
                            ('administrateur', 'directeur', 'enseignant', 'agent_comptable', 'secretariat', 'parent')),
    actif                BOOLEAN DEFAULT true,
    doit_changer_mdp     BOOLEAN DEFAULT true,        -- forcer changement au 1er login
    derniere_connexion   TIMESTAMPTZ,
    tentatives_echouees  SMALLINT DEFAULT 0,          -- verrouillage après N échecs
    verrouille_jusqu_a   TIMESTAMPTZ,
    created_at           TIMESTAMPTZ DEFAULT now()
);

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
    matricule                 VARCHAR(30) NOT NULL UNIQUE,
    nom                       VARCHAR(100) NOT NULL,
    prenom                    VARCHAR(100) NOT NULL,
    sexe                      CHAR(1) CHECK (sexe IN ('M', 'F')),
    date_naissance            DATE,
    lieu_naissance            VARCHAR(100),
    adresse                   TEXT,
    photo_url                 TEXT,
    notes_medicales_chiffrees BYTEA,          -- chiffré via pgcrypto (pgp_sym_encrypt), jamais en clair
    pieces_justificatives     JSONB,          -- [{type, url, date_upload}]
    created_at                TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE eleve_parent (
    id_eleve             UUID NOT NULL REFERENCES eleve(id) ON DELETE CASCADE,
    id_parent            UUID NOT NULL REFERENCES parent_tuteur(id) ON DELETE CASCADE,
    tuteur_legal         BOOLEAN DEFAULT false,
    PRIMARY KEY (id_eleve, id_parent)
);

CREATE TABLE niveau_etude (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    libelle              VARCHAR(50) NOT NULL UNIQUE,   -- ex: 6ème, Terminale
    ordre                SMALLINT,
    cycle                VARCHAR(20) NOT NULL DEFAULT 'premier'
        CHECK (cycle IN ('premier', 'second'))
);

CREATE TABLE classe (
    id                        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_niveau                 UUID NOT NULL REFERENCES niveau_etude(id) ON DELETE RESTRICT,
    id_annee                  UUID NOT NULL REFERENCES annee_scolaire(id) ON DELETE CASCADE,
    libelle                   VARCHAR(50) NOT NULL,        -- ex: 6ème A
    id_professeur_principal   UUID,                        -- FK ajoutée après création de enseignant
    capacite_max              INTEGER DEFAULT 50,
    UNIQUE (id_annee, libelle)
);

CREATE TABLE inscription (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_eleve             UUID NOT NULL REFERENCES eleve(id) ON DELETE CASCADE,
    id_classe            UUID NOT NULL REFERENCES classe(id) ON DELETE RESTRICT,
    id_annee             UUID NOT NULL REFERENCES annee_scolaire(id) ON DELETE CASCADE,
    statut               VARCHAR(20) NOT NULL DEFAULT 'inscrit'
                            CHECK (statut IN ('inscrit', 'abandon', 'suspendu', 'reinscrit', 'diplome')),
    est_boursier         BOOLEAN DEFAULT false,
    taux_reduction       NUMERIC(5,2) DEFAULT 0,
    date_inscription     DATE DEFAULT CURRENT_DATE,
    date_statut_maj      DATE,
    UNIQUE (id_eleve, id_annee)
);

-- ============================================================================
-- 4. PERSONNEL ENSEIGNANT & AFFECTATIONS
-- ============================================================================

CREATE TABLE enseignant (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_utilisateur       UUID REFERENCES utilisateur(id) ON DELETE SET NULL,
    nom                  VARCHAR(100) NOT NULL,
    prenom               VARCHAR(100) NOT NULL,
    specialite           VARCHAR(100),
    type_contrat         VARCHAR(30),
    taux_horaire         NUMERIC(10,2),
    telephone            VARCHAR(30),
    email                VARCHAR(150)
);

ALTER TABLE classe
    ADD CONSTRAINT fk_classe_prof_principal
    FOREIGN KEY (id_professeur_principal) REFERENCES enseignant(id) ON DELETE SET NULL;

CREATE TABLE matiere (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    libelle              VARCHAR(80) NOT NULL,
    code                 VARCHAR(20)
);

CREATE TABLE coefficient_matiere (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_matiere           UUID NOT NULL REFERENCES matiere(id) ON DELETE CASCADE,
    id_niveau            UUID NOT NULL REFERENCES niveau_etude(id) ON DELETE CASCADE,
    coefficient          NUMERIC(4,2) NOT NULL,
    UNIQUE (id_matiere, id_niveau)
);

CREATE TABLE affectation_enseignant (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_enseignant          UUID NOT NULL REFERENCES enseignant(id) ON DELETE CASCADE,
    id_classe              UUID NOT NULL REFERENCES classe(id) ON DELETE CASCADE,
    id_matiere             UUID NOT NULL REFERENCES matiere(id) ON DELETE CASCADE,
    id_annee               UUID NOT NULL REFERENCES annee_scolaire(id) ON DELETE CASCADE,
    volume_horaire_hebdo   NUMERIC(5,2),
    UNIQUE (id_enseignant, id_classe, id_matiere, id_annee)
);

-- ============================================================================
-- 5. EMPLOI DU TEMPS
-- ============================================================================

CREATE TABLE salle (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    libelle              VARCHAR(50) NOT NULL,
    capacite             INTEGER
);

CREATE EXTENSION IF NOT EXISTS btree_gist;

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
    id_classe            UUID NOT NULL REFERENCES classe(id) ON DELETE CASCADE,
    id_matiere           UUID NOT NULL REFERENCES matiere(id) ON DELETE CASCADE,
    id_trimestre         UUID NOT NULL REFERENCES trimestre(id) ON DELETE CASCADE,
    id_enseignant        UUID NOT NULL REFERENCES enseignant(id) ON DELETE RESTRICT,
    type_evaluation      VARCHAR(20) NOT NULL CHECK (type_evaluation IN ('devoir', 'examen', 'interrogation')),
    coefficient          NUMERIC(4,2) NOT NULL DEFAULT 1,
    date_evaluation      DATE NOT NULL,
    libelle              VARCHAR(150),
    statut_publication   VARCHAR(20) NOT NULL DEFAULT 'brouillon'
        CHECK (statut_publication IN ('brouillon', 'publie')),
    statut_saisie        VARCHAR(20) NOT NULL DEFAULT 'en_cours'
        CHECK (statut_saisie IN ('en_cours', 'cloturee'))
);

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
    id_evaluation        UUID NOT NULL REFERENCES evaluation(id) ON DELETE CASCADE,
    id_eleve             UUID NOT NULL REFERENCES eleve(id) ON DELETE CASCADE,
    valeur_note          NUMERIC(4,2) CHECK (valeur_note BETWEEN 0 AND 20),
    absent               BOOLEAN DEFAULT false,     -- distinct d'une note à 0/20
    appreciation         VARCHAR(255),
    saisi_par            UUID REFERENCES utilisateur(id),
    modifie_par          UUID REFERENCES utilisateur(id),
    saisi_le             TIMESTAMPTZ DEFAULT now(),
    modifie_le           TIMESTAMPTZ,
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

CREATE TABLE bulletin (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_eleve               UUID NOT NULL REFERENCES eleve(id) ON DELETE CASCADE,
    id_trimestre           UUID NOT NULL REFERENCES trimestre(id) ON DELETE CASCADE,
    moyenne_generale       NUMERIC(4,2),
    rang                   INTEGER,
    effectif_classe        INTEGER,
    moyenne_classe         NUMERIC(4,2),
    mention                VARCHAR(50),
    appreciation_generale  TEXT,
    statut                 VARCHAR(20) DEFAULT 'brouillon' CHECK (statut IN ('brouillon', 'valide', 'publie')),
    valide_par             UUID REFERENCES utilisateur(id),
    date_generation        TIMESTAMPTZ DEFAULT now(),
    pdf_url                TEXT,
    UNIQUE (id_eleve, id_trimestre)
);

-- ============================================================================
-- 7. MODULE 3 : FINANCE & COMPTABILITÉ
-- ============================================================================

CREATE TABLE frais_scolaire (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_niveau            UUID NOT NULL REFERENCES niveau_etude(id) ON DELETE CASCADE,
    id_annee             UUID NOT NULL REFERENCES annee_scolaire(id) ON DELETE CASCADE,
    motif                VARCHAR(50) NOT NULL,   -- Scolarité, Cantine, Transport, Inscription
    montant_total        NUMERIC(12,2) NOT NULL
);

CREATE TABLE echeance_paiement (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_frais             UUID NOT NULL REFERENCES frais_scolaire(id) ON DELETE CASCADE,
    libelle              VARCHAR(50),
    montant              NUMERIC(12,2) NOT NULL,
    date_echeance        DATE NOT NULL
);

CREATE SEQUENCE seq_numero_recu START 1;

CREATE TABLE paiement (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_eleve             UUID NOT NULL REFERENCES eleve(id) ON DELETE CASCADE,
    id_annee             UUID NOT NULL REFERENCES annee_scolaire(id) ON DELETE CASCADE,
    id_echeance          UUID REFERENCES echeance_paiement(id) ON DELETE SET NULL,
    motif                VARCHAR(50) NOT NULL,
    montant_verse        NUMERIC(12,2) NOT NULL CHECK (montant_verse > 0),
    mode_paiement        VARCHAR(30),            -- Espèces, Mobile Money, Virement
    numero_recu          VARCHAR(30) NOT NULL UNIQUE DEFAULT ('REC-' || nextval('seq_numero_recu')),
    encaisse_par         UUID REFERENCES utilisateur(id),
    annule               BOOLEAN DEFAULT false,  -- annulation traçable, jamais de DELETE sur un paiement
    motif_annulation     TEXT,
    date_paiement        TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- 8. MODULE 5 : ABSENCES, RETARDS & DISCIPLINE
-- ============================================================================

CREATE TABLE absence (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_eleve             UUID NOT NULL REFERENCES eleve(id) ON DELETE CASCADE,
    id_creneau           UUID REFERENCES creneau_emploi_temps(id) ON DELETE SET NULL,  -- NULL = journée entière
    date_absence         DATE NOT NULL,
    type_absence         VARCHAR(20) CHECK (type_absence IN ('absence', 'retard')),
    justifiee            BOOLEAN DEFAULT false,
    motif                TEXT,
    signale_par          UUID REFERENCES utilisateur(id),
    created_at           TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE incident_disciplinaire (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_eleve             UUID NOT NULL REFERENCES eleve(id) ON DELETE CASCADE,
    id_trimestre         UUID REFERENCES trimestre(id) ON DELETE SET NULL,
    type_incident        VARCHAR(30) CHECK (type_incident IN ('avertissement', 'blame', 'exclusion_temporaire')),
    description          TEXT,
    date_incident         DATE NOT NULL,
    declare_par           UUID REFERENCES utilisateur(id)
);

-- ============================================================================
-- 9. MODULE 6 : DOCUMENTS ADMINISTRATIFS
-- ============================================================================

CREATE TABLE document_administratif (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_eleve             UUID NOT NULL REFERENCES eleve(id) ON DELETE CASCADE,
    type_document        VARCHAR(30) CHECK (type_document IN
                            ('carte_scolaire', 'attestation_scolarite', 'certificat', 'diplome')),
    qr_code_data         TEXT,
    date_emission        DATE DEFAULT CURRENT_DATE,
    date_expiration      DATE,
    pdf_url              TEXT,
    genere_par           UUID REFERENCES utilisateur(id)
);

-- ============================================================================
-- 10. MODULE 7 : COMMUNICATION & NOTIFICATIONS
-- ============================================================================

CREATE TABLE notification (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_eleve             UUID REFERENCES eleve(id) ON DELETE CASCADE,
    id_parent            UUID REFERENCES parent_tuteur(id) ON DELETE CASCADE,
    canal                VARCHAR(10) CHECK (canal IN ('sms', 'email')),
    type_notification    VARCHAR(30),   -- absence, bulletin, paiement, relance
    contenu              TEXT,
    statut               VARCHAR(20) DEFAULT 'en_attente' CHECK (statut IN ('en_attente', 'envoye', 'echec')),
    tentative_count       SMALLINT DEFAULT 0,
    envoye_le            TIMESTAMPTZ,
    created_at            TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- 11. AUDIT — traçabilité obligatoire sur les actions sensibles
-- ============================================================================

CREATE TABLE journal_audit (
    id                       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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

CREATE INDEX idx_inscription_classe ON inscription(id_classe);
CREATE INDEX idx_note_eleve ON note(id_eleve);
CREATE INDEX idx_paiement_eleve_annee ON paiement(id_eleve, id_annee);
CREATE INDEX idx_absence_eleve_date ON absence(id_eleve, date_absence);
CREATE INDEX idx_evaluation_classe_trimestre ON evaluation(id_classe, id_trimestre);
CREATE INDEX idx_journal_audit_utilisateur ON journal_audit(id_utilisateur, created_at);
CREATE INDEX idx_eleve_nom_prenom ON eleve(nom, prenom);

-- ============================================================================
-- FONCTIONS UTILITAIRES
-- ============================================================================

-- Empêche plus d'une ligne dans "etablissement" (mono-établissement strict)
CREATE OR REPLACE FUNCTION empecher_multi_etablissement()
RETURNS TRIGGER AS $$
BEGIN
    IF (SELECT COUNT(*) FROM etablissement) >= 1 THEN
        RAISE EXCEPTION 'Ce système est mono-établissement : une seule ligne autorisée dans "etablissement".';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_une_seule_ligne_etablissement
    BEFORE INSERT ON etablissement
    FOR EACH ROW EXECUTE FUNCTION empecher_multi_etablissement();
