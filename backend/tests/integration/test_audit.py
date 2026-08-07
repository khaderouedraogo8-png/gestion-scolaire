"""Tests journal d'audit API."""


def test_audit_list_requires_admin(client, auth_headers):
    response = client.get("/api/audit", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert "items" in data
    assert "total" in data


def test_audit_list_unauthorized(client):
    response = client.get("/api/audit")
    assert response.status_code == 401
