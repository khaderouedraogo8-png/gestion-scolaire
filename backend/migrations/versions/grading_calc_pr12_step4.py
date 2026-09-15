"""PR #12 step 4 — expand evaluation.type_evaluation to catalogue codes.

Allows Evaluation rows to use the same codes as evaluation_type / GradingRuleComponent
(composition, tp, oral, …) so the Calculation Engine can match components.
"""

from alembic import op

revision = "grading_calc_pr12_step4"
down_revision = "grading_rules_pr12_step1"
branch_labels = None
depends_on = None

# Aligné sur SYSTEM_EVALUATION_TYPE_CODES (models/grading.py)
_ALLOWED = (
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
    allowed = ", ".join(f"'{c}'" for c in _ALLOWED)
    op.create_check_constraint(
        "evaluation_type_evaluation_check",
        "evaluation",
        f"type_evaluation IN ({allowed})",
    )


def downgrade():
    # Downgrade unsafe if new codes exist — restrict only if clean
    op.execute(
        """
        UPDATE evaluation
        SET type_evaluation = 'examen'
        WHERE type_evaluation NOT IN ('devoir', 'examen', 'interrogation')
        """
    )
    op.drop_constraint("evaluation_type_evaluation_check", "evaluation", type_="check")
    op.create_check_constraint(
        "evaluation_type_evaluation_check",
        "evaluation",
        "type_evaluation IN ('devoir', 'examen', 'interrogation')",
    )
