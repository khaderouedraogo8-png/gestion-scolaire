"""PR #13 — persistance résultats académiques + invalidation + API."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from flask_jwt_extended import create_access_token

from app.auth.jwt_handler import hash_password
from app.models import (
    AcademicSubjectResult,
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
    Note,
    School,
    Utilisateur,
)
from app.models.emploi_temps import Enseignant
from app.services.academic import build_legacy_period, get_or_create_general_program
from app.services.academic_results import (
    ensure_student_period_results,
    list_results_for_student_period,
    mark_stale_for_evaluation,
    persist_student_period_results,
)
from app.services.calcul_moyennes import refresh_moyenne_matiere_view
from app.services.evaluation_types import ensure_system_evaluation_types
from app.services.generation_bulletin import generer_bulletin


@pytest.fixture
def results_ctx(db, app):
    """École A + B : ruleset 60/40, notes, inscription."""
    out = {}
    suffix = uuid.uuid4().hex[:8]
    for key, code, name in (
        ("a", f"RES-A-{suffix}", f"École Res A {suffix}"),
        ("b", f"RES-B-{suffix}", f"École Res B {suffix}"),
    ):
        school = School(id=uuid.uuid4(), name=name, code=code, is_active=True)
        db.add(school)
        db.flush()
        ensure_system_evaluation_types(db, school.id)
        program = get_or_create_general_program(db, school.id)
        db.add(
            Etablissement(
                id=uuid.uuid4(),
                school_id=school.id,
                nom=name,
                format_matricule="{ANNEE}M-{SEQ}",
            )
        )
        admin = Utilisateur(
            id=uuid.uuid4(),
            nom="Admin",
            prenom=key.upper(),
            email=f"admin-{key}-{suffix}@res.local",
            mot_de_passe_hash=hash_password("Admin123!"),
            role="administrateur",
            actif=True,
            school_id=school.id,
        )
        db.add(admin)
        annee = AnneeScolaire(
            id=uuid.uuid4(),
            school_id=school.id,
            libelle=f"2025-2026-{suffix}-{key}",
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
            libelle="2nde A",
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
        math = Matiere(id=uuid.uuid4(), school_id=school.id, libelle="Mathématiques", code="MATH")
        db.add(math)
        db.flush()
        db.add(
            CoefficientMatiere(
                id=uuid.uuid4(), id_matiere=math.id, id_niveau=niveau.id, coefficient=Decimal(2)
            )
        )
        ens = Enseignant(
            id=uuid.uuid4(),
            school_id=school.id,
            nom="Prof",
            prenom="Math",
            email=f"ens-{key}-{suffix}@res.local",
        )
        db.add(ens)
        eleve = Eleve(
            id=uuid.uuid4(),
            school_id=school.id,
            nom="Eleve",
            prenom=key.upper(),
            matricule=f"M-{key}-{suffix}",
            date_naissance=date(2010, 1, 1),
            sexe="M",
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
        devoir_t = (
            db.query(EvaluationType)
            .filter(EvaluationType.school_id == school.id, EvaluationType.code == "devoir")
            .one()
        )
        comp_t = (
            db.query(EvaluationType)
            .filter(EvaluationType.school_id == school.id, EvaluationType.code == "composition")
            .one()
        )
        rs = GradingRuleset(
            id=uuid.uuid4(),
            school_id=school.id,
            code="STD",
            name="Standard 60/40",
            status="active",
            version=1,
            id_annee=annee.id,
            scale_max=Decimal(20),
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
                id_evaluation_type=devoir_t.id,
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
                id_evaluation_type=comp_t.id,
                evaluation_context="normal",
                weight=Decimal("40.00"),
                sequence=2,
                is_required=True,
            )
        )
        ev_d = Evaluation(
            id=uuid.uuid4(),
            school_id=school.id,
            id_classe=classe.id,
            id_matiere=math.id,
            id_trimestre=period.id,
            id_enseignant=ens.id,
            type_evaluation="devoir",
            coefficient=Decimal(1),
            date_evaluation=date(2025, 10, 1),
            libelle="Devoir 1",
            statut_publication="publie",
            statut_saisie="cloturee",
        )
        ev_c = Evaluation(
            id=uuid.uuid4(),
            school_id=school.id,
            id_classe=classe.id,
            id_matiere=math.id,
            id_trimestre=period.id,
            id_enseignant=ens.id,
            type_evaluation="composition",
            coefficient=Decimal(1),
            date_evaluation=date(2025, 11, 1),
            libelle="Composition",
            statut_publication="publie",
            statut_saisie="cloturee",
        )
        db.add_all([ev_d, ev_c])
        db.flush()
        # 12 devoir + 16 composition → 0.6*12 + 0.4*16 = 13.60
        n1 = Note(
            id=uuid.uuid4(),
            school_id=school.id,
            id_evaluation=ev_d.id,
            id_eleve=eleve.id,
            valeur_note=Decimal(12),
            absent=False,
        )
        n2 = Note(
            id=uuid.uuid4(),
            school_id=school.id,
            id_evaluation=ev_c.id,
            id_eleve=eleve.id,
            valeur_note=Decimal(16),
            absent=False,
        )
        db.add_all([n1, n2])
        out[key] = {
            "school": school,
            "school_id": school.id,
            "admin": admin,
            "admin_id": admin.id,
            "classe": classe,
            "classe_id": classe.id,
            "period": period,
            "period_id": period.id,
            "math": math,
            "math_id": math.id,
            "eleve": eleve,
            "eleve_id": eleve.id,
            "ruleset": rs,
            "ruleset_id": rs.id,
            "ev_devoir": ev_d,
            "ev_devoir_id": ev_d.id,
            "note_devoir": n1,
            "note_devoir_id": n1.id,
        }
    db.commit()
    return out


def _auth(app, user_id, *, role="administrateur", email="x@test.local"):
    with app.app_context():
        from app.extensions import get_db
        from app.models import Utilisateur

        u = get_db().get(Utilisateur, user_id)
        token = create_access_token(
            identity=str(u.id),
            additional_claims={"role": u.role, "email": u.email},
        )
    return {"Authorization": f"Bearer {token}"}


def _auth_ctx(app, user_id):
    from app.extensions import get_db
    from app.models import Utilisateur

    u = get_db().get(Utilisateur, user_id)
    token = create_access_token(
        identity=str(u.id),
        additional_claims={"role": u.role, "email": u.email},
    )
    return app.test_request_context(headers={"Authorization": f"Bearer {token}"})



class TestAcademicResultsPersist:
    def test_persist_stores_ruleset_and_average(self, db, app, results_ctx):
        a = results_ctx["a"]
        with _auth_ctx(app, a["admin_id"]):
            from flask_jwt_extended import verify_jwt_in_request

            verify_jwt_in_request()
            refresh_moyenne_matiere_view(db)
            rows = persist_student_period_results(
                db,
                id_eleve=a["eleve_id"],
                id_classe=a["classe_id"],
                id_period=a["period_id"],
            )
            db.commit()
        assert len(rows) == 1
        r = rows[0]
        assert r.source == "rules_engine"
        assert r.ruleset_id == a["ruleset_id"]
        assert r.ruleset_version == 1
        assert float(r.moyenne) == pytest.approx(13.60, abs=0.01)
        assert r.is_stale is False
        assert r.scale_max is not None
        assert float(r.scale_max) == pytest.approx(20.0)

    def test_no_ruleset_persists_incomplete_not_legacy(self, db, app, results_ctx):
        """PR15-B : sans ruleset ACTIVE → incomplete, jamais source=legacy + MV."""
        from app.models.grading import GRADING_RULESET_STATUS_ARCHIVED, GradingRuleset

        a = results_ctx["a"]
        with _auth_ctx(app, a["admin_id"]):
            from flask_jwt_extended import verify_jwt_in_request

            verify_jwt_in_request()
            rs = db.get(GradingRuleset, a["ruleset_id"])
            rs.status = GRADING_RULESET_STATUS_ARCHIVED
            db.commit()
            rows = persist_student_period_results(
                db,
                id_eleve=a["eleve_id"],
                id_classe=a["classe_id"],
                id_period=a["period_id"],
            )
            db.commit()
        assert len(rows) >= 1
        r = rows[0]
        assert r.source == "rules_engine"
        assert r.incomplete is True
        assert r.moyenne is None
        assert r.incomplete_reason == "NO_RULESET"

    def test_note_change_marks_stale_then_recalc(self, db, app, results_ctx):
        a = results_ctx["a"]
        with _auth_ctx(app, a["admin_id"]):
            from flask_jwt_extended import verify_jwt_in_request

            verify_jwt_in_request()
            refresh_moyenne_matiere_view(db)
            persist_student_period_results(
                db,
                id_eleve=a["eleve_id"],
                id_classe=a["classe_id"],
                id_period=a["period_id"],
            )
            db.commit()
            ev = db.get(Evaluation, a["ev_devoir_id"])
            n = mark_stale_for_evaluation(db, ev)
            db.commit()
            assert n >= 1
            row = list_results_for_student_period(
                db,
                id_eleve=a["eleve_id"],
                id_classe=a["classe_id"],
                id_period=a["period_id"],
            )[0]
            assert row.is_stale is True

            note = db.get(Note, a["note_devoir_id"])
            note.valeur_note = Decimal(18)
            db.commit()
            refresh_moyenne_matiere_view(db)
            rows = ensure_student_period_results(
                db,
                id_eleve=a["eleve_id"],
                id_classe=a["classe_id"],
                id_period=a["period_id"],
            )
            db.commit()
            assert rows[0].is_stale is False
            # 0.6*18 + 0.4*16 = 17.20
            assert float(rows[0].moyenne) == pytest.approx(17.20, abs=0.01)

    def test_bulletin_consumes_persisted_and_snapshots_ruleset(self, db, app, results_ctx):
        a = results_ctx["a"]
        with _auth_ctx(app, a["admin_id"]):
            from flask_jwt_extended import verify_jwt_in_request

            verify_jwt_in_request()
            refresh_moyenne_matiere_view(db)
            bulletin = generer_bulletin(a["eleve_id"], a["period_id"], a["admin_id"])
            assert float(bulletin.moyenne_generale) == pytest.approx(13.60, abs=0.01)
            assert bulletin.rulesets_snapshot
            assert any(
                s.get("ruleset_id") == str(a["ruleset_id"]) for s in bulletin.rulesets_snapshot
            )
            assert bulletin.results_calculated_at is not None
            stored = (
                db.query(AcademicSubjectResult)
                .filter(
                    AcademicSubjectResult.school_id == a["school_id"],
                    AcademicSubjectResult.id_eleve == a["eleve_id"],
                )
                .count()
            )
            assert stored >= 1

    def test_tenant_isolation_results_api(self, client, app, db, results_ctx):
        a = results_ctx["a"]
        b = results_ctx["b"]
        with _auth_ctx(app, a["admin_id"]):
            from flask_jwt_extended import verify_jwt_in_request

            verify_jwt_in_request()
            refresh_moyenne_matiere_view(db)
            persist_student_period_results(
                db,
                id_eleve=a["eleve_id"],
                id_classe=a["classe_id"],
                id_period=a["period_id"],
            )
            db.commit()

        resp = client.get(
            "/api/notes/resultats",
            headers=_auth(app, b["admin_id"]),
            query_string={
                "id_eleve": str(a["eleve_id"]),
                "id_classe": str(a["classe_id"]),
                "id_period": str(a["period_id"]),
            },
        )
        assert resp.status_code == 404

        resp_ok = client.get(
            "/api/notes/resultats",
            headers=_auth(app, a["admin_id"]),
            query_string={
                "id_eleve": str(a["eleve_id"]),
                "id_classe": str(a["classe_id"]),
                "id_period": str(a["period_id"]),
            },
        )
        assert resp_ok.status_code == 200
        body = resp_ok.get_json()
        assert body["total"] >= 1
        assert body["items"][0]["ruleset_id"] == str(a["ruleset_id"])
        assert body["items"][0].get("scale_max") is not None

    def test_recalculate_endpoint_and_reject_school_id(self, client, app, results_ctx):
        a = results_ctx["a"]
        headers = _auth(app, a["admin_id"])
        bad = client.post(
            "/api/notes/resultats/recalculer",
            headers=headers,
            json={
                "id_eleve": str(a["eleve_id"]),
                "id_classe": str(a["classe_id"]),
                "id_period": str(a["period_id"]),
                "school_id": str(a["school_id"]),
            },
        )
        assert bad.status_code == 400

        ok = client.post(
            "/api/notes/resultats/recalculer",
            headers=headers,
            json={
                "id_eleve": str(a["eleve_id"]),
                "id_classe": str(a["classe_id"]),
                "id_period": str(a["period_id"]),
            },
        )
        assert ok.status_code == 200
        data = ok.get_json()
        assert data["total"] == 1
        assert float(data["items"][0]["results"][0]["moyenne"]) == pytest.approx(13.60, abs=0.01)

    def test_note_batch_marks_stale_via_api(self, client, app, db, results_ctx):
        a = results_ctx["a"]
        with _auth_ctx(app, a["admin_id"]):
            from flask_jwt_extended import verify_jwt_in_request

            verify_jwt_in_request()
            refresh_moyenne_matiere_view(db)
            persist_student_period_results(
                db,
                id_eleve=a["eleve_id"],
                id_classe=a["classe_id"],
                id_period=a["period_id"],
            )
            db.commit()

        resp = client.post(
            f"/api/notes/evaluations/{a["ev_devoir_id"]}/notes",
            headers=_auth(app, a["admin_id"]),
            json={
                "notes": [
                    {
                        "id_eleve": str(a["eleve_id"]),
                        "valeur_note": 10,
                        "absent": False,
                    }
                ]
            },
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body.get("results_stale") is True
        assert body.get("id_classe") == str(a["classe_id"])
        assert body.get("id_period") == str(a["period_id"])
        row = (
            db.query(AcademicSubjectResult)
            .filter(
                AcademicSubjectResult.school_id == a["school_id"],
                AcademicSubjectResult.id_eleve == a["eleve_id"],
                AcademicSubjectResult.id_matiere == a["math_id"],
            )
            .one()
        )
        assert row.is_stale is True
