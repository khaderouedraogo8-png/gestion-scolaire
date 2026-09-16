"""PR #16 — unit tests échelle de note (scale_max)."""
from __future__ import annotations

from decimal import Decimal

import pytest
from werkzeug.exceptions import HTTPException

from app.models.grading import DEFAULT_SCALE_MAX
from app.services.note_scale import validate_note_valeur_against_scale


class TestValidateNoteAgainstScale:
    def test_accepts_within_scale_100(self, app):
        with app.app_context():
            assert validate_note_valeur_against_scale(
                85, scale_max=Decimal("100.00")
            ) == Decimal(85)

    def test_accepts_exact_scale_max(self, app):
        with app.app_context():
            assert validate_note_valeur_against_scale(
                100, scale_max=Decimal("100.00")
            ) == Decimal(100)

    def test_accepts_zero(self, app):
        with app.app_context():
            assert validate_note_valeur_against_scale(
                0, scale_max=Decimal("20.00")
            ) == Decimal(0)

    def test_missing_is_none(self, app):
        with app.app_context():
            assert (
                validate_note_valeur_against_scale(None, scale_max=Decimal("20.00"))
                is None
            )

    def test_absent_is_none_even_with_value(self, app):
        with app.app_context():
            assert (
                validate_note_valeur_against_scale(
                    12, scale_max=Decimal("20.00"), absent=True
                )
                is None
            )

    def test_rejects_above_scale(self, app):
        with app.app_context():
            with pytest.raises(HTTPException) as exc:
                validate_note_valeur_against_scale(21, scale_max=Decimal("20.00"))
            resp = exc.value.get_response()
            assert resp.status_code == 400
            body = resp.get_json()
            assert body["error"]["code"] == "GRADE_OUT_OF_SCALE"

    def test_rejects_negative(self, app):
        with app.app_context():
            with pytest.raises(HTTPException) as exc:
                validate_note_valeur_against_scale(-1, scale_max=Decimal("20.00"))
            resp = exc.value.get_response()
            assert resp.status_code == 400
            body = resp.get_json()
            assert body["error"]["code"] == "GRADE_OUT_OF_SCALE"

    def test_default_scale_constant(self):
        assert DEFAULT_SCALE_MAX == Decimal("20.00")
