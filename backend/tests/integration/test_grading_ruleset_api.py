"""PR #12 Step 3 — API Grading Rulesets (CRUD, workflow, resolve, tenant, RBAC)."""
from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.auth.jwt_handler import hash_password
from app.models import (
    AnneeScolaire,
    Classe,
    Etablissement,
    EvaluationType,
    GradingRuleComponent,
    GradingRuleset,
    JournalAudit,
    Matiere,
    NiveauEtude,
    School,
    Utilisateur,
)
from app.services.academic import get_or_create_general_program
from app.services.evaluation_types import ensure_system_evaluation_types


def _auth(client, email: str, password: str = "Admin123!") -> dict:
    resp = client.post("/api/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.get_json()
    return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}


@pytest.fixture
def grading_api_pair(db):
    """Deux écoles avec admin, année, programme, niveau, classe, matière, types."""
    out = {}
    for key, code, name in (("a", "GRAPI-A", "École Grading API A"), ("b", "GRAPI-B", "École Grading API B")):
        school = db.query(School).filter(School.code == code).first()
        if not school:
            school = School(id=uuid.uuid4(), name=name, code=code, is_active=True)
            db.add(school)
            db.flush()
        ensure_system_evaluation_types(db, school.id)
        program = get_or_create_general_program(db, school.id)
        if not db.query(Etablissement).filter(Etablissement.school_id == school.id).first():
            db.add(
                Etablissement(
                    id=uuid.uuid4(),
                    school_id=school.id,
                    nom=name,
                    format_matricule="{ANNEE}M-{SEQ}",
                )
            )
        annee = (
            db.query(AnneeScolaire)
            .filter(AnneeScolaire.school_id == school.id, AnneeScolaire.libelle == "2025-2026")
            .first()
        )
        if not annee:
            annee = AnneeScolaire(
                id=uuid.uuid4(),
                school_id=school.id,
                libelle="2025-2026",
                date_debut=date(2025, 9, 1),
                date_fin=date(2026, 6, 30),
                est_active=True,
            )
            db.add(annee)
            db.flush()
        niveau = (
            db.query(NiveauEtude)
            .filter(
                NiveauEtude.school_id == school.id,
                NiveauEtude.libelle == "2nde",
                NiveauEtude.id_program == program.id,
            )
            .first()
        )
        if not niveau:
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
        classe = (
            db.query(Classe)
            .filter(
                Classe.school_id == school.id,
                Classe.libelle == "2nde A",
                Classe.id_annee == annee.id,
            )
            .first()
        )
        if not classe:
            classe = Classe(
                id=uuid.uuid4(),
                school_id=school.id,
                id_niveau=niveau.id,
                id_annee=annee.id,
                id_program=program.id,
                libelle="2nde A",
            )
            db.add(classe)
            db.flush()
        math = (
            db.query(Matiere)
            .filter(Matiere.school_id == school.id, Matiere.code == "MATH")
            .first()
        )
        if not math:
            math = Matiere(
                id=uuid.uuid4(),
                school_id=school.id,
                libelle="Mathématiques",
                code="MATH",
            )
            db.add(math)
            db.flush()
        fr = (
            db.query(Matiere)
            .filter(Matiere.school_id == school.id, Matiere.code == "FR")
            .first()
        )
        if not fr:
            fr = Matiere(
                id=uuid.uuid4(),
                school_id=school.id,
                libelle="Français",
                code="FR",
            )
            db.add(fr)
            db.flush()
        email = f"admin-{code.lower()}@grapi.test"
        user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
        if not user:
            user = Utilisateur(
                id=uuid.uuid4(),
                nom="Admin",
                prenom=key.upper(),
                email=email,
                mot_de_passe_hash=hash_password("Admin123!"),
                role="administrateur",
                actif=True,
                doit_changer_mdp=False,
                school_id=school.id,
            )
            db.add(user)
        else:
            user.mot_de_passe_hash = hash_password("Admin123!")
            user.role = "administrateur"
            user.actif = True
            user.school_id = school.id

        teacher_email = f"teacher-{code.lower()}@grapi.test"
        teacher = db.query(Utilisateur).filter(Utilisateur.email == teacher_email).first()
        if not teacher:
            teacher = Utilisateur(
                id=uuid.uuid4(),
                nom="Teacher",
                prenom=key.upper(),
                email=teacher_email,
                mot_de_passe_hash=hash_password("Admin123!"),
                role="enseignant",
                actif=True,
                doit_changer_mdp=False,
                school_id=school.id,
            )
            db.add(teacher)

        out[key] = {
            "school": school,
            "program": program,
            "annee": annee,
            "niveau": niveau,
            "classe": classe,
            "math": math,
            "fr": fr,
            "email": email,
            "teacher_email": teacher_email,
            "user": user,
        }
    # Isolation inter-tests (commits précédents) : reset rulesets des écoles fixture
    school_ids = [out["a"]["school"].id, out["b"]["school"].id]
    db.query(GradingRuleComponent).filter(GradingRuleComponent.school_id.in_(school_ids)).delete(
        synchronize_session=False
    )
    db.query(GradingRuleset).filter(GradingRuleset.school_id.in_(school_ids)).delete(
        synchronize_session=False
    )
    db.commit()
    return out


def _et(db, school_id, code="devoir"):
    return (
        db.query(EvaluationType)
        .filter(EvaluationType.school_id == school_id, EvaluationType.code == code)
        .one()
    )


def _create_payload(ctx, *, code=None, with_components=True, **extra):
    code = code or f"RS-{uuid.uuid4().hex[:8].upper()}"
    payload = {
        "code": code,
        "name": extra.pop("name", "Règles LDC"),
        "academic_year_id": str(ctx["annee"].id),
        "program_id": str(ctx["program"].id),
        "scale_max": "20.00",
        "rounding_mode": "half_up",
        "rounding_precision": 2,
    }
    payload.update(extra)
    return payload, code


def _comps_60_40(db, school_id):
    d = _et(db, school_id, "devoir")
    c = _et(db, school_id, "composition")
    return [
        {
            "code": "DEV",
            "label": "Devoirs",
            "evaluation_type_id": str(d.id),
            "weight": "60.00",
            "sequence": 1,
        },
        {
            "code": "COMP",
            "label": "Composition",
            "evaluation_type_id": str(c.id),
            "weight": "40.00",
            "sequence": 2,
        },
    ]


class TestGradingRulesetCrud:
    def test_create_list_get(self, client, db, grading_api_pair):
        a = grading_api_pair["a"]
        h = _auth(client, a["email"])
        payload, code = _create_payload(a)
        payload["components"] = _comps_60_40(db, a["school"].id)
        resp = client.post("/api/grading-rulesets", json=payload, headers=h)
        assert resp.status_code == 201, resp.get_json()
        body = resp.get_json()
        assert body["status"] == "draft"
        assert body["version"] == 1
        assert body["code"] == code
        assert len(body["components"]) == 2
        rid = body["id"]

        listed = client.get("/api/grading-rulesets", headers=h)
        assert listed.status_code == 200
        data = listed.get_json()
        assert "items" in data and "pagination" in data
        assert any(i["id"] == rid for i in data["items"])
        # List without full components payload
        item = next(i for i in data["items"] if i["id"] == rid)
        assert "components" not in item
        assert item["components_count"] == 2

        detail = client.get(f"/api/grading-rulesets/{rid}", headers=h)
        assert detail.status_code == 200
        assert len(detail.get_json()["components"]) == 2

    def test_create_rejects_forced_active_and_school_id(self, client, db, grading_api_pair):
        a = grading_api_pair["a"]
        h = _auth(client, a["email"])
        payload, _ = _create_payload(a)
        payload["status"] = "active"
        payload["school_id"] = str(grading_api_pair["b"]["school"].id)
        resp = client.post("/api/grading-rulesets", json=payload, headers=h)
        assert resp.status_code == 400
        err = resp.get_json()["error"]["code"]
        assert err in ("INVALID_RULESET_STATUS", "BAD_REQUEST")

    def test_create_rejects_class_period_axes(self, client, db, grading_api_pair):
        a = grading_api_pair["a"]
        h = _auth(client, a["email"])
        payload, _ = _create_payload(a, class_id=str(a["classe"].id))
        resp = client.post("/api/grading-rulesets", json=payload, headers=h)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_RULESET_SCOPE"

    def test_patch_draft_then_forbid_active(self, client, db, grading_api_pair):
        a = grading_api_pair["a"]
        h = _auth(client, a["email"])
        payload, _ = _create_payload(a)
        payload["components"] = _comps_60_40(db, a["school"].id)
        rid = client.post("/api/grading-rulesets", json=payload, headers=h).get_json()["id"]
        patch = client.patch(
            f"/api/grading-rulesets/{rid}",
            json={"name": "Renommé"},
            headers=h,
        )
        assert patch.status_code == 200
        assert patch.get_json()["name"] == "Renommé"

        act = client.post(f"/api/grading-rulesets/{rid}/activate", headers=h)
        assert act.status_code == 200
        assert act.get_json()["status"] == "active"

        bad = client.patch(
            f"/api/grading-rulesets/{rid}",
            json={"name": "Hack"},
            headers=h,
        )
        assert bad.status_code == 409
        assert bad.get_json()["error"]["code"] == "INVALID_RULESET_STATUS"


class TestGradingComponents:
    def test_component_crud_and_negative_weight(self, client, db, grading_api_pair):
        a = grading_api_pair["a"]
        h = _auth(client, a["email"])
        payload, _ = _create_payload(a)
        rid = client.post("/api/grading-rulesets", json=payload, headers=h).get_json()["id"]
        devoir = _et(db, a["school"].id, "devoir")
        bad = client.post(
            f"/api/grading-rulesets/{rid}/components",
            json={
                "code": "X",
                "label": "Bad",
                "evaluation_type_id": str(devoir.id),
                "weight": "-20",
                "sequence": 1,
            },
            headers=h,
        )
        assert bad.status_code == 400
        assert bad.get_json()["error"]["code"] == "INVALID_WEIGHT"

        ok = client.post(
            f"/api/grading-rulesets/{rid}/components",
            json={
                "code": "DEV",
                "label": "Devoirs",
                "evaluation_type_id": str(devoir.id),
                "weight": "100.00",
                "sequence": 1,
            },
            headers=h,
        )
        assert ok.status_code == 201
        cid = ok.get_json()["id"]
        patched = client.patch(
            f"/api/grading-rulesets/{rid}/components/{cid}",
            json={"weight": "50.00"},
            headers=h,
        )
        assert patched.status_code == 200
        assert patched.get_json()["weight"] == "50.00"
        deleted = client.delete(f"/api/grading-rulesets/{rid}/components/{cid}", headers=h)
        assert deleted.status_code == 200
        assert deleted.get_json()["deleted"] is True

    def test_invalid_evaluation_type(self, client, db, grading_api_pair):
        a, b = grading_api_pair["a"], grading_api_pair["b"]
        h = _auth(client, a["email"])
        payload, _ = _create_payload(a)
        rid = client.post("/api/grading-rulesets", json=payload, headers=h).get_json()["id"]
        et_b = _et(db, b["school"].id, "devoir")
        resp = client.post(
            f"/api/grading-rulesets/{rid}/components",
            json={
                "code": "DEV",
                "label": "Devoirs",
                "evaluation_type_id": str(et_b.id),
                "weight": "100",
                "sequence": 1,
            },
            headers=h,
        )
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "INVALID_EVALUATION_TYPE"


class TestGradingWorkflow:
    def test_activate_requires_weight_sum_100(self, client, db, grading_api_pair):
        a = grading_api_pair["a"]
        h = _auth(client, a["email"])
        payload, _ = _create_payload(a)
        devoir = _et(db, a["school"].id, "devoir")
        composition = _et(db, a["school"].id, "composition")
        payload["components"] = [
            {
                "code": "DEV",
                "label": "Devoirs",
                "evaluation_type_id": str(devoir.id),
                "weight": "60.00",
                "sequence": 1,
            },
            {
                "code": "COMP",
                "label": "Composition",
                "evaluation_type_id": str(composition.id),
                "weight": "30.00",
                "sequence": 2,
            },
        ]
        rid = client.post("/api/grading-rulesets", json=payload, headers=h).get_json()["id"]
        resp = client.post(f"/api/grading-rulesets/{rid}/activate", headers=h)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_WEIGHT_SUM"

    def test_activate_archive_and_invalid_transitions(self, client, db, grading_api_pair):
        a = grading_api_pair["a"]
        h = _auth(client, a["email"])
        payload, _ = _create_payload(a)
        payload["components"] = _comps_60_40(db, a["school"].id)
        rid = client.post("/api/grading-rulesets", json=payload, headers=h).get_json()["id"]
        assert client.post(f"/api/grading-rulesets/{rid}/activate", headers=h).status_code == 200
        again = client.post(f"/api/grading-rulesets/{rid}/activate", headers=h)
        assert again.status_code == 409
        assert again.get_json()["error"]["code"] == "RULESET_ALREADY_ACTIVE"

        assert client.post(f"/api/grading-rulesets/{rid}/archive", headers=h).status_code == 200
        arch_again = client.post(f"/api/grading-rulesets/{rid}/archive", headers=h)
        assert arch_again.status_code == 409
        assert arch_again.get_json()["error"]["code"] == "RULESET_ALREADY_ARCHIVED"

        reactivate = client.post(f"/api/grading-rulesets/{rid}/activate", headers=h)
        assert reactivate.status_code == 409
        assert reactivate.get_json()["error"]["code"] == "INVALID_RULESET_STATUS"

    def test_activate_archives_same_code_previous_active(self, client, db, grading_api_pair):
        a = grading_api_pair["a"]
        h = _auth(client, a["email"])
        code = f"LDC-{uuid.uuid4().hex[:6].upper()}"
        p1, _ = _create_payload(a, code=code)
        p1["components"] = _comps_60_40(db, a["school"].id)
        id1 = client.post("/api/grading-rulesets", json=p1, headers=h).get_json()["id"]
        assert client.post(f"/api/grading-rulesets/{id1}/activate", headers=h).status_code == 200

        p2, _ = _create_payload(a, code=code)
        p2["components"] = _comps_60_40(db, a["school"].id)
        id2 = client.post("/api/grading-rulesets", json=p2, headers=h).get_json()["id"]
        assert client.get(f"/api/grading-rulesets/{id2}", headers=h).get_json()["version"] == 2
        assert client.post(f"/api/grading-rulesets/{id2}/activate", headers=h).status_code == 200
        assert client.get(f"/api/grading-rulesets/{id1}", headers=h).get_json()["status"] == "archived"
        assert client.get(f"/api/grading-rulesets/{id2}", headers=h).get_json()["status"] == "active"

    def test_activate_conflict_same_scope_different_code(self, client, db, grading_api_pair):
        a = grading_api_pair["a"]
        h = _auth(client, a["email"])
        for code in ("SCOPE-A", "SCOPE-B"):
            p, _ = _create_payload(a, code=f"{code}-{uuid.uuid4().hex[:4]}")
            p["program_id"] = str(a["program"].id)
            p["components"] = _comps_60_40(db, a["school"].id)
            rid = client.post("/api/grading-rulesets", json=p, headers=h).get_json()["id"]
            if code == "SCOPE-A":
                assert client.post(f"/api/grading-rulesets/{rid}/activate", headers=h).status_code == 200
            else:
                resp = client.post(f"/api/grading-rulesets/{rid}/activate", headers=h)
                assert resp.status_code == 409
                assert resp.get_json()["error"]["code"] == "RULESET_CONFLICT"


class TestGradingResolveApi:
    def test_resolve_school_and_program_override(self, client, db, grading_api_pair):
        a = grading_api_pair["a"]
        h = _auth(client, a["email"])
        # school default (program null)
        school_p, _ = _create_payload(a, code=f"SCH-{uuid.uuid4().hex[:6]}")
        school_p.pop("program_id", None)
        school_p["components"] = _comps_60_40(db, a["school"].id)
        sid = client.post("/api/grading-rulesets", json=school_p, headers=h).get_json()["id"]
        assert client.post(f"/api/grading-rulesets/{sid}/activate", headers=h).status_code == 200

        prog_p, _ = _create_payload(a, code=f"PRG-{uuid.uuid4().hex[:6]}")
        # 50/50 for program
        d = _et(db, a["school"].id, "devoir")
        c = _et(db, a["school"].id, "composition")
        prog_p["components"] = [
            {
                "code": "DEV",
                "label": "Devoirs",
                "evaluation_type_id": str(d.id),
                "weight": "50.00",
                "sequence": 1,
            },
            {
                "code": "COMP",
                "label": "Composition",
                "evaluation_type_id": str(c.id),
                "weight": "50.00",
                "sequence": 2,
            },
        ]
        pid = client.post("/api/grading-rulesets", json=prog_p, headers=h).get_json()["id"]
        assert client.post(f"/api/grading-rulesets/{pid}/activate", headers=h).status_code == 200

        resolved = client.post(
            "/api/grading-rulesets/resolve",
            json={
                "academic_year_id": str(a["annee"].id),
                "program_id": str(a["program"].id),
                "subject_id": str(a["math"].id),
                "diagnostic": True,
            },
            headers=h,
        )
        assert resolved.status_code == 200, resolved.get_json()
        body = resolved.get_json()
        assert body["ruleset"]["id"] == pid
        assert body["components"][0]["weight"] == "50.00"
        assert "diagnostic" in body
        assert body["diagnostic"]["selected"]["ruleset_id"] == pid

    def test_resolve_no_ruleset(self, client, db, grading_api_pair):
        a = grading_api_pair["a"]
        h = _auth(client, a["email"])
        resp = client.post(
            "/api/grading-rulesets/resolve",
            json={
                "academic_year_id": str(a["annee"].id),
                "program_id": str(a["program"].id),
                "subject_id": str(a["fr"].id),
            },
            headers=h,
        )
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NO_RULESET"

    def test_resolve_subject_override(self, client, db, grading_api_pair):
        a = grading_api_pair["a"]
        h = _auth(client, a["email"])
        base, _ = _create_payload(a, code=f"BASE-{uuid.uuid4().hex[:6]}")
        base["components"] = _comps_60_40(db, a["school"].id)
        # change to 50/50
        d = _et(db, a["school"].id, "devoir")
        c = _et(db, a["school"].id, "composition")
        base["components"] = [
            {
                "code": "DEV",
                "label": "Devoirs",
                "evaluation_type_id": str(d.id),
                "weight": "50.00",
                "sequence": 1,
            },
            {
                "code": "COMP",
                "label": "Composition",
                "evaluation_type_id": str(c.id),
                "weight": "50.00",
                "sequence": 2,
            },
        ]
        bid = client.post("/api/grading-rulesets", json=base, headers=h).get_json()["id"]
        assert client.post(f"/api/grading-rulesets/{bid}/activate", headers=h).status_code == 200

        math_p, _ = _create_payload(a, code=f"MATH-{uuid.uuid4().hex[:6]}")
        math_p["subject_id"] = str(a["math"].id)
        math_p["components"] = _comps_60_40(db, a["school"].id)
        mid = client.post("/api/grading-rulesets", json=math_p, headers=h).get_json()["id"]
        assert client.post(f"/api/grading-rulesets/{mid}/activate", headers=h).status_code == 200

        math_r = client.post(
            "/api/grading-rulesets/resolve",
            json={
                "academic_year_id": str(a["annee"].id),
                "program_id": str(a["program"].id),
                "subject_id": str(a["math"].id),
            },
            headers=h,
        ).get_json()
        fr_r = client.post(
            "/api/grading-rulesets/resolve",
            json={
                "academic_year_id": str(a["annee"].id),
                "program_id": str(a["program"].id),
                "subject_id": str(a["fr"].id),
            },
            headers=h,
        ).get_json()
        assert math_r["ruleset"]["id"] == mid
        assert fr_r["ruleset"]["id"] == bid


class TestGradingTenantSecurity:
    def test_cross_tenant_404(self, client, db, grading_api_pair):
        a, b = grading_api_pair["a"], grading_api_pair["b"]
        ha, hb = _auth(client, a["email"]), _auth(client, b["email"])
        payload, _ = _create_payload(b)
        payload["components"] = _comps_60_40(db, b["school"].id)
        rid = client.post("/api/grading-rulesets", json=payload, headers=hb).get_json()["id"]

        assert client.get(f"/api/grading-rulesets/{rid}", headers=ha).status_code == 404
        assert client.patch(
            f"/api/grading-rulesets/{rid}", json={"name": "X"}, headers=ha
        ).status_code == 404
        assert client.post(f"/api/grading-rulesets/{rid}/activate", headers=ha).status_code == 404
        assert client.post(f"/api/grading-rulesets/{rid}/archive", headers=ha).status_code == 404

        # resolve with B resources as A → invalid context
        resp = client.post(
            "/api/grading-rulesets/resolve",
            json={
                "academic_year_id": str(b["annee"].id),
                "program_id": str(b["program"].id),
            },
            headers=ha,
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_ACADEMIC_CONTEXT"

    def test_rbac_teacher_read_not_write(self, client, db, grading_api_pair):
        a = grading_api_pair["a"]
        admin = _auth(client, a["email"])
        teacher = _auth(client, a["teacher_email"])
        payload, _ = _create_payload(a)
        payload["components"] = _comps_60_40(db, a["school"].id)
        rid = client.post("/api/grading-rulesets", json=payload, headers=admin).get_json()["id"]

        assert client.get(f"/api/grading-rulesets/{rid}", headers=teacher).status_code == 200
        assert client.get("/api/evaluation-types", headers=teacher).status_code == 200
        assert client.post("/api/grading-rulesets", json=payload, headers=teacher).status_code == 403
        assert client.post(f"/api/grading-rulesets/{rid}/activate", headers=teacher).status_code == 403

    def test_invalid_scope_level_other_program(self, client, db, grading_api_pair):
        a = grading_api_pair["a"]
        h = _auth(client, a["email"])
        # Create technical program + level
        tech = client.post(
            "/api/etablissement/programs",
            json={"code": f"TECH-{uuid.uuid4().hex[:4]}", "name": "Technique", "program_type": "technique"},
            headers=h,
        )
        assert tech.status_code == 201
        tech_id = tech.get_json()["id"]
        # niveau belongs to GENERAL — use with TECH program
        payload, _ = _create_payload(a)
        payload["program_id"] = tech_id
        payload["level_id"] = str(a["niveau"].id)
        resp = client.post("/api/grading-rulesets", json=payload, headers=h)
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_RULESET_SCOPE"


class TestGradingAudit:
    def test_create_activate_audited(self, client, db, grading_api_pair):
        a = grading_api_pair["a"]
        h = _auth(client, a["email"])
        payload, _ = _create_payload(a)
        payload["components"] = _comps_60_40(db, a["school"].id)
        rid = client.post("/api/grading-rulesets", json=payload, headers=h).get_json()["id"]
        client.post(f"/api/grading-rulesets/{rid}/activate", headers=h)
        actions = {
            row.action
            for row in db.query(JournalAudit)
            .filter(JournalAudit.school_id == a["school"].id)
            .all()
        }
        assert "GRADING_RULESET_CREATED" in actions
        assert "GRADING_RULESET_ACTIVATED" in actions
