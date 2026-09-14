"""P0 — Upload sécurisé + forgot-password (pas de fuite reset_token)."""
import io
import os
import uuid
from datetime import date

import pytest

from app.auth.jwt_handler import hash_password
from app.models import (
    AnneeScolaire,
    Classe,
    Eleve,
    Inscription,
    NiveauEtude,
    Utilisateur,
)


def _admin_headers(client, db):
    email = f"admin-sec-{uuid.uuid4().hex[:8]}@ecole.local"
    user = Utilisateur(
        id=uuid.uuid4(),
        nom="Admin",
        prenom="Sec",
        email=email,
        mot_de_passe_hash=hash_password("Admin123!"),
        role="administrateur",
        actif=True,
    )
    db.add(user)
    db.commit()
    res = client.post("/api/login", json={"email": email, "password": "Admin123!"})
    assert res.status_code == 200, res.get_json()
    return {"Authorization": f"Bearer {res.get_json()['access_token']}"}


@pytest.fixture
def eleve_for_upload(db):
    suffix = uuid.uuid4().hex[:8]
    annee = AnneeScolaire(
        id=uuid.uuid4(),
        libelle=f"2025-u-{suffix}",
        date_debut=date(2025, 9, 1),
        date_fin=date(2026, 6, 30),
        est_active=True,
    )
    niveau = NiveauEtude(id=uuid.uuid4(), libelle=f"5ème-{suffix}", cycle="premier", ordre=2)
    db.add_all([annee, niveau])
    db.flush()
    classe = Classe(
        id=uuid.uuid4(),
        id_niveau=niveau.id,
        id_annee=annee.id,
        libelle=f"5A-{suffix}",
    )
    eleve = Eleve(
        id=uuid.uuid4(),
        matricule=f"U-{suffix}",
        nom="Upload",
        prenom="Test",
        date_naissance=date(2013, 1, 1),
        sexe="M",
    )
    db.add_all([classe, eleve])
    db.flush()
    db.add(
        Inscription(
            id=uuid.uuid4(),
            id_eleve=eleve.id,
            id_classe=classe.id,
            id_annee=annee.id,
            statut="inscrit",
        )
    )
    db.commit()
    return eleve.id


class TestUploadSecurity:
    def test_reject_php_upload(self, client, db, eleve_for_upload):
        headers = _admin_headers(client, db)
        data = {
            "file": (io.BytesIO(b"<?php echo 1; ?>"), "shell.php"),
            "type": "autre",
        }
        res = client.post(
            f"/api/eleves/{eleve_for_upload}/upload",
            headers=headers,
            data=data,
            content_type="multipart/form-data",
        )
        assert res.status_code == 400

    def test_reject_path_traversal_name(self, client, db, eleve_for_upload):
        headers = _admin_headers(client, db)
        data = {
            "file": (io.BytesIO(b"%PDF-1.4"), "../../etc/passwd.pdf"),
            "type": "autre",
        }
        res = client.post(
            f"/api/eleves/{eleve_for_upload}/upload",
            headers=headers,
            data=data,
            content_type="multipart/form-data",
        )
        assert res.status_code == 400

    def test_accept_pdf_upload(self, client, db, eleve_for_upload):
        headers = _admin_headers(client, db)
        data = {
            "file": (io.BytesIO(b"%PDF-1.4 fake"), "bulletin.pdf"),
            "type": "piece",
        }
        res = client.post(
            f"/api/eleves/{eleve_for_upload}/upload",
            headers=headers,
            data=data,
            content_type="multipart/form-data",
        )
        assert res.status_code == 201, res.get_json()
        body = res.get_json()
        assert "filename" in body
        assert body["filename"].endswith(".pdf")
        assert "bulletin" not in body["filename"]  # nom serveur UUID


class TestForgotPasswordSecurity:
    def test_no_token_without_expose_even_if_debug(self, client, app, monkeypatch):
        monkeypatch.setenv("EXPOSE_RESET_TOKEN", "0")
        monkeypatch.setenv("SMTP_ENABLED", "0")
        monkeypatch.setenv("SMTP_HOST", "localhost")
        monkeypatch.delenv("FLASK_ENV", raising=False)
        app.config["TESTING"] = False  # simule hors tests pour la branche expose
        app.config["DEBUG"] = True
        with app.test_client() as c:
            # Sans TESTING + sans SMTP_ENABLED → 503, pas de token
            res = c.post("/api/forgot-password", json={"email": "nobody@ecole.local"})
            # Remettre TESTING pour le reste de la session fixture globale
            app.config["TESTING"] = True
            assert res.status_code == 503
            assert "reset_token" not in (res.get_json() or {})

    def test_token_only_when_testing_or_expose(self, client, db):
        # Fixture app a TESTING=True → token autorisé pour faciliter les tests
        email = f"reset-{uuid.uuid4().hex[:8]}@ecole.local"
        db.add(
            Utilisateur(
                id=uuid.uuid4(),
                nom="Reset",
                prenom="User",
                email=email,
                mot_de_passe_hash=hash_password("Reset123!"),
                role="secretariat",
                actif=True,
            )
        )
        db.commit()
        res = client.post("/api/forgot-password", json={"email": email})
        assert res.status_code == 200
        assert "reset_token" in res.get_json()
