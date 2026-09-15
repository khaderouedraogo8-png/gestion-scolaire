"""PR #12 Step 4 — tests unitaires Calculation Engine (purs, sans DB)."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.models.grading import (
    GRADING_ROUNDING_DOWN,
    GRADING_ROUNDING_HALF_EVEN,
    GRADING_ROUNDING_HALF_UP,
    GRADING_ROUNDING_UP,
)
from app.services.academic_calculation import (
    GradeInput,
    apply_rounding,
    build_minimal_resolved_rules,
    calculate_general_average,
    calculate_subject_result,
)


def _g(type_code: str, valeur, *, absent: bool = False) -> GradeInput:
    return GradeInput(
        evaluation_id=uuid.uuid4(),
        evaluation_type_code=type_code,
        valeur=None if valeur is None else Decimal(str(valeur)),
        absent=absent,
    )


class TestSubject60_40:
    def test_devoir_14_composition_10(self):
        rules = build_minimal_resolved_rules(
            components=[("DEV", "devoir", Decimal(60)), ("COMP", "composition", Decimal(40))]
        )
        result = calculate_subject_result(
            [_g("devoir", 14), _g("composition", 10)],
            rules,
            subject_id=uuid.uuid4(),
        )
        # 14*0.6 + 10*0.4 = 8.4 + 4 = 12.4
        assert result.subject_average == Decimal("12.40")
        assert not result.incomplete
        assert result.ruleset_version == 1


class TestSubject30_20_50:
    def test_devoir_tp_composition(self):
        rules = build_minimal_resolved_rules(
            components=[
                ("DEV", "devoir", Decimal(30)),
                ("TP", "tp", Decimal(20)),
                ("COMP", "composition", Decimal(50)),
            ]
        )
        result = calculate_subject_result(
            [_g("devoir", 12), _g("tp", 16), _g("composition", 14)],
            rules,
        )
        # 12*0.3 + 16*0.2 + 14*0.5 = 3.6 + 3.2 + 7 = 13.8
        assert result.subject_average == Decimal("13.80")


class TestMultipleDevoirs:
    def test_average_devoirs_then_weight(self):
        rules = build_minimal_resolved_rules(
            components=[("DEV", "devoir", Decimal(60)), ("COMP", "composition", Decimal(40))]
        )
        # devoirs 10, 14, 16 → mean 13.333... ; composition 12
        # 13.333... * 0.6 + 12 * 0.4
        result = calculate_subject_result(
            [
                _g("devoir", 10),
                _g("devoir", 14),
                _g("devoir", 16),
                _g("composition", 12),
            ],
            rules,
        )
        devoir_mean = (Decimal(10) + Decimal(14) + Decimal(16)) / Decimal(3)
        expected_raw = devoir_mean * Decimal("0.60") + Decimal(12) * Decimal("0.40")
        from app.services.academic_calculation import apply_rounding

        expected = apply_rounding(expected_raw, mode="half_up", precision=2)
        assert result.subject_average == expected
        dev = next(c for c in result.components if c.code == "DEV")
        assert len(dev.grade_values) == 3
        assert dev.component_average == devoir_mean


class TestZeroAndMissing:
    def test_explicit_zero_counts(self):
        rules = build_minimal_resolved_rules(
            components=[("DEV", "devoir", Decimal(60)), ("COMP", "composition", Decimal(40))]
        )
        result = calculate_subject_result(
            [_g("devoir", 0), _g("composition", 14)],
            rules,
        )
        # 0*0.6 + 14*0.4 = 5.6
        assert result.subject_average == Decimal("5.60")

    def test_none_not_zero_required_missing(self):
        rules = build_minimal_resolved_rules(
            components=[("DEV", "devoir", Decimal(60)), ("COMP", "composition", Decimal(40))]
        )
        result = calculate_subject_result(
            [_g("devoir", None), _g("composition", 14)],
            rules,
        )
        assert result.subject_average is None
        assert result.incomplete
        assert "DEV" in (result.incomplete_reason or "")

    def test_absent_excluded_not_zero(self):
        rules = build_minimal_resolved_rules(
            components=[("DEV", "devoir", Decimal(60)), ("COMP", "composition", Decimal(40))]
        )
        result = calculate_subject_result(
            [_g("devoir", 0, absent=True), _g("composition", 14)],
            rules,
        )
        assert result.incomplete
        assert result.subject_average is None

    def test_mix_none_zero_five_twenty(self):
        rules = build_minimal_resolved_rules(
            components=[("DEV", "devoir", Decimal(100))]
        )
        result = calculate_subject_result(
            [
                _g("devoir", None),
                _g("devoir", 0),
                _g("devoir", 5),
                _g("devoir", 20),
            ],
            rules,
        )
        # usable: 0, 5, 20 → mean 8.333... → 8.33
        assert result.subject_average == Decimal("8.33")


class TestCoefficientSeparate:
    def test_coefficient_after_subject_average(self):
        rules = build_minimal_resolved_rules(
            components=[("DEV", "devoir", Decimal(60)), ("COMP", "composition", Decimal(40))]
        )
        result = calculate_subject_result(
            [_g("devoir", 14), _g("composition", 10)],
            rules,
            subject_coefficient=Decimal(5),
        )
        assert result.subject_average == Decimal("12.40")
        assert result.weighted_score == Decimal("62.00")  # 12.40 * 5
        # Must NOT be 14*0.6*5 + ...


class TestRounding:
    @pytest.mark.parametrize(
        "mode,value,expected",
        [
            (GRADING_ROUNDING_HALF_UP, "13.245", "13.25"),
            (GRADING_ROUNDING_HALF_UP, "13.255", "13.26"),
            (GRADING_ROUNDING_HALF_EVEN, "13.25", "13.2"),  # precision 1 for clear half-even
            (GRADING_ROUNDING_DOWN, "13.259", "13.25"),
            (GRADING_ROUNDING_UP, "13.251", "13.26"),
        ],
    )
    def test_apply_rounding_modes(self, mode, value, expected):
        precision = 1 if mode == GRADING_ROUNDING_HALF_EVEN and value == "13.25" else 2
        if mode == GRADING_ROUNDING_HALF_EVEN and value == "13.25":
            assert apply_rounding(Decimal(value), mode=mode, precision=1) == Decimal(expected)
        else:
            assert apply_rounding(Decimal(value), mode=mode, precision=precision) == Decimal(
                expected
            )

    def test_ruleset_rounding_used(self):
        rules = build_minimal_resolved_rules(
            components=[("DEV", "devoir", Decimal(100))],
            rounding_mode=GRADING_ROUNDING_DOWN,
            rounding_precision=1,
        )
        # mean of 13.29 → 13.2 with down precision 1
        result = calculate_subject_result([_g("devoir", "13.29")], rules)
        assert result.subject_average == Decimal("13.2")


class TestScaleMax:
    def test_scale_100_not_assume_20(self):
        rules = build_minimal_resolved_rules(
            components=[("DEV", "devoir", Decimal(50)), ("EX", "examen", Decimal(50))],
            scale_max=Decimal("100.00"),
        )
        result = calculate_subject_result(
            [_g("devoir", 80), _g("examen", 60)],
            rules,
        )
        # 80*0.5 + 60*0.5 = 70 on /100 scale
        assert result.subject_average == Decimal("70.00")
        assert result.scale_max == Decimal("100.00")


class TestGeneralAverage:
    def test_weighted_general(self):
        rules = build_minimal_resolved_rules(
            components=[("DEV", "devoir", Decimal(100))]
        )
        math = calculate_subject_result(
            [_g("devoir", 14)], rules, subject_id=uuid.uuid4(), subject_coefficient=3
        )
        fr = calculate_subject_result(
            [_g("devoir", 12)], rules, subject_id=uuid.uuid4(), subject_coefficient=2
        )
        ga = calculate_general_average([math, fr])
        assert ga.average == Decimal("13.20")

    def test_missing_subject_excluded(self):
        rules = build_minimal_resolved_rules(
            components=[("DEV", "devoir", Decimal(100))]
        )
        math = calculate_subject_result(
            [_g("devoir", 14)], rules, subject_coefficient=3
        )
        incomplete = calculate_subject_result(
            [], rules, subject_coefficient=5
        )
        assert incomplete.subject_average is None
        ga = calculate_general_average([math, incomplete])
        assert ga.average == Decimal("14.00")
        assert ga.subjects_counted == 1

    def test_coef_zero_excluded(self):
        rules = build_minimal_resolved_rules(
            components=[("DEV", "devoir", Decimal(100))]
        )
        a = calculate_subject_result([_g("devoir", 10)], rules, subject_coefficient=0)
        b = calculate_subject_result([_g("devoir", 14)], rules, subject_coefficient=2)
        ga = calculate_general_average([a, b])
        assert ga.average == Decimal("14.00")
