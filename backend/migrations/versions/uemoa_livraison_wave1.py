"""UEMOA livraison Vague A/B — intégrité finance + setup + SYSCOHADA stub + template bulletin.

- Unique métier frais / échéances (après soft-dedup)
- school_setup_progress (checklist démarrage)
- etablissement.bulletin_template
- plan_comptable_syscohada (lecture, seed minimal)
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "uemoa_livraison_wave1"
down_revision = "erp_roles_notifications_inbox"
branch_labels = None
depends_on = None


def upgrade():
    # --- Soft-dedup échéances (garde le plus ancien id) ---
    op.execute(
        """
        DELETE FROM echeance_paiement a
        USING echeance_paiement b
        WHERE a.id > b.id
          AND a.id_frais = b.id_frais
          AND COALESCE(a.libelle, '') = COALESCE(b.libelle, '')
          AND a.date_echeance = b.date_echeance
        """
    )
    # --- Soft-dedup frais (cascade échéances orphelines via ON DELETE CASCADE SQL) ---
    op.execute(
        """
        DELETE FROM echeance_paiement
        WHERE id_frais IN (
            SELECT a.id
            FROM frais_scolaire a
            JOIN frais_scolaire b
              ON a.id > b.id
             AND a.school_id = b.school_id
             AND a.id_niveau = b.id_niveau
             AND a.id_annee = b.id_annee
             AND a.motif = b.motif
        )
        """
    )
    op.execute(
        """
        DELETE FROM frais_scolaire a
        USING frais_scolaire b
        WHERE a.id > b.id
          AND a.school_id = b.school_id
          AND a.id_niveau = b.id_niveau
          AND a.id_annee = b.id_annee
          AND a.motif = b.motif
        """
    )

    op.create_unique_constraint(
        "uq_frais_school_niveau_annee_motif",
        "frais_scolaire",
        ["school_id", "id_niveau", "id_annee", "motif"],
    )
    # libelle peut être NULL → index d'expression (NULL traité comme '')
    op.execute(
        """
        CREATE UNIQUE INDEX uq_echeance_frais_libelle_date
        ON echeance_paiement (id_frais, COALESCE(libelle, ''), date_echeance)
        """
    )

    # Template bulletin (pays) — défaut BF
    op.add_column(
        "etablissement",
        sa.Column(
            "bulletin_template",
            sa.String(length=20),
            nullable=False,
            server_default="BF",
        ),
    )

    op.create_table(
        "school_setup_progress",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "school_id",
            UUID(as_uuid=True),
            sa.ForeignKey("schools.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("niveaux_ok", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("classes_ok", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("frais_ok", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("eleves_ok", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("enseignants_ok", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "plan_comptable_syscohada",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "school_id",
            UUID(as_uuid=True),
            sa.ForeignKey("schools.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("compte", sa.String(length=16), nullable=False),
        sa.Column("libelle", sa.String(length=120), nullable=False),
        sa.Column("classe", sa.String(length=8), nullable=False),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("school_id", "compte", name="uq_plan_comptable_school_compte"),
    )


def downgrade():
    op.drop_table("plan_comptable_syscohada")
    op.drop_table("school_setup_progress")
    op.drop_column("etablissement", "bulletin_template")
    op.execute("DROP INDEX IF EXISTS uq_echeance_frais_libelle_date")
    op.drop_constraint("uq_frais_school_niveau_annee_motif", "frais_scolaire", type_="unique")
