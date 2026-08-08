"""Extensions pédagogiques §8 : calendrier scolaire et cahier de texte."""
revision = "add_pedagogie_extensions"
down_revision = "add_programme_pedagogique"
branch_labels = None
depends_on = None


def upgrade():
    from alembic import op
    import sqlalchemy as sa
    from sqlalchemy.dialects.postgresql import UUID

    op.create_table(
        "evenement_calendrier",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("id_annee", UUID(as_uuid=True), sa.ForeignKey("annee_scolaire.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type_evenement", sa.String(length=30), nullable=False),
        sa.Column("libelle", sa.String(length=150), nullable=False),
        sa.Column("date_debut", sa.Date(), nullable=False),
        sa.Column("date_fin", sa.Date(), nullable=False),
        sa.Column("bloque_programmation", sa.Boolean(), server_default="true", nullable=False),
        sa.CheckConstraint(
            "type_evenement IN ('ferie', 'vacances', 'rentree', 'examen_officiel', 'autre')",
            name="ck_evenement_calendrier_type",
        ),
    )

    op.create_table(
        "seance_cours",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("id_classe", UUID(as_uuid=True), sa.ForeignKey("classe.id", ondelete="CASCADE"), nullable=False),
        sa.Column("id_matiere", UUID(as_uuid=True), sa.ForeignKey("matiere.id", ondelete="CASCADE"), nullable=False),
        sa.Column("id_enseignant", UUID(as_uuid=True), sa.ForeignKey("enseignant.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("id_annee", UUID(as_uuid=True), sa.ForeignKey("annee_scolaire.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date_seance", sa.Date(), nullable=False),
        sa.Column("contenu", sa.Text(), nullable=False),
        sa.UniqueConstraint("id_classe", "id_matiere", "date_seance", name="uq_seance_cours_classe_matiere_date"),
    )


def downgrade():
    from alembic import op

    op.drop_table("seance_cours")
    op.drop_table("evenement_calendrier")
