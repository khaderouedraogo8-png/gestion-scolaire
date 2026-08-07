"""Tests d'intégration — authentification."""
import pytest


class TestAuth:
    def test_health(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.get_json()["status"] == "ok"

    def test_login_success(self, client, admin_user):
        response = client.post(
            "/api/login",
            json={"email": "admin@ecole.local", "password": "Admin123!"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "access_token" in data
        assert "doit_changer_mdp" in data
        set_cookie_header = " ".join(response.headers.getlist("Set-Cookie"))
        assert "refresh_token=" in set_cookie_header
        assert "HttpOnly" in set_cookie_header
        assert "SameSite=Strict" in set_cookie_header

    def test_create_app_production_requires_encryption_key(self, monkeypatch):
        """Le mode production refuse de démarrer sans ENCRYPTION_KEY."""
        from app import create_app

        monkeypatch.setenv("JWT_SECRET_KEY", "prod-jwt-secret-32chars-minimum!!")
        monkeypatch.setenv("REFRESH_SECRET_KEY", "prod-refresh-secret-32chars-min!!")
        monkeypatch.setenv("QR_HMAC_SECRET", "prod-qr-hmac-secret-32chars-min!!")
        monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

        with pytest.raises(RuntimeError, match="ENCRYPTION_KEY"):
            create_app("production")

    def test_login_invalid(self, client, admin_user):
        response = client.post(
            "/api/login",
            json={"email": "admin@ecole.local", "password": "WrongPassword!"},
        )
        assert response.status_code == 401

    def test_me_authenticated(self, client, auth_headers):
        response = client.get("/api/me", headers=auth_headers)
        assert response.status_code == 200
        assert response.get_json()["email"] == "admin@ecole.local"

    def test_me_unauthenticated(self, client):
        response = client.get("/api/me")
        assert response.status_code == 401

    def test_change_password(self, client, auth_headers, db):
        response = client.post(
            "/api/change-password",
            headers=auth_headers,
            json={
                "ancien_mot_de_passe": "Admin123!",
                "nouveau_mot_de_passe": "NewAdmin456!",
            },
        )
        assert response.status_code == 200

        # Restaurer le mot de passe pour les autres tests
        from app.auth.jwt_handler import hash_password
        from app.models import Utilisateur

        user = db.query(Utilisateur).filter(Utilisateur.email == "admin@ecole.local").first()
        user.mot_de_passe_hash = hash_password("Admin123!")
        user.doit_changer_mdp = True
        db.commit()
