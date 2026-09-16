"""Delivery — bulletin moyennes Numeric(6,2) pour échelles > 20.

Parent: pr16_note_scale_integrity
"""

import sqlalchemy as sa
from alembic import op

revision = "delivery_bulletin_scale"
down_revision = "pr16_note_scale_integrity"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "bulletin",
        "moyenne_generale",
        existing_type=sa.Numeric(4, 2),
        type_=sa.Numeric(6, 2),
        existing_nullable=True,
    )
    op.alter_column(
        "bulletin",
        "moyenne_classe",
        existing_type=sa.Numeric(4, 2),
        type_=sa.Numeric(6, 2),
        existing_nullable=True,
    )


def downgrade():
    op.execute(
        """
        UPDATE bulletin
        SET moyenne_generale = LEAST(moyenne_generale, 99.99)
        WHERE moyenne_generale IS NOT NULL AND moyenne_generale > 99.99
        """
    )
    op.execute(
        """
        UPDATE bulletin
        SET moyenne_classe = LEAST(moyenne_classe, 99.99)
        WHERE moyenne_classe IS NOT NULL AND moyenne_classe > 99.99
        """
    )
    op.alter_column(
        "bulletin",
        "moyenne_generale",
        existing_type=sa.Numeric(6, 2),
        type_=sa.Numeric(4, 2),
        existing_nullable=True,
    )
    op.alter_column(
        "bulletin",
        "moyenne_classe",
        existing_type=sa.Numeric(6, 2),
        type_=sa.Numeric(4, 2),
        existing_nullable=True,
    )
