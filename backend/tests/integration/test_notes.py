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

    def test_saisie_notes_absent_vs_zero(self, client, auth_headers, db, annee_classe, default_school):
        from app.models import Enseignant, Matiere, Trimestre

        sid = default_school.id
        matiere = Matiere(id=uuid.uuid4(), libelle="Français", code="FR", school_id=sid)
        db.add(matiere)
        enseignant = Enseignant(
            id=uuid.uuid4(),
            nom="Dupont",
            prenom="Jean",
            email="jean@test.local",
            school_id=sid,
        )
        db.add(enseignant)
        trimestre = (
            db.query(Trimestre)
            .filter(
                Trimestre.id_annee == annee_classe["annee"].id,
                Trimestre.sequence == 1,
            )
            .first()
        )
        if not trimestre:
            from app.services.academic import build_legacy_period, get_or_create_general_program

            program = get_or_create_general_program(db, sid)
            trimestre = build_legacy_period(
                id_annee=annee_classe["annee"].id,
                school_id=sid,
                id_program=program.id,
                sequence=1,
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

    def test_create_evaluation_rejects_unknown_type(self, client, auth_headers, db, annee_classe, default_school):
        from app.models import Enseignant, Matiere, Trimestre
        from app.services.evaluation_types import ensure_system_evaluation_types

        ensure_system_evaluation_types(db, default_school.id)
        db.commit()
        sid = default_school.id
        matiere = Matiere(id=uuid.uuid4(), libelle="Histoire", code="HIST", school_id=sid)
        enseignant = Enseignant(
            id=uuid.uuid4(), nom="X", prenom="Y", email=f"xy-{uuid.uuid4().hex[:6]}@t.local", school_id=sid
        )
        db.add_all([matiere, enseignant])
        trimestre = (
            db.query(Trimestre).filter(Trimestre.id_annee == annee_classe["annee"].id).first()
        )
        db.commit()
        resp = client.post(
            "/api/notes/evaluations",
            headers=auth_headers,
            json={
                "id_classe": str(annee_classe["classe"].id),
                "id_matiere": str(matiere.id),
                "id_trimestre": str(trimestre.id),
                "id_enseignant": str(enseignant.id),
                "type_evaluation": "type-inconnu-xyz",
                "coefficient": 1,
                "date_evaluation": "2025-10-15",
            },
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_EVALUATION_TYPE"

    def test_create_evaluation_accepts_custom_catalogue_type(
        self, client, auth_headers, db, annee_classe, default_school
    ):
        from app.models import Enseignant, Matiere, Trimestre
        from app.models.grading import EvaluationType
        from app.services.evaluation_types import ensure_system_evaluation_types

        ensure_system_evaluation_types(db, default_school.id)
        custom_code = f"atelier{uuid.uuid4().hex[:6]}"
        custom = EvaluationType(
            id=uuid.uuid4(),
            school_id=default_school.id,
            code=custom_code,
            label="Atelier",
            is_system=False,
            is_active=True,
        )
        sid = default_school.id
        matiere = Matiere(id=uuid.uuid4(), libelle="Arts", code="ART", school_id=sid)
        enseignant = Enseignant(
            id=uuid.uuid4(),
            nom="Art",
            prenom="Prof",
            email=f"art-{uuid.uuid4().hex[:6]}@t.local",
            school_id=sid,
        )
        db.add_all([custom, matiere, enseignant])
        trimestre = (
            db.query(Trimestre).filter(Trimestre.id_annee == annee_classe["annee"].id).first()
        )
        db.commit()
        resp = client.post(
            "/api/notes/evaluations",
            headers=auth_headers,
            json={
                "id_classe": str(annee_classe["classe"].id),
                "id_matiere": str(matiere.id),
                "id_trimestre": str(trimestre.id),
                "id_enseignant": str(enseignant.id),
                "type_evaluation": custom_code,
                "coefficient": 1,
                "date_evaluation": "2025-10-15",
                "libelle": "Atelier 1",
            },
        )
        assert resp.status_code == 201, resp.get_json()
        assert resp.get_json()["type_evaluation"] == custom_code

    def test_create_evaluation_rejects_inactive_type(
        self, client, auth_headers, db, annee_classe, default_school
    ):
        from app.models import Enseignant, Matiere, Trimestre
        from app.models.grading import EvaluationType
        from app.services.evaluation_types import ensure_system_evaluation_types

        ensure_system_evaluation_types(db, default_school.id)
        mute_code = f"mute{uuid.uuid4().hex[:6]}"
        custom = EvaluationType(
            id=uuid.uuid4(),
            school_id=default_school.id,
            code=mute_code,
            label="Mute",
            is_system=False,
            is_active=False,
        )
        sid = default_school.id
        matiere = Matiere(id=uuid.uuid4(), libelle="Sport", code="EPS", school_id=sid)
        enseignant = Enseignant(
            id=uuid.uuid4(),
            nom="Sp",
            prenom="Ort",
            email=f"eps-{uuid.uuid4().hex[:6]}@t.local",
            school_id=sid,
        )
        db.add_all([custom, matiere, enseignant])
        trimestre = (
            db.query(Trimestre).filter(Trimestre.id_annee == annee_classe["annee"].id).first()
        )
        db.commit()
        resp = client.post(
            "/api/notes/evaluations",
            headers=auth_headers,
            json={
                "id_classe": str(annee_classe["classe"].id),
                "id_matiere": str(matiere.id),
                "id_trimestre": str(trimestre.id),
                "id_enseignant": str(enseignant.id),
                "type_evaluation": mute_code,
                "coefficient": 1,
                "date_evaluation": "2025-10-15",
            },
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_EVALUATION_TYPE"