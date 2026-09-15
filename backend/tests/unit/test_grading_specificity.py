"""Tests unitaires — scoring de spécificité (PR #12 Step 2, sans DB)."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.models.grading import WEIGHT_PERCENT_SCALE
from app.services.grading_rules import (
    SPEC_LEVEL,
    SPEC_PROGRAM,
    SPEC_SUBJECT,
    GradingRulesInvalidError,
    ResolvedComponent,
    scope_description_for,
    scope_level_label,
    specificity_score,
    validate_component_weights,
)


class TestSpecificityScore:
    def test_school_default_is_zero(self):
        assert specificity_score(id_program=None, id_niveau=None, id_matiere=None) == 0

    def test_program_only(self):
        assert (
            specificity_score(id_program=uuid.uuid4(), id_niveau=None, id_matiere=None)
            == SPEC_PROGRAM
        )

    def test_program_level(self):
        assert (
            specificity_score(id_program=uuid.uuid4(), id_niveau=uuid.uuid4(), id_matiere=None)
            == SPEC_PROGRAM + SPEC_LEVEL
        )

    def test_subject_only(self):
        assert (
            specificity_score(id_program=None, id_niveau=None, id_matiere=uuid.uuid4())
            == SPEC_SUBJECT
        )

    def test_program_subject(self):
        assert (
            specificity_score(id_program=uuid.uuid4(), id_niveau=None, id_matiere=uuid.uuid4())
            == SPEC_PROGRAM + SPEC_SUBJECT
        )

    def test_full_scope_highest(self):
        full = specificity_score(
            id_program=uuid.uuid4(), id_niveau=uuid.uuid4(), id_matiere=uuid.uuid4()
        )
        program_subject = SPEC_PROGRAM + SPEC_SUBJECT
        school = 0
        assert full > program_subject > school
        assert full == SPEC_PROGRAM + SPEC_LEVEL + SPEC_SUBJECT

    def test_subject_outranks_program_level(self):
        """Matière seule (100) > programme+niveau (11)."""
        assert SPEC_SUBJECT > SPEC_PROGRAM + SPEC_LEVEL

    def test_hierarchy_order(self):
        scores = [
            specificity_score(id_program=None, id_niveau=None, id_matiere=None),
            specificity_score(id_program=uuid.uuid4(), id_niveau=None, id_matiere=None),
            specificity_score(id_program=uuid.uuid4(), id_niveau=uuid.uuid4(), id_matiere=None),
            specificity_score(id_program=None, id_niveau=None, id_matiere=uuid.uuid4()),
            specificity_score(id_program=uuid.uuid4(), id_niveau=None, id_matiere=uuid.uuid4()),
            specificity_score(
                id_program=uuid.uuid4(), id_niveau=uuid.uuid4(), id_matiere=uuid.uuid4()
            ),
        ]
        assert scores == sorted(scores)


class TestScopeDescription:
    def test_school_year(self):
        assert (
            scope_description_for(id_program=None, id_niveau=None, id_matiere=None)
            == "school+year"
        )

    def test_full(self):
        assert (
            scope_description_for(
                id_program=uuid.uuid4(), id_niveau=uuid.uuid4(), id_matiere=uuid.uuid4()
            )
            == "school+year+program+level+subject"
        )

    def test_scope_level_labels(self):
        assert scope_level_label(0) == "school"
        assert scope_level_label(SPEC_PROGRAM) == "program"
        assert scope_level_label(SPEC_SUBJECT) == "subject"
        assert scope_level_label(SPEC_SUBJECT + SPEC_LEVEL + SPEC_PROGRAM) == "program+level+subject"


class TestValidateComponentWeights:
    def _comp(self, weight: str, seq: int = 1) -> ResolvedComponent:
        return ResolvedComponent(
            id=uuid.uuid4(),
            code=f"C{seq}",
            label=f"C{seq}",
            evaluation_type_id=uuid.uuid4(),
            evaluation_type_code="devoir",
            evaluation_context="normal",
            weight=Decimal(weight),
            sequence=seq,
            is_required=True,
        )

    def test_sum_100_ok(self):
        total = validate_component_weights([self._comp("60.00", 1), self._comp("40.00", 2)])
        assert total == WEIGHT_PERCENT_SCALE

    def test_sum_not_100_raises(self):
        with pytest.raises(GradingRulesInvalidError) as exc:
            validate_component_weights([self._comp("60.00"), self._comp("30.00", 2)])
        assert exc.value.code == "RULESET_INVALID"

    def test_empty_raises(self):
        with pytest.raises(GradingRulesInvalidError):
            validate_component_weights([])
