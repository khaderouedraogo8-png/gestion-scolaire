"""PR #9 step 3/5 — FK school_id RESTRICT, indexes, UNIQUE(id,school_id), FKs composites."""
revision = "tenant_fks_indexes"
down_revision = "tenant_backfill"
branch_labels = None
depends_on = None

DIRECT_FK_TABLES = (
    "etablissement",
    "annee_scolaire",
    "niveau_etude",
    "eleve",
    "parent_tuteur",
    "enseignant",
    "matiere",
    "salle",
    "frais_scolaire",
    "classe",
    "evaluation",
    "paiement",
    "absence",
    "incident_disciplinaire",
    "document_administratif",
    "notification",
    "journal_audit",
    "bulletin",
    "inscription",
    "note",
    "affectation_enseignant",
)

# Parents exposant UNIQUE(id, school_id) pour FKs composites
COMPOSITE_PARENTS = (
    "eleve",
    "classe",
    "annee_scolaire",
    "niveau_etude",
    "evaluation",
    "matiere",
    "enseignant",
)


def upgrade():
    from alembic import op
    import sqlalchemy as sa

    # --- 1:1 établissement ↔ school : lever le trigger mono-ligne global ---
    op.execute("DROP TRIGGER IF EXISTS trg_une_seule_ligne_etablissement ON etablissement")
    op.execute("DROP FUNCTION IF EXISTS empecher_multi_etablissement()")

    # utilisateur.school_id : SET NULL → RESTRICT (colonne bientôt NOT NULL)
    op.drop_constraint("fk_utilisateur_school_id", "utilisateur", type_="foreignkey")
    op.create_foreign_key(
        "fk_utilisateur_school_id",
        "utilisateur",
        "schools",
        ["school_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # FK school_id → schools (RESTRICT) + index
    for table in DIRECT_FK_TABLES:
        op.create_foreign_key(
            f"fk_{table}_school_id",
            table,
            "schools",
            ["school_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(f"ix_{table}_school_id", table, ["school_id"], unique=False)

    # 1 établissement par école
    op.create_index("uq_etablissement_school_id", "etablissement", ["school_id"], unique=True)

    # UNIQUE(id, school_id) pour FKs composites
    for table in COMPOSITE_PARENTS:
        op.create_unique_constraint(f"uq_{table}_id_school", table, ["id", "school_id"])

    # --- Remplacer FKs simples par FKs composites (même école) ---

    # classe → niveau + annee
    op.drop_constraint("classe_id_niveau_fkey", "classe", type_="foreignkey")
    op.drop_constraint("classe_id_annee_fkey", "classe", type_="foreignkey")
    op.create_foreign_key(
        "fk_classe_niveau_school",
        "classe",
        "niveau_etude",
        ["id_niveau", "school_id"],
        ["id", "school_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_classe_annee_school",
        "classe",
        "annee_scolaire",
        ["id_annee", "school_id"],
        ["id", "school_id"],
        ondelete="CASCADE",
    )

    # inscription → eleve + classe + annee
    op.drop_constraint("inscription_id_eleve_fkey", "inscription", type_="foreignkey")
    op.drop_constraint("inscription_id_classe_fkey", "inscription", type_="foreignkey")
    op.drop_constraint("inscription_id_annee_fkey", "inscription", type_="foreignkey")
    op.create_foreign_key(
        "fk_inscription_eleve_school",
        "inscription",
        "eleve",
        ["id_eleve", "school_id"],
        ["id", "school_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_inscription_classe_school",
        "inscription",
        "classe",
        ["id_classe", "school_id"],
        ["id", "school_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_inscription_annee_school",
        "inscription",
        "annee_scolaire",
        ["id_annee", "school_id"],
        ["id", "school_id"],
        ondelete="CASCADE",
    )

    # evaluation → classe + matiere + enseignant (trimestre reste parent-only)
    op.drop_constraint("evaluation_id_classe_fkey", "evaluation", type_="foreignkey")
    op.drop_constraint("evaluation_id_matiere_fkey", "evaluation", type_="foreignkey")
    op.drop_constraint("evaluation_id_enseignant_fkey", "evaluation", type_="foreignkey")
    op.create_foreign_key(
        "fk_evaluation_classe_school",
        "evaluation",
        "classe",
        ["id_classe", "school_id"],
        ["id", "school_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_evaluation_matiere_school",
        "evaluation",
        "matiere",
        ["id_matiere", "school_id"],
        ["id", "school_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_evaluation_enseignant_school",
        "evaluation",
        "enseignant",
        ["id_enseignant", "school_id"],
        ["id", "school_id"],
        ondelete="RESTRICT",
    )

    # note → evaluation + eleve
    op.drop_constraint("note_id_evaluation_fkey", "note", type_="foreignkey")
    op.drop_constraint("note_id_eleve_fkey", "note", type_="foreignkey")
    op.create_foreign_key(
        "fk_note_evaluation_school",
        "note",
        "evaluation",
        ["id_evaluation", "school_id"],
        ["id", "school_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_note_eleve_school",
        "note",
        "eleve",
        ["id_eleve", "school_id"],
        ["id", "school_id"],
        ondelete="CASCADE",
    )

    # affectation → enseignant + classe + matiere + annee
    op.drop_constraint("affectation_enseignant_id_enseignant_fkey", "affectation_enseignant", type_="foreignkey")
    op.drop_constraint("affectation_enseignant_id_classe_fkey", "affectation_enseignant", type_="foreignkey")
    op.drop_constraint("affectation_enseignant_id_matiere_fkey", "affectation_enseignant", type_="foreignkey")
    op.drop_constraint("affectation_enseignant_id_annee_fkey", "affectation_enseignant", type_="foreignkey")
    op.create_foreign_key(
        "fk_affectation_enseignant_school",
        "affectation_enseignant",
        "enseignant",
        ["id_enseignant", "school_id"],
        ["id", "school_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_affectation_classe_school",
        "affectation_enseignant",
        "classe",
        ["id_classe", "school_id"],
        ["id", "school_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_affectation_matiere_school",
        "affectation_enseignant",
        "matiere",
        ["id_matiere", "school_id"],
        ["id", "school_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_affectation_annee_school",
        "affectation_enseignant",
        "annee_scolaire",
        ["id_annee", "school_id"],
        ["id", "school_id"],
        ondelete="CASCADE",
    )

    # paiement → eleve + annee (FKs existantes nommées)
    op.drop_constraint("paiement_id_eleve_fkey", "paiement", type_="foreignkey")
    op.drop_constraint("paiement_id_annee_fkey", "paiement", type_="foreignkey")
    op.create_foreign_key(
        "fk_paiement_eleve_school",
        "paiement",
        "eleve",
        ["id_eleve", "school_id"],
        ["id", "school_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_paiement_annee_school",
        "paiement",
        "annee_scolaire",
        ["id_annee", "school_id"],
        ["id", "school_id"],
        ondelete="CASCADE",
    )

    # absence / incident / document / bulletin → eleve
    for table, old_fk in (
        ("absence", "absence_id_eleve_fkey"),
        ("incident_disciplinaire", "incident_disciplinaire_id_eleve_fkey"),
        ("document_administratif", "document_administratif_id_eleve_fkey"),
        ("bulletin", "bulletin_id_eleve_fkey"),
    ):
        op.drop_constraint(old_fk, table, type_="foreignkey")
        op.create_foreign_key(
            f"fk_{table}_eleve_school",
            table,
            "eleve",
            ["id_eleve", "school_id"],
            ["id", "school_id"],
            ondelete="CASCADE",
        )

    # notification.id_eleve nullable — FK composite MATCH SIMPLE
    op.drop_constraint("notification_id_eleve_fkey", "notification", type_="foreignkey")
    op.create_foreign_key(
        "fk_notification_eleve_school",
        "notification",
        "eleve",
        ["id_eleve", "school_id"],
        ["id", "school_id"],
        ondelete="CASCADE",
    )

    # frais_scolaire → niveau + annee (pas de FK nommées standard — vérifier)
    # Les colonnes existent sans FK ORM ; ajouter FKs composites si absentes
    insp = sa.inspect(op.get_bind())
    frais_fks = {fk["name"] for fk in insp.get_foreign_keys("frais_scolaire")}
    if "frais_scolaire_id_niveau_fkey" in frais_fks:
        op.drop_constraint("frais_scolaire_id_niveau_fkey", "frais_scolaire", type_="foreignkey")
    if "frais_scolaire_id_annee_fkey" in frais_fks:
        op.drop_constraint("frais_scolaire_id_annee_fkey", "frais_scolaire", type_="foreignkey")
    op.create_foreign_key(
        "fk_frais_niveau_school",
        "frais_scolaire",
        "niveau_etude",
        ["id_niveau", "school_id"],
        ["id", "school_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_frais_annee_school",
        "frais_scolaire",
        "annee_scolaire",
        ["id_annee", "school_id"],
        ["id", "school_id"],
        ondelete="CASCADE",
    )


def downgrade():
    from alembic import op
    import sqlalchemy as sa

    # Reverse utilisateur FK to SET NULL
    op.drop_constraint("fk_utilisateur_school_id", "utilisateur", type_="foreignkey")
    op.create_foreign_key(
        "fk_utilisateur_school_id",
        "utilisateur",
        "schools",
        ["school_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Reverse composite FKs → simple FKs (best-effort)
    op.drop_constraint("fk_frais_annee_school", "frais_scolaire", type_="foreignkey")
    op.drop_constraint("fk_frais_niveau_school", "frais_scolaire", type_="foreignkey")

    op.drop_constraint("fk_notification_eleve_school", "notification", type_="foreignkey")
    op.create_foreign_key(
        "notification_id_eleve_fkey",
        "notification",
        "eleve",
        ["id_eleve"],
        ["id"],
        ondelete="CASCADE",
    )

    for table in ("bulletin", "document_administratif", "incident_disciplinaire", "absence"):
        op.drop_constraint(f"fk_{table}_eleve_school", table, type_="foreignkey")
        op.create_foreign_key(
            f"{table}_id_eleve_fkey",
            table,
            "eleve",
            ["id_eleve"],
            ["id"],
            ondelete="CASCADE",
        )

    op.drop_constraint("fk_paiement_annee_school", "paiement", type_="foreignkey")
    op.drop_constraint("fk_paiement_eleve_school", "paiement", type_="foreignkey")
    op.create_foreign_key(
        "paiement_id_eleve_fkey", "paiement", "eleve", ["id_eleve"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "paiement_id_annee_fkey",
        "paiement",
        "annee_scolaire",
        ["id_annee"],
        ["id"],
        ondelete="CASCADE",
    )

    for name in (
        "fk_affectation_annee_school",
        "fk_affectation_matiere_school",
        "fk_affectation_classe_school",
        "fk_affectation_enseignant_school",
    ):
        op.drop_constraint(name, "affectation_enseignant", type_="foreignkey")
    op.create_foreign_key(
        "affectation_enseignant_id_enseignant_fkey",
        "affectation_enseignant",
        "enseignant",
        ["id_enseignant"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "affectation_enseignant_id_classe_fkey",
        "affectation_enseignant",
        "classe",
        ["id_classe"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "affectation_enseignant_id_matiere_fkey",
        "affectation_enseignant",
        "matiere",
        ["id_matiere"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "affectation_enseignant_id_annee_fkey",
        "affectation_enseignant",
        "annee_scolaire",
        ["id_annee"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("fk_note_eleve_school", "note", type_="foreignkey")
    op.drop_constraint("fk_note_evaluation_school", "note", type_="foreignkey")
    op.create_foreign_key(
        "note_id_evaluation_fkey", "note", "evaluation", ["id_evaluation"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "note_id_eleve_fkey", "note", "eleve", ["id_eleve"], ["id"], ondelete="CASCADE"
    )

    for name in (
        "fk_evaluation_enseignant_school",
        "fk_evaluation_matiere_school",
        "fk_evaluation_classe_school",
    ):
        op.drop_constraint(name, "evaluation", type_="foreignkey")
    op.create_foreign_key(
        "evaluation_id_classe_fkey", "evaluation", "classe", ["id_classe"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "evaluation_id_matiere_fkey", "evaluation", "matiere", ["id_matiere"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "evaluation_id_enseignant_fkey",
        "evaluation",
        "enseignant",
        ["id_enseignant"],
        ["id"],
        ondelete="RESTRICT",
    )

    for name in (
        "fk_inscription_annee_school",
        "fk_inscription_classe_school",
        "fk_inscription_eleve_school",
    ):
        op.drop_constraint(name, "inscription", type_="foreignkey")
    op.create_foreign_key(
        "inscription_id_eleve_fkey", "inscription", "eleve", ["id_eleve"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "inscription_id_classe_fkey", "inscription", "classe", ["id_classe"], ["id"], ondelete="RESTRICT"
    )
    op.create_foreign_key(
        "inscription_id_annee_fkey",
        "inscription",
        "annee_scolaire",
        ["id_annee"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("fk_classe_annee_school", "classe", type_="foreignkey")
    op.drop_constraint("fk_classe_niveau_school", "classe", type_="foreignkey")
    op.create_foreign_key(
        "classe_id_niveau_fkey", "classe", "niveau_etude", ["id_niveau"], ["id"], ondelete="RESTRICT"
    )
    op.create_foreign_key(
        "classe_id_annee_fkey", "classe", "annee_scolaire", ["id_annee"], ["id"], ondelete="CASCADE"
    )

    for table in COMPOSITE_PARENTS:
        op.drop_constraint(f"uq_{table}_id_school", table, type_="unique")

    op.drop_index("uq_etablissement_school_id", table_name="etablissement")

    for table in DIRECT_FK_TABLES:
        op.drop_index(f"ix_{table}_school_id", table_name=table)
        op.drop_constraint(f"fk_{table}_school_id", table, type_="foreignkey")

    # Restaurer trigger mono-établissement (best-effort)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION empecher_multi_etablissement()
        RETURNS trigger AS $$
        BEGIN
            IF (SELECT COUNT(*) FROM etablissement) >= 1 THEN
                RAISE EXCEPTION 'Ce système est mono-établissement : une seule ligne autorisée dans "etablissement".';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_une_seule_ligne_etablissement
            BEFORE INSERT ON etablissement
            FOR EACH ROW EXECUTE FUNCTION empecher_multi_etablissement();
        """
    )
