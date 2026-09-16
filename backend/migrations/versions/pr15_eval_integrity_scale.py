"""PR #15 — évaluation catalogue + scale_max sur résultats persistés.

- Drop CHECK système-only sur evaluation.type_evaluation (validation app via catalogue).
- Ajoute academic_subject_result.scale_max (échelle du ruleset résolu).
"""

from alembic import op
import sqlalchemy as sa

revision = "pr15_eval_integrity_scale"
down_revision = "academic_results_pr13"
branch_labels = None
depends_on = None

_SYSTEM_ALLOWED = (
    "devoir",
    "interrogation",
    "composition",
    "examen",
    "tp",
    "oral",
    "projet",
    "exam_blanc",
    "rattrapage",
)


def upgrade():
    op.drop_constraint("evaluation_type_evaluation_check", "evaluation", type_="check")
    op.add_column(
        "academic_subject_result",
        sa.Column("scale_max", sa.Numeric(6, 2), nullable=True),
    )


def downgrade():
    op.drop_column("academic_subject_result", "scale_max")
    # Restaure le CHECK système ; codes custom éventuels → 'examen'
    allowed = ", ".join(f"'{c}'" for c in _SYSTEM_ALLOWED)
    op.execute(
        f"""
        UPDATE evaluation
        SET type_evaluation = 'examen'
        WHERE type_evaluation NOT IN ({allowed})
        """
    )
    op.create_check_constraint(
        "evaluation_type_evaluation_check",
        "evaluation",
        f"type_evaluation IN ({allowed})",
    )
