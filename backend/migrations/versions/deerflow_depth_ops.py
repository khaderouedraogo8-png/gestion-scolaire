"""Deerflow depth ops — paie/cantine/transport/biblio/sortie/inventaire.

Ajoute colonnes métier et table transport_pointage pour approfondir
les modules au-delà du CRUD mince.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "deerflow_depth_ops"
down_revision = "deerflow_depth_roles"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    def _has_column(table: str, column: str) -> bool:
        return bool(
            conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name=:t AND column_name=:c"
                ),
                {"t": table, "c": column},
            ).fetchone()
        )

    def _has_table(table: str) -> bool:
        return bool(
            conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_name=:t"
                ),
                {"t": table},
            ).fetchone()
        )

    if not _has_column("cantine_abonnement", "id_paiement"):
        op.add_column(
            "cantine_abonnement",
            sa.Column("id_paiement", UUID(as_uuid=True), nullable=True),
        )

    if not _has_column("bibliotheque_pret", "amende"):
        op.add_column(
            "bibliotheque_pret",
            sa.Column(
                "amende",
                sa.Numeric(12, 2),
                nullable=False,
                server_default="0",
            ),
        )

    if not _has_column("sortie_eleve", "token_hmac"):
        op.add_column(
            "sortie_eleve",
            sa.Column("token_hmac", sa.String(128), nullable=True),
        )
    if not _has_column("sortie_eleve", "parent_valide"):
        op.add_column(
            "sortie_eleve",
            sa.Column(
                "parent_valide",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )
    if not _has_column("sortie_eleve", "parent_valide_le"):
        op.add_column(
            "sortie_eleve",
            sa.Column("parent_valide_le", sa.DateTime(timezone=True), nullable=True),
        )

    if not _has_table("transport_pointage"):
        op.create_table(
            "transport_pointage",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("school_id", UUID(as_uuid=True), nullable=False),
            sa.Column("id_arret", UUID(as_uuid=True), nullable=False),
            sa.Column("id_eleve", UUID(as_uuid=True), nullable=False),
            sa.Column("date_pointage", sa.Date(), nullable=False),
            sa.Column(
                "embarque",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["school_id"],
                ["schools.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["id_arret"],
                ["transport_arret.id"],
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint(
                "school_id",
                "id_arret",
                "date_pointage",
                "id_eleve",
                name="uq_transport_pointage_arret_date_eleve",
            ),
        )
        op.create_index(
            "ix_transport_pointage_school_id",
            "transport_pointage",
            ["school_id"],
        )
        op.create_index(
            "ix_transport_pointage_id_arret",
            "transport_pointage",
            ["id_arret"],
        )
        op.create_index(
            "ix_transport_pointage_id_eleve",
            "transport_pointage",
            ["id_eleve"],
        )


def downgrade():
    op.drop_table("transport_pointage")
    op.drop_column("sortie_eleve", "parent_valide_le")
    op.drop_column("sortie_eleve", "parent_valide")
    op.drop_column("sortie_eleve", "token_hmac")
    op.drop_column("bibliotheque_pret", "amende")
    op.drop_column("cantine_abonnement", "id_paiement")
