"""PR #11 étape 2 — API Programs / Periodes / façade trimestres + isolation tenant."""
from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.auth.jwt_handler import hash_password
from app.models import (
    PROGRAM_CODE_GENERAL,
    AnneeScolaire,
    Classe,
    Etablissement,
    NiveauEtude,
    School,
    Utilisateur,
)
from app.services.academic import get_or_create_general_program


def _auth(client, email: str, password: str = "Admin123!") -> dict:
    resp = client.post("/api/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.get_json()
    return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}


@pytest.fixture
def api_school_pair(db):
    """Deux écoles complètes pour tests API étape 2."""
    out = {}
    for key, code, name in (("a", "API11-A", "École API A"), ("b", "API11-B", "École API B")):
        school = db.query(School).filter(School.code == code).first()
        if not school:
            school = School(id=uuid.uuid4(), name=name, code=code, is_active=True)
            db.add(school)
            db.flush()
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
                NiveauEtude.libelle == "6ème",
                NiveauEtude.id_program == program.id,
            )
            .first()
        )
        if not niveau:
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
        classe = (
            db.query(Classe)
            .filter(
                Classe.school_id == school.id,
                Classe.libelle == "6ème A",
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
                libelle="6ème A",
            )
            db.add(classe)
            db.flush()
        email = f"admin-{code.lower()}@api11.test"
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
            user.actif = True
            user.school_id = school.id
        out[key] = {
            "school": school,
            "program": program,
            "annee": annee,
            "niveau": niveau,
            "classe": classe,
            "email": email,
            "user": user,
        }
    db.commit()
    return out


class TestProgramApi:
    def test_create_read_update_deactivate(self, client, api_school_pair):
        ha = _auth(client, api_school_pair["a"]["email"])
        suffix = uuid.uuid4().hex[:6]
        create = client.post(
            "/api/etablissement/programs",
            headers=ha,
            json={
                "code": f"LDC-G-{suffix}",
                "name": "LDC Général",
                "description": "Filière générale",
                "program_type": "general",
                "period_type_default": "trimestre",
            },
        )
        assert create.status_code == 201, create.get_json()
        body = create.get_json()
        assert body["code"] == f"LDC-G-{suffix}".upper()
        assert body["levels_count"] == 0
        pid = body["id"]

        detail = client.get(f"/api/etablissement/programs/{pid}", headers=ha)
        assert detail.status_code == 200
        assert detail.get_json()["name"] == "LDC Général"

        patch = client.patch(
            f"/api/etablissement/programs/{pid}",
            headers=ha,
            json={"name": "LDC Général (maj)"},
        )
        assert patch.status_code == 200
        assert patch.get_json()["name"] == "LDC Général (maj)"

        deact = client.post(f"/api/etablissement/programs/{pid}/deactivate", headers=ha)
        assert deact.status_code == 200
        assert deact.get_json()["is_active"] is False

    def test_duplicate_code_conflict(self, client, api_school_pair):
        ha = _auth(client, api_school_pair["a"]["email"])
        code = f"DUP-{uuid.uuid4().hex[:6]}"
        r1 = client.post(
            "/api/etablissement/programs",
            headers=ha,
            json={"code": code, "name": "One"},
        )
        assert r1.status_code == 201
        r2 = client.post(
            "/api/etablissement/programs",
            headers=ha,
            json={"code": code, "name": "Two"},
        )
        assert r2.status_code == 409

    def test_reject_client_school_id_spoof(self, client, api_school_pair):
        ha = _auth(client, api_school_pair["a"]["email"])
        resp = client.post(
            "/api/etablissement/programs",
            headers=ha,
            json={
                "code": f"SPOOF-{uuid.uuid4().hex[:6]}",
                "name": "Spoof",
                "school_id": str(api_school_pair["b"]["school"].id),
            },
        )
        assert resp.status_code == 400

    def test_cannot_deactivate_general(self, client, api_school_pair):
        ha = _auth(client, api_school_pair["a"]["email"])
        listed = client.get("/api/etablissement/programs", headers=ha)
        assert listed.status_code == 200
        general = next(p for p in listed.get_json()["items"] if p["code"] == PROGRAM_CODE_GENERAL)
        resp = client.post(
            f"/api/etablissement/programs/{general['id']}/deactivate",
            headers=ha,
        )
        assert resp.status_code == 409

    def test_teacher_cannot_create(self, client, db, api_school_pair):
        email = f"teacher-{uuid.uuid4().hex[:6]}@api11.test"
        db.add(
            Utilisateur(
                id=uuid.uuid4(),
                nom="Prof",
                prenom="Test",
                email=email,
                mot_de_passe_hash=hash_password("Teacher123!"),
                role="enseignant",
                actif=True,
                school_id=api_school_pair["a"]["school"].id,
            )
        )
        db.commit()
        ht = _auth(client, email, "Teacher123!")
        resp = client.post(
            "/api/etablissement/programs",
            headers=ht,
            json={"code": "X", "name": "X"},
        )
        assert resp.status_code == 403


class TestPeriodApi:
    def test_create_t1_to_t4_and_semestre_custom(self, client, api_school_pair):
        a = api_school_pair["a"]
        ha = _auth(client, a["email"])
        # create dedicated program for custom periods
        prog = client.post(
            "/api/etablissement/programs",
            headers=ha,
            json={
                "code": f"TECH-{uuid.uuid4().hex[:6]}",
                "name": "Technique",
                "program_type": "technique",
                "period_type_default": "semestre",
            },
        ).get_json()

        for seq in (1, 2, 3, 4):
            r = client.post(
                "/api/etablissement/periodes",
                headers=ha,
                json={
                    "id_annee": str(a["annee"].id),
                    "id_program": prog["id"],
                    "sequence": seq,
                    "period_type": "trimestre",
                    "date_debut": "2025-09-01",
                    "date_fin": "2025-12-20",
                },
            )
            assert r.status_code == 201, r.get_json()
            assert r.get_json()["sequence"] == seq
            assert r.get_json()["code"] == f"T{seq}"

        s1 = client.post(
            "/api/etablissement/periodes",
            headers=ha,
            json={
                "id_annee": str(a["annee"].id),
                "id_program": prog["id"],
                "sequence": 10,
                "period_type": "semestre",
                "date_debut": "2025-09-01",
                "date_fin": "2026-01-31",
            },
        )
        assert s1.status_code == 201
        assert s1.get_json()["code"] == "S10"

        c1 = client.post(
            "/api/etablissement/periodes",
            headers=ha,
            json={
                "id_annee": str(a["annee"].id),
                "id_program": prog["id"],
                "sequence": 11,
                "period_type": "custom",
                "date_debut": "2026-02-01",
                "date_fin": "2026-03-01",
            },
        )
        assert c1.status_code == 201
        assert c1.get_json()["code"] == "P11"

    def test_duplicate_sequence_and_invalid_dates(self, client, api_school_pair):
        a = api_school_pair["a"]
        ha = _auth(client, a["email"])
        base = {
            "id_annee": str(a["annee"].id),
            "id_program": str(a["program"].id),
            "sequence": int(uuid.uuid4().int % 9000) + 100,
            "period_type": "trimestre",
            "date_debut": "2025-09-01",
            "date_fin": "2025-12-01",
        }
        assert client.post("/api/etablissement/periodes", headers=ha, json=base).status_code == 201
        assert client.post("/api/etablissement/periodes", headers=ha, json=base).status_code == 409

        bad_dates = {
            **base,
            "sequence": base["sequence"] + 1,
            "date_debut": "2025-12-01",
            "date_fin": "2025-09-01",
        }
        assert (
            client.post("/api/etablissement/periodes", headers=ha, json=bad_dates).status_code
            == 400
        )

    def test_cross_school_year_program_rejected(self, client, api_school_pair):
        a, b = api_school_pair["a"], api_school_pair["b"]
        ha = _auth(client, a["email"])
        resp = client.post(
            "/api/etablissement/periodes",
            headers=ha,
            json={
                "id_annee": str(a["annee"].id),
                "id_program": str(b["program"].id),
                "sequence": 1,
                "date_debut": "2025-09-01",
                "date_fin": "2025-12-20",
            },
        )
        assert resp.status_code == 404


class TestLegacyTrimestresFacade:
    def test_trimestres_use_same_service_numero_from_sequence(self, client, api_school_pair):
        a = api_school_pair["a"]
        ha = _auth(client, a["email"])
        created = client.post(
            "/api/etablissement/trimestres",
            headers=ha,
            json={
                "id_annee": str(a["annee"].id),
                "numero": int(uuid.uuid4().int % 8000) + 100,
                "date_debut": "2025-09-01",
                "date_fin": "2025-10-01",
            },
        )
        assert created.status_code == 201, created.get_json()
        body = created.get_json()
        assert body["numero"] >= 1
        assert "id" in body

        listed = client.get(
            f"/api/etablissement/trimestres?id_annee={a['annee'].id}",
            headers=ha,
        )
        assert listed.status_code == 200
        ids = {row["id"] for row in listed.get_json()}
        assert body["id"] in ids

        periods = client.get(
            f"/api/etablissement/periodes?id_annee={a['annee'].id}"
            f"&id_program={a['program'].id}&per_page=100",
            headers=ha,
        )
        assert periods.status_code == 200
        seqs = {p["sequence"] for p in periods.get_json()["items"]}
        assert body["numero"] in seqs


class TestNiveauClasseProgram:
    def test_homonymous_levels_two_programs(self, client, api_school_pair):
        a = api_school_pair["a"]
        ha = _auth(client, a["email"])
        tech = client.post(
            "/api/etablissement/programs",
            headers=ha,
            json={"code": f"TECH-{uuid.uuid4().hex[:6]}", "name": "Tech"},
        ).get_json()
        label = f"Première-{uuid.uuid4().hex[:6]}"
        n1 = client.post(
            "/api/etablissement/niveaux",
            headers=ha,
            json={
                "libelle": label,
                "ordre": 6,
                "cycle": "second",
                "id_program": str(a["program"].id),
            },
        )
        n2 = client.post(
            "/api/etablissement/niveaux",
            headers=ha,
            json={
                "libelle": label,
                "ordre": 6,
                "cycle": "second",
                "id_program": tech["id"],
            },
        )
        assert n1.status_code == 201, n1.get_json()
        assert n2.status_code == 201, n2.get_json()
        assert n1.get_json()["id"] != n2.get_json()["id"]

    def test_niveau_update_program(self, client, api_school_pair):
        a = api_school_pair["a"]
        ha = _auth(client, a["email"])
        tech = client.post(
            "/api/etablissement/programs",
            headers=ha,
            json={"code": f"UPD-{uuid.uuid4().hex[:6]}", "name": "UpdateProg"},
        ).get_json()
        created = client.post(
            "/api/etablissement/niveaux",
            headers=ha,
            json={
                "libelle": f"NivU-{uuid.uuid4().hex[:4]}",
                "ordre": 2,
                "cycle": "premier",
                "id_program": str(a["program"].id),
            },
        )
        assert created.status_code == 201, created.get_json()
        nid = created.get_json()["id"]
        updated = client.put(
            f"/api/etablissement/niveaux/{nid}",
            headers=ha,
            json={
                "libelle": "2nde",
                "ordre": 3,
                "cycle": "second",
                "id_program": tech["id"],
            },
        )
        assert updated.status_code == 200, updated.get_json()
        body = updated.get_json()
        assert body["libelle"] == "2nde"
        assert body["id_program"] == tech["id"]
        assert body["cycle"] == "second"

    def test_level_wrong_tenant_program_rejected(self, client, api_school_pair):
        a, b = api_school_pair["a"], api_school_pair["b"]
        ha = _auth(client, a["email"])
        resp = client.post(
            "/api/etablissement/niveaux",
            headers=ha,
            json={
                "libelle": f"Bad-{uuid.uuid4().hex[:4]}",
                "cycle": "premier",
                "id_program": str(b["program"].id),
            },
        )
        assert resp.status_code == 404

    def test_class_program_mismatch_rejected(self, client, api_school_pair):
        a = api_school_pair["a"]
        ha = _auth(client, a["email"])
        tech = client.post(
            "/api/etablissement/programs",
            headers=ha,
            json={"code": f"MIS-{uuid.uuid4().hex[:6]}", "name": "Mismatch"},
        ).get_json()
        niveau = client.post(
            "/api/etablissement/niveaux",
            headers=ha,
            json={
                "libelle": f"Niv-{uuid.uuid4().hex[:4]}",
                "cycle": "premier",
                "id_program": str(a["program"].id),
            },
        ).get_json()
        resp = client.post(
            "/api/etablissement/classes",
            headers=ha,
            json={
                "id_niveau": niveau["id"],
                "id_annee": str(a["annee"].id),
                "libelle": f"Cls-{uuid.uuid4().hex[:4]}",
                "id_program": tech["id"],
            },
        )
        assert resp.status_code == 400, resp.get_json()


class TestTenantIsolationApi:
    def test_school_a_cannot_read_or_patch_program_b(self, client, api_school_pair):
        a, b = api_school_pair["a"], api_school_pair["b"]
        ha = _auth(client, a["email"])
        hb = _auth(client, b["email"])
        created = client.post(
            "/api/etablissement/programs",
            headers=hb,
            json={"code": f"BONLY-{uuid.uuid4().hex[:6]}", "name": "B Only"},
        )
        assert created.status_code == 201
        pid = created.get_json()["id"]

        assert client.get(f"/api/etablissement/programs/{pid}", headers=ha).status_code == 404
        assert (
            client.patch(
                f"/api/etablissement/programs/{pid}",
                headers=ha,
                json={"name": "Hacked"},
            ).status_code
            == 404
        )

    def test_school_a_cannot_read_period_b(self, client, api_school_pair):
        a, b = api_school_pair["a"], api_school_pair["b"]
        ha = _auth(client, a["email"])
        hb = _auth(client, b["email"])
        period = client.post(
            "/api/etablissement/periodes",
            headers=hb,
            json={
                "id_annee": str(b["annee"].id),
                "id_program": str(b["program"].id),
                "sequence": int(uuid.uuid4().int % 8000) + 200,
                "date_debut": "2025-09-01",
                "date_fin": "2025-12-01",
            },
        )
        assert period.status_code == 201, period.get_json()
        pid = period.get_json()["id"]
        assert client.get(f"/api/etablissement/periodes/{pid}", headers=ha).status_code == 404

    def test_school_a_cannot_use_level_b_for_class(self, client, api_school_pair):
        a, b = api_school_pair["a"], api_school_pair["b"]
        ha = _auth(client, a["email"])
        resp = client.post(
            "/api/etablissement/classes",
            headers=ha,
            json={
                "id_niveau": str(b["niveau"].id),
                "id_annee": str(a["annee"].id),
                "libelle": f"Hack-{uuid.uuid4().hex[:4]}",
            },
        )
        assert resp.status_code == 404
