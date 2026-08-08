"""Fixtures pytest pour tests d'intégration."""
import os
import uuid

import pytest

from app import create_app
from app.auth.jwt_handler import hash_password
from app.extensions import db_session, get_db
from app.models import AnneeScolaire, Classe, Etablissement, NiveauEtude, Utilisateur


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
def admin_user(db):
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
        )
        db.add(user)
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
def etablissement_data(db):
    if not db.query(Etablissement).first():
        etab = Etablissement(
            id=uuid.uuid4(),
            nom="École Test",
            sigle="ET",
            format_matricule="{ANNEE}M-{SEQ}",
        )
        db.add(etab)
        db.commit()
    return db.query(Etablissement).first()


@pytest.fixture
def annee_classe(db, etablissement_data):
    from datetime import date

    annee = db.query(AnneeScolaire).filter(AnneeScolaire.est_active.is_(True)).first()
    if not annee:
        annee = AnneeScolaire(
            id=uuid.uuid4(),
            libelle="2025-2026",
            date_debut=date(2025, 9, 1),
            date_fin=date(2026, 6, 30),
            est_active=True,
        )
        db.add(annee)
        db.flush()

    niveau = db.query(NiveauEtude).filter(NiveauEtude.libelle == "6ème").first()
    if not niveau:
        niveau = NiveauEtude(id=uuid.uuid4(), libelle="6ème", ordre=1, cycle="premier")
        db.add(niveau)
        db.flush()
    else:
        niveau.cycle = "premier"

    classe = db.query(Classe).filter(Classe.libelle == "6ème A").first()
    if not classe:
        classe = Classe(
            id=uuid.uuid4(),
            id_niveau=niveau.id,
            id_annee=annee.id,
            libelle="6ème A",
        )
        db.add(classe)
        db.commit()

    return {"annee": annee, "classe": classe, "niveau": niveau}
