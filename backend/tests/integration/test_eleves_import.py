"""Tests import bulk élèves."""
from __future__ import annotations

import io
import uuid
from datetime import date

import pytest
from flask_jwt_extended import create_access_token
from openpyxl import Workbook

from app.auth.jwt_handler import hash_password
from app.models import (
    AnneeScolaire,
    Classe,
    Eleve,
    Etablissement,
    NiveauEtude,
    School,
    Utilisateur,
)
from app.services.academic import get_or_create_general_program
from app.services.evaluation_types import ensure_system_evaluation_types


def _auth(app, user_id):
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def import_ctx(db, app):
    suffix = uuid.uuid4().hex[:8]
    school = School(
        id=uuid.uuid4(), name=f"Imp {suffix}", code=f"IM-{suffix}", is_active=True
    )
    db.add(school)
    db.flush()
    ensure_system_evaluation_types(db, school.id)
    program = get_or_create_general_program(db, school.id)
    db.add(
        Etablissement(
            id=uuid.uuid4(),
            school_id=school.id,
            nom=school.name,
            format_matricule="{ANNEE}M-{SEQ}",
        )
    )
    admin = Utilisateur(
        id=uuid.uuid4(),
        nom="Admin",
        prenom="Imp",
        email=f"admin-imp-{suffix}@t.local",
        mot_de_passe_hash=hash_password("Admin123!"),
        role="administrateur",
        actif=True,
        school_id=school.id,
    )
    db.add(admin)
    annee = AnneeScolaire(
        id=uuid.uuid4(),
        school_id=school.id,
        libelle=f"2025-{suffix}",
        date_debut=date(2025, 9, 1),
        date_fin=date(2026, 6, 30),
        est_active=True,
    )
    db.add(annee)
    db.flush()
    niveau = NiveauEtude(
        id=uuid.uuid4(),
        school_id=school.id,
        id_program=program.id,
        libelle="6ème",
        ordre=1,
        cycle="premier",
    )
    db.add(niveau)
    db.flush()
    classe = Classe(
        id=uuid.uuid4(),
        school_id=school.id,
        id_niveau=niveau.id,
        id_annee=annee.id,
        id_program=program.id,
        libelle="6ème A",
    )
    db.add(classe)
    db.commit()
    return {
        "admin_id": admin.id,
        "annee_id": annee.id,
        "classe_id": classe.id,
        "school_id": school.id,
        "classe_libelle": "6ème A",
    }


def _xlsx_bytes(rows):
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestElevesImport:
    def test_preview_and_confirm(self, client, app, import_ctx, db):
        headers = _auth(app, import_ctx["admin_id"])
        content = _xlsx_bytes(
            [
                ["matricule", "nom", "prenom", "sexe", "classe"],
                ["IMP001", "TRAORE", "Ali", "M", import_ctx["classe_libelle"]],
                ["", "KABORE", "Fatou", "F", import_ctx["classe_libelle"]],
            ]
        )
        preview = client.post(
            "/api/eleves/import/preview",
            headers=headers,
            data={
                "id_annee": str(import_ctx["annee_id"]),
                "file": (io.BytesIO(content), "eleves.xlsx"),
            },
            content_type="multipart/form-data",
        )
        assert preview.status_code == 200, preview.get_json()
        body = preview.get_json()
        assert body["summary"]["ok"] == 2
        assert body["summary"]["errors"] == 0

        confirm = client.post(
            "/api/eleves/import/confirm",
            headers=headers,
            json={
                "id_annee": str(import_ctx["annee_id"]),
                "rows": body["items"],
            },
        )
        assert confirm.status_code == 201, confirm.get_json()
        assert confirm.get_json()["imported"] == 2
        assert db.query(Eleve).filter(Eleve.school_id == import_ctx["school_id"]).count() == 2

    def test_rejects_duplicate_matricule(self, client, app, import_ctx, db):
        headers = _auth(app, import_ctx["admin_id"])
        # seed existing
        db.add(
            Eleve(
                id=uuid.uuid4(),
                school_id=import_ctx["school_id"],
                matricule="DUP99",
                nom="Exist",
                prenom="Deja",
                sexe="M",
            )
        )
        db.commit()
        content = _xlsx_bytes(
            [
                ["matricule", "nom", "prenom", "classe"],
                ["DUP99", "NEW", "One", import_ctx["classe_libelle"]],
            ]
        )
        preview = client.post(
            "/api/eleves/import/preview",
            headers=headers,
            data={
                "id_annee": str(import_ctx["annee_id"]),
                "file": (io.BytesIO(content), "eleves.xlsx"),
            },
            content_type="multipart/form-data",
        )
        assert preview.status_code == 200
        assert preview.get_json()["summary"]["errors"] == 1

    def test_rejects_bad_extension(self, client, app, import_ctx):
        headers = _auth(app, import_ctx["admin_id"])
        resp = client.post(
            "/api/eleves/import/preview",
            headers=headers,
            data={
                "id_annee": str(import_ctx["annee_id"]),
                "file": (io.BytesIO(b"not excel"), "eleves.pdf"),
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "IMPORT_BAD_EXTENSION"

    def test_unauthenticated(self, client, import_ctx):
        resp = client.post(
            "/api/eleves/import/preview",
            data={"id_annee": str(import_ctx["annee_id"])},
        )
        assert resp.status_code == 401
