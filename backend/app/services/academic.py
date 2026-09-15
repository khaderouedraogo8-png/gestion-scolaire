"""Helpers fondation académique — Program GENERAL et périodes."""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.etablissement import (
    PROGRAM_CODE_GENERAL,
    PROGRAM_NAME_GENERAL,
    AcademicPeriod,
    AnneeScolaire,
    Program,
)


def get_or_create_general_program(db: Session, school_id: uuid.UUID) -> Program:
    """Retourne le Program GENERAL de l'école (compatibilité historique permanente).

    Ne crée le programme que s'il n'existe pas déjà. Ne jamais le supprimer
    automatiquement : il rattache les données historiques.
    """
    program = (
        db.query(Program)
        .filter(Program.school_id == school_id, Program.code == PROGRAM_CODE_GENERAL)
        .first()
    )
    if program:
        return program
    program = Program(
        id=uuid.uuid4(),
        school_id=school_id,
        code=PROGRAM_CODE_GENERAL,
        name=PROGRAM_NAME_GENERAL,
        description="Programme de compatibilité historique (données pré-PR11).",
        program_type="general",
        period_type_default="trimestre",
        is_active=True,
    )
    db.add(program)
    db.flush()
    return program


def period_code_and_label(sequence: int, period_type: str = "trimestre") -> tuple[str, str]:
    """Génère code/label UX par défaut pour une période."""
    if period_type == "semestre":
        return f"S{sequence}", f"Semestre {sequence}"
    if period_type == "annuel":
        return "AN", "Année"
    if period_type == "custom":
        return f"P{sequence}", f"Période {sequence}"
    return f"T{sequence}", f"Trimestre {sequence}"


def build_legacy_period(
    *,
    id_annee: uuid.UUID,
    school_id: uuid.UUID,
    id_program: uuid.UUID,
    sequence: int,
    date_debut,
    date_fin,
    period_id: uuid.UUID | None = None,
    period_type: str = "trimestre",
    code: str | None = None,
    label: str | None = None,
) -> AcademicPeriod:
    """Construit une AcademicPeriod avec defaults compatibles façade /trimestres."""
    default_code, default_label = period_code_and_label(sequence, period_type)
    return AcademicPeriod(
        id=period_id or uuid.uuid4(),
        school_id=school_id,
        id_annee=id_annee,
        id_program=id_program,
        sequence=sequence,
        code=code or default_code,
        label=label or default_label,
        period_type=period_type,
        date_debut=date_debut,
        date_fin=date_fin,
        is_active=True,
    )


def resolve_period_school_and_program(
    db: Session,
    id_annee: uuid.UUID,
    id_program: uuid.UUID | None = None,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Résout school_id + program pour création période (façade legacy)."""
    annee = db.query(AnneeScolaire).filter(AnneeScolaire.id == id_annee).first()
    if annee is None:
        raise ValueError("Année scolaire introuvable")
    if id_program is not None:
        program = (
            db.query(Program)
            .filter(Program.id == id_program, Program.school_id == annee.school_id)
            .first()
        )
        if program is None:
            raise ValueError("Programme introuvable pour cette école")
        return annee.school_id, program.id
    general = get_or_create_general_program(db, annee.school_id)
    return annee.school_id, general.id
