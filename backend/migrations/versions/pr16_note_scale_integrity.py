"""PR #16 — échelle de notation : notes hors plafond /20 hardcodé.

- Drop CHECK note.valeur_note BETWEEN 0 AND 20
- Widen NUMERIC(4,2) → NUMERIC(6,2) pour permettre scale_max jusqu'à 100+
- Garde contrainte valeur_note >= 0 (plafond = app via ruleset)
- Drop/recreate MV moyenne_matiere_eleve (dépend de la colonne)
"""

import sqlalchemy as sa
from alembic import op

revision = "pr16_note_scale_integrity"
down_revision = "pr15_eval_integrity_scale"
branch_labels = None
depends_on = None

_MV_SQL = """
CREATE MATERIALIZED VIEW moyenne_matiere_eleve AS
SELECT
    n.id_eleve,
    e.id_classe,
    e.id_matiere,
    e.id_trimestre,
    ROUND(
        SUM(n.valeur_note * e.coefficient) FILTER (WHERE n.absent = false)
        / NULLIF(SUM(e.coefficient) FILTER (WHERE n.absent = false), 0)
    , 2) AS moyenne
FROM note n
JOIN evaluation e ON e.id = n.id_evaluation
GROUP BY n.id_eleve, e.id_classe, e.id_matiere, e.id_trimestre
"""


def upgrade():
    op.execute("DROP MATERIALIZED VIEW IF EXISTS moyenne_matiere_eleve")
    op.drop_constraint("note_valeur_note_check", "note", type_="check")
    op.alter_column(
        "note",
        "valeur_note",
        existing_type=sa.Numeric(4, 2),
        type_=sa.Numeric(6, 2),
        existing_nullable=True,
    )
    op.create_check_constraint(
        "note_valeur_note_non_negative",
        "note",
        "valeur_note IS NULL OR valeur_note >= 0",
    )
    op.execute(_MV_SQL)
    op.execute(
        "CREATE UNIQUE INDEX idx_moyenne_unique "
        "ON moyenne_matiere_eleve(id_eleve, id_classe, id_matiere, id_trimestre)"
    )


def downgrade():
    op.execute("DROP MATERIALIZED VIEW IF EXISTS moyenne_matiere_eleve")
    op.drop_constraint("note_valeur_note_non_negative", "note", type_="check")
    op.execute(
        """
        UPDATE note
        SET valeur_note = LEAST(valeur_note, 20)
        WHERE valeur_note IS NOT NULL AND valeur_note > 20
        """
    )
    op.alter_column(
        "note",
        "valeur_note",
        existing_type=sa.Numeric(6, 2),
        type_=sa.Numeric(4, 2),
        existing_nullable=True,
    )
    op.create_check_constraint(
        "note_valeur_note_check",
        "note",
        "valeur_note BETWEEN 0 AND 20",
    )
    op.execute(_MV_SQL)
    op.execute(
        "CREATE UNIQUE INDEX idx_moyenne_unique "
        "ON moyenne_matiere_eleve(id_eleve, id_classe, id_matiere, id_trimestre)"
    )
