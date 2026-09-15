"""PR #10 — SUPER_ADMIN, platform schools, onboarding, RBAC, inactive school."""
from __future__ import annotations

import uuid

import pytest
from flask_jwt_extended import decode_token

from app.auth.jwt_handler import hash_password
from app.models import Etablissement, JournalAudit, School, Utilisateur
from app.models.utilisateur import PLATFORM_ROLE_SUPER_ADMIN


@pytest.fixture
def super_admin(db):
    email = "super@platform.local"
    user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
    if not user:
        user = Utilisateur(
            id=uuid.uuid4(),
            nom="Super",
            prenom="Admin",
            email=email,
            role=PLATFORM_ROLE_SUPER_ADMIN,
            mot_de_passe_hash=hash_password("SuperAdmin123!"),
            actif=True,
            doit_changer_mdp=False,
            school_id=None,
        )
        db.add(user)
        db.commit()
    else:
        user.role = PLATFORM_ROLE_SUPER_ADMIN
        user.school_id = None
        user.mot_de_passe_hash = hash_password("SuperAdmin123!")
        user.actif = True
        user.doit_changer_mdp = False
        db.commit()
    return user


@pytest.fixture
def super_headers(client, super_admin):
    resp = client.post(
        "/api/login",
        json={"email": "super@platform.local", "password": "SuperAdmin123!"},
    )
    assert resp.status_code == 200, resp.get_json()
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _login(client, email, password="Admin123!"):
    resp = client.post("/api/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.get_json()
    return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}


class TestSuperAdminAuth:
    def test_super_admin_login(self, client, super_admin):
        resp = client.post(
            "/api/login",
            json={"email": "super@platform.local", "password": "SuperAdmin123!"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["user"]["role"] == "super_admin"
        assert data["user"]["school_id"] is None

    def test_admin_login(self, client, admin_user):
        resp = client.post(
            "/api/login",
            json={"email": "admin@ecole.local", "password": "Admin123!"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["user"]["role"] == "administrateur"
        assert resp.get_json()["user"]["school_id"] is not None


class TestPlatformRBAC:
    def test_admin_forbidden_on_platform_list(self, client, auth_headers):
        resp = client.get("/api/platform/schools", headers=auth_headers)
        assert resp.status_code == 403

    def test_super_admin_can_list(self, client, super_headers):
        resp = client.get("/api/platform/schools", headers=super_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert "items" in body or "data" in body or isinstance(body, dict)

    def test_cannot_promote_to_super_admin(self, client, auth_headers, admin_user, db):
        # Create a teacher in same school
        teacher = Utilisateur(
            id=uuid.uuid4(),
            nom="Prof",
            prenom="Test",
            email=f"prof-{uuid.uuid4().hex[:8]}@ecole.local",
            role="enseignant",
            mot_de_passe_hash=hash_password("Teacher123!"),
            actif=True,
            school_id=admin_user.school_id,
        )
        db.add(teacher)
        db.commit()
        resp = client.patch(
            f"/api/users/{teacher.id}",
            headers=auth_headers,
            json={"role": "super_admin"},
        )
        assert resp.status_code in (400, 403, 422)


class TestOnboarding:
    def test_onboard_atomic(self, client, super_headers, db):
        code = f"ONB-{uuid.uuid4().hex[:6].upper()}"
        email = f"admin-{uuid.uuid4().hex[:8]}@newschool.local"
        resp = client.post(
            "/api/platform/schools/onboard",
            headers=super_headers,
            json={
                "name": "Nouvelle École Test",
                "code": code,
                "city": "Ouagadougou",
                "country": "Burkina Faso",
                "admin_nom": "Koné",
                "admin_prenom": "Awa",
                "admin_email": email,
                "admin_password": "Admin12345!",
            },
        )
        assert resp.status_code == 201, resp.get_json()
        data = resp.get_json()
        school_id = data["school"]["id"]
        assert data["school"]["code"] == code
        assert data["school"]["is_active"] is True
        assert data["admin"]["role"] == "administrateur"
        assert data["admin"]["school_id"] == school_id

        school = db.query(School).filter(School.id == school_id).first()
        assert school is not None
        etab = db.query(Etablissement).filter(Etablissement.school_id == school_id).first()
        assert etab is not None
        assert etab.nom == "Nouvelle École Test"

        actions = {
            a.action
            for a in db.query(JournalAudit).filter(JournalAudit.school_id == school.id).all()
        }
        assert "SCHOOL_CREATED" in actions
        assert "ADMIN_CREATED" in actions

    def test_onboard_email_conflict_rollback(self, client, super_headers, admin_user, db):
        code = f"FAIL-{uuid.uuid4().hex[:6].upper()}"
        before = db.query(School).filter(School.code == code).count()
        resp = client.post(
            "/api/platform/schools/onboard",
            headers=super_headers,
            json={
                "name": "École Conflict",
                "code": code,
                "admin_nom": "X",
                "admin_prenom": "Y",
                "admin_email": admin_user.email,  # déjà pris
                "admin_password": "Admin12345!",
            },
        )
        assert resp.status_code == 409
        assert db.query(School).filter(School.code == code).count() == before

    def test_duplicate_code(self, client, super_headers, default_school):
        resp = client.post(
            "/api/platform/schools/onboard",
            headers=super_headers,
            json={
                "name": "Dup",
                "code": default_school.code,
                "admin_nom": "A",
                "admin_prenom": "B",
                "admin_email": f"dup-{uuid.uuid4().hex[:8]}@x.local",
                "admin_password": "Admin12345!",
            },
        )
        assert resp.status_code == 409


class TestSchoolLifecycle:
    def test_activate_deactivate(self, client, super_headers, db):
        code = f"LC-{uuid.uuid4().hex[:6].upper()}"
        onboard = client.post(
            "/api/platform/schools/onboard",
            headers=super_headers,
            json={
                "name": "Lifecycle School",
                "code": code,
                "admin_nom": "Admin",
                "admin_prenom": "LC",
                "admin_email": f"lc-{uuid.uuid4().hex[:8]}@school.local",
                "admin_password": "Admin12345!",
            },
        )
        school_id = onboard.get_json()["school"]["id"]
        admin_email = onboard.get_json()["admin"]["email"]

        de = client.post(f"/api/platform/schools/{school_id}/deactivate", headers=super_headers)
        assert de.status_code == 200
        assert de.get_json()["is_active"] is False

        # Admin école ne peut plus se connecter
        login = client.post("/api/login", json={"email": admin_email, "password": "Admin12345!"})
        assert login.status_code == 403

        # Super admin peut toujours gérer
        get_s = client.get(f"/api/platform/schools/{school_id}", headers=super_headers)
        assert get_s.status_code == 200

        ac = client.post(f"/api/platform/schools/{school_id}/activate", headers=super_headers)
        assert ac.status_code == 200
        assert ac.get_json()["is_active"] is True
        login2 = client.post("/api/login", json={"email": admin_email, "password": "Admin12345!"})
        assert login2.status_code == 200

    def test_update_school(self, client, super_headers, default_school):
        resp = client.patch(
            f"/api/platform/schools/{default_school.id}",
            headers=super_headers,
            json={"city": "Koudougou"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["city"] == "Koudougou"


class TestSchoolContextAndMetier:
    def test_metier_without_context_forbidden(self, client, super_headers):
        resp = client.get("/api/eleves", headers=super_headers)
        assert resp.status_code == 403

    def test_context_switch_allows_tenant_scope(self, client, super_headers, school_pair):
        # reuse fixture from true tenant isolation if available
        school_a = school_pair["A"]["school"]
        school_b = school_pair["B"]["school"]

        enter = client.put(
            "/api/platform/context/school",
            headers=super_headers,
            json={"school_id": str(school_a.id)},
        )
        assert enter.status_code == 200, enter.get_json()
        token = enter.get_json()["access_token"]
        claims = decode_token(token)
        assert claims.get("acting_school_id") == str(school_a.id)
        headers = {"Authorization": f"Bearer {token}"}

        list_a = client.get("/api/eleves", headers=headers)
        assert list_a.status_code == 200
        items = list_a.get_json().get("items") or list_a.get_json().get("data") or []
        ids = {str(e["id"]) for e in items}
        assert str(school_pair["A"]["eleve"].id) in ids
        assert str(school_pair["B"]["eleve"].id) not in ids

        # Switch to B
        enter_b = client.put(
            "/api/platform/context/school",
            headers=headers,
            json={"school_id": str(school_b.id)},
        )
        headers_b = {"Authorization": f"Bearer {enter_b.get_json()['access_token']}"}
        list_b = client.get("/api/eleves", headers=headers_b)
        items_b = list_b.get_json().get("items") or list_b.get_json().get("data") or []
        ids_b = {str(e["id"]) for e in items_b}
        assert str(school_pair["B"]["eleve"].id) in ids_b
        assert str(school_pair["A"]["eleve"].id) not in ids_b

        # Exit
        exit_r = client.delete("/api/platform/context/school", headers=headers_b)
        assert exit_r.status_code == 200
        headers_out = {"Authorization": f"Bearer {exit_r.get_json()['access_token']}"}
        assert client.get("/api/eleves", headers=headers_out).status_code == 403


class TestSecurity:
    def test_school_id_spoof_on_user_create(self, client, auth_headers, school_pair):
        other = school_pair["B"]["school"].id
        resp = client.post(
            "/api/users",
            headers=auth_headers,
            json={
                "nom": "Hack",
                "prenom": "User",
                "email": f"hack-{uuid.uuid4().hex[:8]}@ecole.local",
                "role": "enseignant",
                "password": "Hack12345!",
                "school_id": str(other),
            },
        )
        assert resp.status_code == 400

    def test_admin_cannot_access_other_school_users(self, client, auth_headers, school_pair, db):
        # Create admin on school B
        school_b = school_pair["B"]["school"]
        email = f"adminb-{uuid.uuid4().hex[:8]}@b.local"
        admin_b = Utilisateur(
            id=uuid.uuid4(),
            nom="Admin",
            prenom="B",
            email=email,
            role="administrateur",
            mot_de_passe_hash=hash_password("Admin123!"),
            actif=True,
            school_id=school_b.id,
        )
        db.add(admin_b)
        db.commit()
        headers_b = _login(client, email)
        # A admin listing users — only A
        list_a = client.get("/api/users", headers=auth_headers)
        assert list_a.status_code == 200
        emails = [u["email"] for u in (list_a.get_json().get("items") or list_a.get_json().get("data") or [])]
        assert email not in emails
        # B cannot patch A admin by id
        patch_cross = client.patch(
            f"/api/users/{school_pair['A']['admin'].id}",
            headers=headers_b,
            json={"nom": "Hacked"},
        )
        assert patch_cross.status_code == 404

    def test_last_admin_cannot_deactivate(self, client, db):
        code = f"LAST-{uuid.uuid4().hex[:6].upper()}"
        school = School(id=uuid.uuid4(), name="Seul Admin", code=code, is_active=True)
        db.add(school)
        db.flush()
        email = f"seul-{uuid.uuid4().hex[:8]}@school.local"
        admin = Utilisateur(
            id=uuid.uuid4(),
            nom="Seul",
            prenom="Admin",
            email=email,
            role="administrateur",
            mot_de_passe_hash=hash_password("Admin123!"),
            actif=True,
            school_id=school.id,
        )
        db.add(admin)
        db.commit()
        headers = _login(client, email)
        resp = client.post(f"/api/users/{admin.id}/toggle-actif", headers=headers)
        assert resp.status_code == 409


# Import school_pair fixture from tenant isolation module
pytest_plugins = []


@pytest.fixture
def school_pair(db):
    """Deux écoles avec admin + élève (copie légère pour PR10)."""
    from datetime import date

    from app.models import AnneeScolaire, Classe, Eleve, Inscription, NiveauEtude

    result = {}
    for key, code, name in (("A", "PR10-A", "École PR10 A"), ("B", "PR10-B", "École PR10 B")):
        school = db.query(School).filter(School.code == code).first()
        if not school:
            school = School(id=uuid.uuid4(), name=name, code=code, is_active=True)
            db.add(school)
            db.flush()
        if not db.query(Etablissement).filter(Etablissement.school_id == school.id).first():
            db.add(
                Etablissement(
                    id=uuid.uuid4(),
                    school_id=school.id,
                    nom=name,
                    format_matricule="{ANNEE}M-{SEQ}",
                )
            )
            db.flush()
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
            .filter(NiveauEtude.school_id == school.id, NiveauEtude.libelle == "6ème")
            .first()
        )
        if not niveau:
            niveau = NiveauEtude(
                id=uuid.uuid4(), school_id=school.id, libelle="6ème", ordre=1, cycle="premier"
            )
            db.add(niveau)
            db.flush()
        classe = (
            db.query(Classe)
            .filter(Classe.school_id == school.id, Classe.libelle == "6ème A", Classe.id_annee == annee.id)
            .first()
        )
        if not classe:
            classe = Classe(
                id=uuid.uuid4(),
                school_id=school.id,
                id_niveau=niveau.id,
                id_annee=annee.id,
                libelle="6ème A",
            )
            db.add(classe)
            db.flush()
        admin_email = f"admin-{code.lower()}@pr10.local"
        admin = db.query(Utilisateur).filter(Utilisateur.email == admin_email).first()
        if not admin:
            admin = Utilisateur(
                id=uuid.uuid4(),
                nom="Admin",
                prenom=key,
                email=admin_email,
                role="administrateur",
                mot_de_passe_hash=hash_password("Admin123!"),
                actif=True,
                school_id=school.id,
            )
            db.add(admin)
            db.flush()
        matricule = f"{code}-E1"
        eleve = db.query(Eleve).filter(Eleve.school_id == school.id, Eleve.matricule == matricule).first()
        if not eleve:
            eleve = Eleve(
                id=uuid.uuid4(),
                school_id=school.id,
                matricule=matricule,
                nom="Eleve",
                prenom=key,
                sexe="F",
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
        result[key] = {"school": school, "admin": admin, "eleve": eleve}
    db.commit()
    return result
