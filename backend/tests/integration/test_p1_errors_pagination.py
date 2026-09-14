"""P1 — Error handler global + pagination listes critiques."""

class TestErrorHandler:
    def test_unhandled_path_404_json_envelope(self, client, auth_headers):
        res = client.get("/api/chemin-inexistant-p1", headers=auth_headers)
        assert res.status_code == 404
        body = res.get_json()
        assert body is not None
        assert body.get("success") is False
        assert "message" in body
        assert body.get("error", {}).get("code") == "NOT_FOUND"
        assert "Traceback" not in str(body)

    def test_validation_error_on_user_create(self, client, auth_headers):
        res = client.post(
            "/api/users",
            headers=auth_headers,
            json={"email": "not-an-email", "password": "x"},
        )
        assert res.status_code in (400, 422)
        body = res.get_json()
        assert body is not None
        assert "message" in body or "errors" in body or "error" in body

    def test_unauthenticated_returns_json_envelope(self, client):
        res = client.get("/api/users")
        assert res.status_code == 401
        body = res.get_json()
        assert body is not None
        assert body.get("success") is False
        assert body.get("error", {}).get("code") == "UNAUTHORIZED"
        assert "msg" not in body
        assert "Traceback" not in str(body)

    def test_invalid_jwt_returns_sanitized_401(self, client):
        res = client.get(
            "/api/users",
            headers={"Authorization": "Bearer not-a-valid-token"},
        )
        assert res.status_code == 401
        body = res.get_json()
        assert body is not None
        assert body.get("success") is False
        assert body.get("error", {}).get("code") == "UNAUTHORIZED"
        assert "msg" not in body

    def test_not_found_message_is_sanitized(self, client, auth_headers):
        res = client.get("/api/chemin-inexistant-p1-sanitize", headers=auth_headers)
        assert res.status_code == 404
        body = res.get_json()
        assert body is not None
        assert body.get("success") is False
        assert body.get("error", {}).get("code") == "NOT_FOUND"
        assert body.get("message") == "Ressource introuvable."
        assert "werkzeug" not in (body.get("message") or "").lower()
        assert "not found" not in (body.get("message") or "").lower()

    def test_internal_error_does_not_leak_details(self):
        import os

        from app import create_app

        os.environ["FLASK_ENV"] = "testing"
        boom_app = create_app("testing")
        boom_app.config["TESTING"] = True

        @boom_app.get("/api/_test_boom_p1")
        def _boom():
            raise RuntimeError("SECRET_DB_PASSWORD=supersecret")

        with boom_app.test_client() as boom_client:
            res = boom_client.get("/api/_test_boom_p1")
        assert res.status_code == 500
        body = res.get_json()
        assert body is not None
        assert body.get("success") is False
        assert body.get("error", {}).get("code") == "INTERNAL_ERROR"
        blob = str(body)
        assert "SECRET_DB_PASSWORD" not in blob
        assert "supersecret" not in blob
        assert "Traceback" not in blob


class TestPagination:
    def test_eleves_paginated_shape(self, client, auth_headers):
        res = client.get("/api/eleves/?page=1&per_page=5", headers=auth_headers)
        assert res.status_code == 200
        body = res.get_json()
        assert "items" in body
        assert "total" in body
        assert body["page"] == 1
        assert body["per_page"] == 5

    def test_paiements_paginated_shape(self, client, auth_headers):
        res = client.get("/api/finance/paiements?page=1&per_page=10", headers=auth_headers)
        assert res.status_code == 200
        body = res.get_json()
        assert "items" in body
        assert isinstance(body["items"], list)
        assert "pagination" in body
        assert body["pagination"]["page"] == 1

    def test_absences_paginated_shape(self, client, auth_headers):
        res = client.get("/api/absences/?page=1&per_page=10", headers=auth_headers)
        assert res.status_code == 200
        body = res.get_json()
        assert "items" in body
        assert "total" in body

    def test_evaluations_paginated_shape(self, client, auth_headers):
        res = client.get("/api/notes/evaluations?page=1&per_page=10", headers=auth_headers)
        assert res.status_code == 200
        body = res.get_json()
        assert "items" in body

    def test_users_paginated_shape(self, client, auth_headers):
        res = client.get("/api/users?page=1&per_page=10", headers=auth_headers)
        assert res.status_code == 200
        body = res.get_json()
        assert "items" in body
        assert isinstance(body["items"], list)

    def test_per_page_capped(self, client, auth_headers):
        res = client.get("/api/finance/paiements?page=1&per_page=9999", headers=auth_headers)
        assert res.status_code == 200
        body = res.get_json()
        assert body["per_page"] <= 100

    def test_documents_paginated_shape(self, client, auth_headers):
        res = client.get("/api/documents/?page=1&per_page=10", headers=auth_headers)
        assert res.status_code == 200
        body = res.get_json()
        assert "items" in body

    def test_discipline_paginated_shape(self, client, auth_headers):
        res = client.get("/api/absences/discipline?page=1&per_page=10", headers=auth_headers)
        assert res.status_code == 200
        body = res.get_json()
        assert "items" in body
        assert "pagination" in body

    def test_bulletins_paginated_shape(self, client, auth_headers):
        res = client.get("/api/notes/bulletins?page=1&per_page=10", headers=auth_headers)
        assert res.status_code == 200
        body = res.get_json()
        assert "items" in body
        assert "pagination" in body
