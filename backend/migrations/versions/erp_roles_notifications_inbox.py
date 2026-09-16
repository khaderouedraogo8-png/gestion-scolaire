"""ERP finalisation — inbox parent + clé d'idempotence notifications.

Parent: delivery_bulletin_scale
"""

import sqlalchemy as sa
from alembic import op

revision = "erp_roles_notifications_inbox"
down_revision = "delivery_bulletin_scale"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "notification",
        sa.Column("lu_le", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "notification",
        sa.Column("idempotency_key", sa.String(120), nullable=True),
    )
    op.create_index(
        "ix_notification_idempotency_key",
        "notification",
        ["school_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.create_index(
        "ix_notification_id_parent_created",
        "notification",
        ["id_parent", "created_at"],
    )
    # Canal inbox interne (en plus de sms/email)
    op.execute("ALTER TABLE notification DROP CONSTRAINT IF EXISTS notification_canal_check")
    op.execute(
        "ALTER TABLE notification ADD CONSTRAINT notification_canal_check "
        "CHECK (canal IS NULL OR canal IN ('sms', 'email', 'interne'))"
    )


def downgrade():
    op.execute("ALTER TABLE notification DROP CONSTRAINT IF EXISTS notification_canal_check")
    op.execute(
        "ALTER TABLE notification ADD CONSTRAINT notification_canal_check "
        "CHECK (canal IS NULL OR canal IN ('sms', 'email'))"
    )
    op.drop_index("ix_notification_id_parent_created", table_name="notification")
    op.drop_index("ix_notification_idempotency_key", table_name="notification")
    op.drop_column("notification", "idempotency_key")
    op.drop_column("notification", "lu_le")
