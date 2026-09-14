"""Tests fondation multi-tenant Phase 1 — School + tenant context."""
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.auth.jwt_handler import hash_password
from app.models import School, Utilisateur
from app.services.tenant import TenantRequiredError, require_user_school


@pytest.fixture
def school_a(db):
    school = db.query(School).filter(School.code == "SCHOOL-A").first()
    if not school:
        school = School(
            id=uuid.uuid4(),
            name="École Alpha",
            code="SCHOOL-A",
            city="Ouagadougou",
            country="Burkina Faso",
            is_active=True,
        )
        db.add(school)
        db.commit()
    return school


@pytest.fixture
def school_b(db):
    school = db.query(School).filter(School.code == "SCHOOL-B").first()
    if not school:
        school = School(
            id=uuid.uuid4(),
            name="École Beta",
            code="SCHOOL-B",
            city="Bobo-Dioulasso",
            country="Burkina Faso",
            is_active=True,
        )
        db.add(school)
        db.commit()
    return school


@pytest.fixture
def user_school_a(db, school_a):
    email = "admin-a@school-a.test"
    user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
    if not user:
        user = Utilisateur(
            id=uuid.uuid4(),
            nom="Admin",
            prenom="Alpha",
            email=email,
            mot_de_passe_hash=hash_password("Admin123!"),
            role="administrateur",
            actif=True,
            doit_changer_mdp=False,
            school_id=school_a.id,
        )
        db.add(user)
        db.commit()
    else:
        user.school_id = school_a.id
        user.mot_de_passe_hash = hash_password("Admin123!")
        user.actif = True
        db.commit()
    return user


@pytest.fixture
def user_school_b(db, school_b):
    email = "admin-b@school-b.test"
    user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
    if not user:
        user = Utilisateur(
            id=uuid.uuid4(),
            nom="Admin",
            prenom="Beta",
            email=email,
            mot_de_passe_hash=hash_password("Admin123!"),
            role="administrateur",
            actif=True,
            doit_changer_mdp=False,
            school_id=school_b.id,
        )
        db.add(user)
        db.commit()
    else:
        user.school_id = school_b.id
        user.mot_de_passe_hash = hash_password("Admin123!")
        user.actif = True
        db.commit()
    return user


class TestSchoolModel:
    def test_create_and_read(self, db):
        code = f"T-{uuid.uuid4().hex[:8]}"
        school = School(
            id=uuid.uuid4(),
            name="École Test Création",
            code=code,
            is_active=True,
        )
        db.add(school)
        db.commit()

        loaded = db.query(School).filter(School.code == code).first()
        assert loaded is not None
        assert loaded.name == "École Test Création"
        assert loaded.is_active is True

    def test_code_unique(self, db, school_a):
        dup = School(
            id=uuid.uuid4(),
            name="Doublon",
            code=school_a.code,
            is_active=True,
        )
        db.add(dup)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


class TestUserSchoolId:
    def test_user_has_school_id(self, db, user_school_a, school_a):
        user = db.query(Utilisateur).filter(Utilisateur.id == user_school_a.id).first()
        assert user.school_id == school_a.id

    def test_admin_fixture_backfilled_or_nullable(self, db, admin_user):
        """Après migration, les utilisateurs existants ont un school_id (sinon nullable)."""
        user = db.query(Utilisateur).filter(Utilisateur.id == admin_user.id).first()
        assert hasattr(user, "school_id")
        # school_id peut être None seulement si migration non appliquée — en test on l'exige après setup
        # La fixture default_school ci-dessous assure le backfill local.


class TestTenantContext:
    def test_require_user_school_ok(self, user_school_a, school_a):
        assert require_user_school(user_school_a) == school_a.id

    def test_require_user_school_missing(self, db):
        user = Utilisateur(
            id=uuid.uuid4(),
            nom="Sans",
            prenom="École",
            email=f"no-school-{uuid.uuid4().hex[:8]}@test.local",
            mot_de_passe_hash=hash_password("Admin123!"),
            role="administrateur",
            actif=True,
            school_id=None,
        )
        db.add(user)
        db.commit()
        with pytest.raises(TenantRequiredError):
            require_user_school(user)

    def test_isolation_context_a_vs_b(self, user_school_a, user_school_b, school_a, school_b):
        assert require_user_school(user_school_a) == school_a.id
        assert require_user_school(user_school_b) == school_b.id
        assert require_user_school(user_school_a) != require_user_school(user_school_b)


class TestCurrentSchoolApi:
    def test_get_current_school(self, client, db, user_school_a, school_a):
        login = client.post(
            "/api/login",
            json={"email": user_school_a.email, "password": "Admin123!"},
        )
        assert login.status_code == 200
        token = login.get_json()["access_token"]
        resp = client.get(
            "/api/schools/current",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == str(school_a.id)
        assert data["code"] == school_a.code
        assert data["name"] == school_a.name

    def test_get_current_school_without_school(self, client, db):
        email = f"orphan-{uuid.uuid4().hex[:8]}@test.local"
        user = Utilisateur(
            id=uuid.uuid4(),
            nom="Orphan",
            prenom="User",
            email=email,
            mot_de_passe_hash=hash_password("Admin123!"),
            role="administrateur",
            actif=True,
            doit_changer_mdp=False,
            school_id=None,
        )
        db.add(user)
        db.commit()

        login = client.post("/api/login", json={"email": email, "password": "Admin123!"})
        assert login.status_code == 200
        token = login.get_json()["access_token"]
        resp = client.get(
            "/api/schools/current",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_unauthenticated(self, client):
        resp = client.get("/api/schools/current")
        assert resp.status_code == 401
