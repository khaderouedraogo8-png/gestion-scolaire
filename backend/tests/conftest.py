"""Fixtures pytest pour tests d'intégration."""
import os
import uuid

import pytest

from app import create_app
from app.auth.jwt_handler import hash_password
from app.extensions import get_db
from app.models import AnneeScolaire, Classe, Etablissement, NiveauEtude, School, Trimestre, Utilisateur
from app.services.academic import build_legacy_period, get_or_create_general_program

DEFAULT_SCHOOL_CODE = "ECOLE-EXISTANTE"


@pytest.fixture(scope="session")
def app():
    os.environ["FLASK_ENV"] = "testing"
    application = create_app("testing")
    application.config["TESTING"] = True
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    with app.app_context():
        session = get_db()
        yield session
        session.rollback()


@pytest.fixture
def default_school(db):
    """École tenant par défaut (équivalent backfill migration)."""
    school = db.query(School).filter(School.code == DEFAULT_SCHOOL_CODE).first()
    if not school:
        etab = db.query(Etablissement).first()
        school = School(
            id=uuid.uuid4(),
            name=(etab.nom if etab else "École existante"),
            code=DEFAULT_SCHOOL_CODE,
            email=etab.email if etab else None,
            phone=etab.telephone if etab else None,
            address=etab.adresse if etab else None,
            city=etab.ville if etab else None,
            country=etab.pays if etab else None,
            logo=etab.logo_url if etab else None,
            is_active=True,
        )
        db.add(school)
        db.commit()
    get_or_create_general_program(db, school.id)
    from app.services.evaluation_types import ensure_system_evaluation_types

    ensure_system_evaluation_types(db, school.id)
    db.commit()
    return school


@pytest.fixture
def admin_user(db, default_school):
    user = db.query(Utilisateur).filter(Utilisateur.email == "admin@ecole.local").first()
    if not user:
        user = Utilisateur(
            id=uuid.uuid4(),
            nom="Admin",
            prenom="Test",
            email="admin@ecole.local",
            mot_de_passe_hash=hash_password("Admin123!"),
            role="administrateur",
            actif=True,
            doit_changer_mdp=True,
            school_id=default_school.id,
        )
        db.add(user)
        db.commit()
    else:
        user.mot_de_passe_hash = hash_password("Admin123!")
        user.tentatives_echouees = 0
        user.verrouille_jusqu_a = None
        user.actif = True
        user.school_id = default_school.id
        db.commit()
    return user


@pytest.fixture
def auth_headers(client, admin_user):
    response = client.post(
        "/api/login",
        json={"email": "admin@ecole.local", "password": "Admin123!"},
    )
    token = response.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def etablissement_data(db, default_school):
    etab = (
        db.query(Etablissement)
        .filter(Etablissement.school_id == default_school.id)
        .first()
    )
    if not etab:
        etab = Etablissement(
            id=uuid.uuid4(),
            school_id=default_school.id,
            nom="École Test",
            sigle="ET",
            format_matricule="{ANNEE}M-{SEQ}",
        )
        db.add(etab)
        db.commit()
    return etab


@pytest.fixture
def annee_classe(db, etablissement_data, default_school):
    from datetime import date

    sid = default_school.id
    program = get_or_create_general_program(db, sid)
    annee = (
        db.query(AnneeScolaire)
        .filter(AnneeScolaire.school_id == sid, AnneeScolaire.est_active.is_(True))
        .first()
    )
    if not annee:
        annee = AnneeScolaire(
            id=uuid.uuid4(),
            school_id=sid,
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
            NiveauEtude.school_id == sid,
            NiveauEtude.libelle == "6ème",
            NiveauEtude.id_program == program.id,
        )
        .first()
    )
    if not niveau:
        niveau = NiveauEtude(
            id=uuid.uuid4(),
            school_id=sid,
            id_program=program.id,
            libelle="6ème",
            ordre=1,
            cycle="premier",
        )
        db.add(niveau)
        db.flush()
    else:
        niveau.cycle = "premier"
        if getattr(niveau, "id_program", None) is None:
            niveau.id_program = program.id

    classe = (
        db.query(Classe)
        .filter(Classe.school_id == sid, Classe.libelle == "6ème A", Classe.id_annee == annee.id)
        .first()
    )
    if not classe:
        classe = Classe(
            id=uuid.uuid4(),
            school_id=sid,
            id_niveau=niveau.id,
            id_annee=annee.id,
            id_program=program.id,
            libelle="6ème A",
        )
        db.add(classe)
        db.flush()
    elif getattr(classe, "id_program", None) is None:
        classe.id_program = program.id

    trimestre = (
        db.query(Trimestre)
        .filter(Trimestre.id_annee == annee.id, Trimestre.sequence == 1)
        .first()
    )
    if not trimestre:
        trimestre = build_legacy_period(
            id_annee=annee.id,
            school_id=sid,
            id_program=program.id,
            sequence=1,
            date_debut=date(2025, 9, 1),
            date_fin=date(2025, 12, 20),
        )
        db.add(trimestre)

    db.commit()

    return {
        "annee": annee,
        "classe": classe,
        "niveau": niveau,
        "trimestre": trimestre,
        "program": program,
    }
