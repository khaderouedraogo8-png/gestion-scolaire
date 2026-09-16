"""Tests CRUD evaluation_type (delivery)."""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from flask_jwt_extended import create_access_token

from app.auth.jwt_handler import hash_password
from app.models import AnneeScolaire, Etablissement, School, Utilisateur
from app.services.academic import get_or_create_general_program
from app.services.evaluation_types import ensure_system_evaluation_types


def _auth(app, user_id):
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def etype_ctx(db, app):
    suffix = uuid.uuid4().hex[:8]
    school = School(
        id=uuid.uuid4(), name=f"ET {suffix}", code=f"ET-{suffix}", is_active=True
    )
    db.add(school)
    db.flush()
    ensure_system_evaluation_types(db, school.id)
    get_or_create_general_program(db, school.id)
    db.add(
        Etablissement(
            id=uuid.uuid4(), school_id=school.id, nom=school.name, format_matricule="{ANNEE}M-{SEQ}"
        )
    )
    admin = Utilisateur(
        id=uuid.uuid4(),
        nom="A",
        prenom="B",
        email=f"et-{suffix}@t.local",
        mot_de_passe_hash=hash_password("Admin123!"),
        role="administrateur",
        actif=True,
        school_id=school.id,
    )
    db.add(admin)
    db.add(
        AnneeScolaire(
            id=uuid.uuid4(),
            school_id=school.id,
            libelle=f"2025-{suffix}",
            date_debut=date(2025, 9, 1),
            date_fin=date(2026, 6, 30),
            est_active=True,
        )
    )
    db.commit()
    return {"admin_id": admin.id}


class TestEvaluationTypeCrud:
    def test_create_custom_and_deactivate(self, client, app, etype_ctx):
        headers = _auth(app, etype_ctx["admin_id"])
        create = client.post(
            "/api/evaluation-types",
            headers=headers,
            json={"code": "quiz", "label": "Quiz"},
        )
        assert create.status_code == 201, create.get_json()
        tid = create.get_json()["id"]

        deact = client.post(f"/api/evaluation-types/{tid}/deactivate", headers=headers)
        assert deact.status_code == 200
        assert deact.get_json()["is_active"] is False

        active = client.get("/api/evaluation-types?active_only=true", headers=headers)
        codes = [i["code"] for i in active.get_json()["items"]]
        assert "quiz" not in codes

    def test_duplicate_rejected(self, client, app, etype_ctx):
        headers = _auth(app, etype_ctx["admin_id"])
        client.post(
            "/api/evaluation-types",
            headers=headers,
            json={"code": "oral_blanc", "label": "Oral blanc"},
        )
        dup = client.post(
            "/api/evaluation-types",
            headers=headers,
            json={"code": "oral_blanc", "label": "Autre"},
        )
        assert dup.status_code == 409
