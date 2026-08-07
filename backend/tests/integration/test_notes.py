"""Tests d'intégration — notes."""
import uuid
from datetime import date


class TestNotes:
    def test_list_matieres(self, client, auth_headers):
        response = client.get("/api/notes/matieres", headers=auth_headers)
        assert response.status_code == 200

    def test_create_matiere(self, client, auth_headers, db):
        response = client.post(
            "/api/notes/matieres",
            headers=auth_headers,
            json={"libelle": "Mathématiques", "code": "MATH"},
        )
        assert response.status_code == 201
        assert response.get_json()["libelle"] == "Mathématiques"

    def test_saisie_notes_absent_vs_zero(self, client, auth_headers, db, annee_classe):
        from app.models import Enseignant, Matiere, Trimestre

        matiere = Matiere(id=uuid.uuid4(), libelle="Français", code="FR")
        db.add(matiere)
        enseignant = Enseignant(
            id=uuid.uuid4(), nom="Dupont", prenom="Jean", email="jean@test.local"
        )
        db.add(enseignant)
        trimestre = (
            db.query(Trimestre)
            .filter(
                Trimestre.id_annee == annee_classe["annee"].id,
                Trimestre.numero == 1,
            )
            .first()
        )
        if not trimestre:
            trimestre = Trimestre(
                id=uuid.uuid4(),
                id_annee=annee_classe["annee"].id,
                numero=1,
                date_debut=date(2025, 9, 1),
                date_fin=date(2025, 12, 20),
            )
            db.add(trimestre)
        db.commit()

        eval_resp = client.post(
            "/api/notes/evaluations",
            headers=auth_headers,
            json={
                "id_classe": str(annee_classe["classe"].id),
                "id_matiere": str(matiere.id),
                "id_trimestre": str(trimestre.id),
                "id_enseignant": str(enseignant.id),
                "type_evaluation": "devoir",
                "coefficient": 2,
                "date_evaluation": "2025-10-15",
                "libelle": "Devoir 1",
            },
        )
        assert eval_resp.status_code == 201
        id_evaluation = eval_resp.get_json()["id"]

        def create_eleve(nom, prenom):
            resp = client.post(
                "/api/eleves/",
                headers=auth_headers,
                json={
                    "nom": nom,
                    "prenom": prenom,
                    "sexe": "M",
                    "id_classe": str(annee_classe["classe"].id),
                    "id_annee": str(annee_classe["annee"].id),
                },
            )
            assert resp.status_code == 201
            return resp.get_json()["id"]

        id_eleve_absent = create_eleve("Test", "Absent")
        id_eleve_zero = create_eleve("Test", "Zero")
        notes_resp = client.post(
            f"/api/notes/evaluations/{id_evaluation}/notes",
            headers=auth_headers,
            json={
                "notes": [
                    {"id_eleve": id_eleve_absent, "absent": True},
                    {"id_eleve": id_eleve_zero, "valeur_note": 0, "absent": False},
                ]
            },
        )
        assert notes_resp.status_code == 200

        grid_resp = client.get(
            f"/api/notes/evaluations/{id_evaluation}/notes",
            headers=auth_headers,
        )
        assert grid_resp.status_code == 200
        grid = {n["id_eleve"]: n for n in grid_resp.get_json()["notes"]}
        assert grid[id_eleve_absent]["absent"] is True
        assert grid[id_eleve_absent]["valeur_note"] is None
        assert grid[id_eleve_zero]["absent"] is False
        assert grid[id_eleve_zero]["valeur_note"] == 0.0
