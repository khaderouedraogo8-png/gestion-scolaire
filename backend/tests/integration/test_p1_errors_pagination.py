"""P1 — Error handler global + pagination listes critiques."""
import uuid


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
