"""Programme pédagogique : programme_devoir + statuts évaluation."""
revision = "add_programme_pedagogique"
down_revision = "add_cycle_niveau"
branch_labels = None
depends_on = None


def upgrade():
    from alembic import op
    import sqlalchemy as sa
    from sqlalchemy.dialects.postgresql import UUID

    op.create_table(
        "programme_devoir",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("id_classe", UUID(as_uuid=True), sa.ForeignKey("classe.id", ondelete="CASCADE"), nullable=False),
        sa.Column("id_matiere", UUID(as_uuid=True), sa.ForeignKey("matiere.id", ondelete="CASCADE"), nullable=False),
        sa.Column("jour_semaine", sa.SmallInteger(), nullable=False),
        sa.Column("frequence", sa.String(length=20), server_default="hebdomadaire", nullable=False),
        sa.Column("note", sa.String(length=255)),
        sa.Column("id_annee", UUID(as_uuid=True), sa.ForeignKey("annee_scolaire.id", ondelete="CASCADE"), nullable=False),
        sa.CheckConstraint("jour_semaine BETWEEN 1 AND 7", name="ck_programme_devoir_jour"),
        sa.CheckConstraint(
            "frequence IN ('hebdomadaire', 'quinzomadaire')",
            name="ck_programme_devoir_frequence",
        ),
        sa.UniqueConstraint(
            "id_classe", "id_matiere", "jour_semaine", "id_annee",
            name="uq_programme_devoir_classe_matiere_jour_annee",
        ),
    )

    op.add_column(
        "evaluation",
        sa.Column("statut_publication", sa.String(length=20), server_default="brouillon", nullable=False),
    )
    op.add_column(
        "evaluation",
        sa.Column("statut_saisie", sa.String(length=20), server_default="en_cours", nullable=False),
    )
    op.create_check_constraint(
        "ck_evaluation_statut_publication",
        "evaluation",
        "statut_publication IN ('brouillon', 'publie')",
    )
    op.create_check_constraint(
        "ck_evaluation_statut_saisie",
        "evaluation",
        "statut_saisie IN ('en_cours', 'cloturee')",
    )
    op.execute(
        """
        UPDATE evaluation SET statut_publication = 'publie'
        WHERE type_evaluation != 'examen';
        UPDATE evaluation SET statut_saisie = 'cloturee'
        WHERE id IN (SELECT DISTINCT id_evaluation FROM note);
        """
    )


def downgrade():
    from alembic import op

    op.drop_constraint("ck_evaluation_statut_saisie", "evaluation", type_="check")
    op.drop_constraint("ck_evaluation_statut_publication", "evaluation", type_="check")
    op.drop_column("evaluation", "statut_saisie")
    op.drop_column("evaluation", "statut_publication")
    op.drop_table("programme_devoir")
