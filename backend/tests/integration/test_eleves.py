"""Tests d'intégration — élèves."""
import uuid


class TestEleves:
    def test_list_eleves(self, client, auth_headers):
        response = client.get("/api/eleves/", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_create_eleve(self, client, auth_headers, annee_classe):
        data = {
            "nom": "Diallo",
            "prenom": "Amadou",
            "sexe": "M",
            "id_classe": str(annee_classe["classe"].id),
            "id_annee": str(annee_classe["annee"].id),
            "parents": [
                {
                    "nom": "Diallo",
                    "prenom": "Ibrahim",
                    "lien_parente": "père",
                    "telephone": "+22670000001",
                    "tuteur_legal": True,
                }
            ],
        }
        response = client.post("/api/eleves/", headers=auth_headers, json=data)
        assert response.status_code == 201
        result = response.get_json()
        assert result["nom"] == "Diallo"
        assert "matricule" in result

    def test_get_eleve_detail(self, client, auth_headers, annee_classe):
        data = {
            "nom": "Sow",
            "prenom": "Fatou",
            "sexe": "F",
            "id_classe": str(annee_classe["classe"].id),
            "id_annee": str(annee_classe["annee"].id),
        }
        create_resp = client.post("/api/eleves/", headers=auth_headers, json=data)
        eleve_id = create_resp.get_json()["id"]

        response = client.get(f"/api/eleves/{eleve_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.get_json()["prenom"] == "Fatou"
        # Notes médicales jamais dans export par défaut sans permission explicite endpoint
        assert "notes_medicales_chiffrees" not in response.get_json()
