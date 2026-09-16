"""PR #16 — intégration échelle de notes (scale_max ruleset)."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from flask_jwt_extended import create_access_token

from app.auth.jwt_handler import hash_password
from app.models import (
    AnneeScolaire,
    Classe,
    CoefficientMatiere,
    Eleve,
    Etablissement,
    Evaluation,
    EvaluationType,
    GradingRuleComponent,
    GradingRuleset,
    Inscription,
    Matiere,
    NiveauEtude,
    School,
    Utilisateur,
)
from app.models.emploi_temps import Enseignant
from app.models.grading import GRADING_RULESET_STATUS_ACTIVE
from app.services.academic import build_legacy_period, get_or_create_general_program
from app.services.evaluation_types import ensure_system_evaluation_types


def _auth(app, user_id):
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def scale_ctx(db, app):
    """École avec ruleset scale_max=100 et évaluation devoir."""
    suffix = uuid.uuid4().hex[:8]
    school = School(
        id=uuid.uuid4(), name=f"Scale {suffix}", code=f"SC-{suffix}", is_active=True
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
        prenom="S",
        email=f"admin-scale-{suffix}@t.local",
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
        libelle="2nde",
        ordre=2,
        cycle="second",
    )
    db.add(niveau)
    db.flush()
    classe = Classe(
        id=uuid.uuid4(),
        school_id=school.id,
        id_niveau=niveau.id,
        id_annee=annee.id,
        id_program=program.id,
        libelle="2nde S",
    )
    db.add(classe)
    period = build_legacy_period(
        id_annee=annee.id,
        school_id=school.id,
        id_program=program.id,
        sequence=1,
        date_debut=date(2025, 9, 1),
        date_fin=date(2025, 12, 20),
        period_type="trimestre",
    )
    db.add(period)
    math = Matiere(id=uuid.uuid4(), school_id=school.id, libelle="Math", code="M")
    db.add(math)
    db.flush()
    db.add(
        CoefficientMatiere(
            id=uuid.uuid4(), id_matiere=math.id, id_niveau=niveau.id, coefficient=Decimal(1)
        )
    )
    ens = Enseignant(
        id=uuid.uuid4(),
        school_id=school.id,
        nom="P",
        prenom="R",
        email=f"ens-{suffix}@t.local",
    )
    db.add(ens)
    eleve = Eleve(
        id=uuid.uuid4(),
        school_id=school.id,
        nom="Eleve",
        prenom="Test",
        sexe="M",
        matricule=f"M-{suffix}",
        date_naissance=date(2010, 1, 1),
    )
    db.add(eleve)
    db.flush()
    db.add(
        Inscription(
            id=uuid.uuid4(),
            school_id=school.id,
            id_eleve=eleve.id,
            id_classe=classe.id,
            id_annee=annee.id,
            statut="inscrit",
        )
    )
    devoir = (
        db.query(EvaluationType).filter_by(school_id=school.id, code="devoir").one()
    )
    composition = (
        db.query(EvaluationType).filter_by(school_id=school.id, code="composition").one()
    )
    rs = GradingRuleset(
        id=uuid.uuid4(),
        school_id=school.id,
        code="SCALE100",
        name="Scale 100",
        status=GRADING_RULESET_STATUS_ACTIVE,
        version=1,
        id_annee=annee.id,
        id_program=program.id,
        id_niveau=niveau.id,
        id_matiere=math.id,
        scale_max=Decimal("100.00"),
        rounding_mode="half_up",
        rounding_precision=2,
    )
    db.add(rs)
    db.flush()
    db.add(
        GradingRuleComponent(
            id=uuid.uuid4(),
            school_id=school.id,
            ruleset_id=rs.id,
            code="DEV",
            label="Devoirs",
            id_evaluation_type=devoir.id,
            evaluation_context="normal",
            weight=Decimal("60.00"),
            sequence=1,
            is_required=True,
        )
    )
    db.add(
        GradingRuleComponent(
            id=uuid.uuid4(),
            school_id=school.id,
            ruleset_id=rs.id,
            code="COMP",
            label="Composition",
            id_evaluation_type=composition.id,
            evaluation_context="normal",
            weight=Decimal("40.00"),
            sequence=2,
            is_required=True,
        )
    )
    ev = Evaluation(
        id=uuid.uuid4(),
        school_id=school.id,
        id_classe=classe.id,
        id_matiere=math.id,
        id_trimestre=period.id,
        id_enseignant=ens.id,
        type_evaluation="devoir",
        coefficient=Decimal(1),
        date_evaluation=date(2025, 10, 1),
        libelle="Devoir scale",
        statut_publication="publie",
        statut_saisie="en_cours",
    )
    db.add(ev)
    db.commit()
    return {
        "admin_id": admin.id,
        "eleve_id": eleve.id,
        "ev_id": ev.id,
        "school_id": school.id,
    }


class TestNoteScaleIntegrity:
    def test_grid_exposes_scale_max_100(self, client, app, scale_ctx):
        resp = client.get(
            f"/api/notes/evaluations/{scale_ctx['ev_id']}/notes",
            headers=_auth(app, scale_ctx["admin_id"]),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["evaluation"]["scale_max"] == pytest.approx(100.0)

    def test_accepts_note_85_on_scale_100(self, client, app, scale_ctx):
        resp = client.post(
            f"/api/notes/evaluations/{scale_ctx['ev_id']}/notes",
            headers=_auth(app, scale_ctx["admin_id"]),
            json={
                "notes": [
                    {
                        "id_eleve": str(scale_ctx["eleve_id"]),
                        "valeur_note": 85,
                        "absent": False,
                    }
                ]
            },
        )
        assert resp.status_code == 200, resp.get_json()
        assert resp.get_json()["scale_max"] == pytest.approx(100.0)

    def test_rejects_note_101_on_scale_100(self, client, app, scale_ctx):
        resp = client.post(
            f"/api/notes/evaluations/{scale_ctx['ev_id']}/notes",
            headers=_auth(app, scale_ctx["admin_id"]),
            json={
                "notes": [
                    {
                        "id_eleve": str(scale_ctx["eleve_id"]),
                        "valeur_note": 101,
                        "absent": False,
                    }
                ]
            },
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"]["code"] == "GRADE_OUT_OF_SCALE"

    def test_rejects_negative_note(self, client, app, scale_ctx):
        resp = client.post(
            f"/api/notes/evaluations/{scale_ctx['ev_id']}/notes",
            headers=_auth(app, scale_ctx["admin_id"]),
            json={
                "notes": [
                    {
                        "id_eleve": str(scale_ctx["eleve_id"]),
                        "valeur_note": -0.5,
                        "absent": False,
                    }
                ]
            },
        )
        # Marshmallow Range(min=0) → 422, ou GRADE_OUT_OF_SCALE → 400
        assert resp.status_code in (400, 422)

    def test_unauthenticated_rejected(self, client, scale_ctx):
        resp = client.post(
            f"/api/notes/evaluations/{scale_ctx['ev_id']}/notes",
            json={"notes": [{"id_eleve": str(scale_ctx["eleve_id"]), "valeur_note": 10}]},
        )
        assert resp.status_code == 401

    def test_missing_note_persists_as_null(self, client, app, scale_ctx):
        resp = client.post(
            f"/api/notes/evaluations/{scale_ctx['ev_id']}/notes",
            headers=_auth(app, scale_ctx["admin_id"]),
            json={
                "notes": [
                    {
                        "id_eleve": str(scale_ctx["eleve_id"]),
                        "valeur_note": None,
                        "absent": False,
                    }
                ]
            },
        )
        assert resp.status_code == 200, resp.get_json()
        grid = client.get(
            f"/api/notes/evaluations/{scale_ctx['ev_id']}/notes",
            headers=_auth(app, scale_ctx["admin_id"]),
        ).get_json()
        note = next(n for n in grid["notes"] if n["id_eleve"] == str(scale_ctx["eleve_id"]))
        assert note["valeur_note"] is None
        assert note["absent"] is False
