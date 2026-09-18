"""SaaS commercial billing — plans, abonnements, factures.

down_revision: deerflow_elearning_lms
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "saas_billing_foundation"
down_revision = "deerflow_elearning_lms"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    def _has_table(table: str) -> bool:
        return bool(
            conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables WHERE table_name=:t"
                ),
                {"t": table},
            ).fetchone()
        )

    if not _has_table("saas_plan"):
        op.create_table(
            "saas_plan",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("code", sa.String(40), nullable=False, unique=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "price_xof",
                sa.Numeric(12, 2),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "billing_interval",
                sa.String(20),
                nullable=False,
                server_default="mensuel",
            ),
            sa.Column("max_eleves", sa.Integer(), nullable=True),
            sa.Column(
                "trial_days",
                sa.Integer(),
                nullable=False,
                server_default="14",
            ),
            sa.Column(
                "grace_days",
                sa.Integer(),
                nullable=False,
                server_default="7",
            ),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "sort_order",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
        )

    if not _has_table("school_subscription"):
        op.create_table(
            "school_subscription",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("school_id", UUID(as_uuid=True), nullable=False),
            sa.Column("plan_id", UUID(as_uuid=True), nullable=False),
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="trial",
            ),
            sa.Column("trial_ends_at", sa.Date(), nullable=True),
            sa.Column("current_period_start", sa.Date(), nullable=True),
            sa.Column("current_period_end", sa.Date(), nullable=True),
            sa.Column(
                "grace_days",
                sa.Integer(),
                nullable=False,
                server_default="7",
            ),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["plan_id"], ["saas_plan.id"], ondelete="RESTRICT"),
            sa.UniqueConstraint("school_id", name="uq_school_subscription_school"),
        )
        op.create_index(
            "ix_school_subscription_school_id",
            "school_subscription",
            ["school_id"],
        )
        op.create_index(
            "ix_school_subscription_plan_id",
            "school_subscription",
            ["plan_id"],
        )

    if not _has_table("saas_invoice"):
        op.create_table(
            "saas_invoice",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("school_id", UUID(as_uuid=True), nullable=False),
            sa.Column("subscription_id", UUID(as_uuid=True), nullable=False),
            sa.Column("number", sa.String(40), nullable=False, unique=True),
            sa.Column("amount_xof", sa.Numeric(12, 2), nullable=False),
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="issued",
            ),
            sa.Column("period_start", sa.Date(), nullable=True),
            sa.Column("period_end", sa.Date(), nullable=True),
            sa.Column("due_at", sa.Date(), nullable=True),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("external_ref", sa.String(120), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["subscription_id"],
                ["school_subscription.id"],
                ondelete="CASCADE",
            ),
        )
        op.create_index("ix_saas_invoice_school_id", "saas_invoice", ["school_id"])
        op.create_index(
            "ix_saas_invoice_subscription_id",
            "saas_invoice",
            ["subscription_id"],
        )


def downgrade():
    op.drop_table("saas_invoice")
    op.drop_table("school_subscription")
    op.drop_table("saas_plan")
