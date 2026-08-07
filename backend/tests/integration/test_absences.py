"""Tests d'intégration — absences."""
import uuid
from datetime import date


class TestAbsences:
    def test_list_absences(self, client, auth_headers):
        response = client.get("/api/absences/", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.get_json(), list)

    def test_create_absence(self, client, auth_headers, annee_classe):
        eleve_resp = client.post(
            "/api/eleves/",
            headers=auth_headers,
            json={
                "nom": "Absence",
                "prenom": "Test",
                "sexe": "M",
                "id_classe": str(annee_classe["classe"].id),
                "id_annee": str(annee_classe["annee"].id),
            },
        )
        assert eleve_resp.status_code == 201
        id_eleve = eleve_resp.get_json()["id"]

        response = client.post(
            "/api/absences/",
            headers=auth_headers,
            json={
                "id_eleve": id_eleve,
                "date_absence": "2025-11-01",
                "type_absence": "absence",
            },
        )
        assert response.status_code == 201

    def test_list_discipline(self, client, auth_headers):
        response = client.get("/api/absences/discipline", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.get_json(), list)
