"""P0 — Contrôle d'accès objet (enseignant) : pas d'IDOR via UUID."""
import uuid
from datetime import date

import pytest

from app.auth.jwt_handler import hash_password
from app.models import (
    AffectationEnseignant,
    AnneeScolaire,
    Classe,
    Eleve,
    Enseignant,
    Evaluation,
    Inscription,
    Matiere,
    NiveauEtude,
    Utilisateur,
)
from app.services.academic import build_legacy_period, get_or_create_general_program


def _auth(client, email, password):
    res = client.post("/api/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.get_json()
    return {"Authorization": f"Bearer {res.get_json()['access_token']}"}


@pytest.fixture
def teacher_idor_setup(db, default_school):
    """Deux classes : enseignant affecté seulement à la classe A."""
    suffix = uuid.uuid4().hex[:8]
    sid = default_school.id
    program = get_or_create_general_program(db, sid)
    annee = AnneeScolaire(
        id=uuid.uuid4(),
        school_id=sid,
        libelle=f"2025-{suffix}",
        date_debut=date(2025, 9, 1),
        date_fin=date(2026, 6, 30),
        est_active=True,
    )
    db.add(annee)
    niveau = NiveauEtude(
        id=uuid.uuid4(),
        libelle=f"6ème-{suffix}",
        cycle="premier",
        ordre=1,
        school_id=sid,
        id_program=program.id,
    )
    db.add(niveau)
    db.flush()

    classe_a = Classe(
        id=uuid.uuid4(),
        id_niveau=niveau.id,
        id_annee=annee.id,
        id_program=program.id,
        libelle=f"6A-{suffix}",
        school_id=sid,
    )
    classe_b = Classe(
        id=uuid.uuid4(),
        id_niveau=niveau.id,
        id_annee=annee.id,
        id_program=program.id,
        libelle=f"6B-{suffix}",
        school_id=sid,
    )
    db.add_all([classe_a, classe_b])

    matiere = Matiere(id=uuid.uuid4(), libelle=f"Math-{suffix}", code=f"M{suffix[:4]}", school_id=sid)
    db.add(matiere)

    user = Utilisateur(
        id=uuid.uuid4(),
        nom="Prof",
        prenom="Test",
        email=f"prof-idor-{suffix}@ecole.local",
        mot_de_passe_hash=hash_password("Enseignant123!"),
        role="enseignant",
        actif=True,
        school_id=sid,
    )
    db.add(user)
    db.flush()
    enseignant = Enseignant(
        id=uuid.uuid4(),
        id_utilisateur=user.id,
        nom="Prof",
        prenom="Test",
        email=user.email,
        school_id=sid,
    )
    db.add(enseignant)
    db.flush()
    db.add(
        AffectationEnseignant(
            id=uuid.uuid4(),
            id_enseignant=enseignant.id,
            id_classe=classe_a.id,
            id_matiere=matiere.id,
            id_annee=annee.id,
            school_id=sid,
        )
    )

    eleve_a = Eleve(
        id=uuid.uuid4(),
        matricule=f"A-{suffix}",
        nom="Eleve",
        prenom="ClasseA",
        date_naissance=date(2012, 1, 1),
        sexe="M",
        school_id=sid,
    )
    eleve_b = Eleve(
        id=uuid.uuid4(),
        matricule=f"B-{suffix}",
        nom="Eleve",
        prenom="ClasseB",
        date_naissance=date(2012, 1, 1),
        sexe="F",
        school_id=sid,
    )
    db.add_all([eleve_a, eleve_b])
    db.flush()
    db.add_all(
        [
            Inscription(
                id=uuid.uuid4(),
                id_eleve=eleve_a.id,
                id_classe=classe_a.id,
                id_annee=annee.id,
                statut="inscrit",
                school_id=sid,
            ),
            Inscription(
                id=uuid.uuid4(),
                id_eleve=eleve_b.id,
                id_classe=classe_b.id,
                id_annee=annee.id,
                statut="inscrit",
                school_id=sid,
            ),
        ]
    )

    trim = build_legacy_period(
        id_annee=annee.id,
        school_id=sid,
        id_program=program.id,
        sequence=1,
        date_debut=date(2025, 9, 1),
        date_fin=date(2025, 12, 15),
    )
    db.add(trim)
    db.flush()

    # Enseignant « fantôme » pour l'éval de la classe B (pas l'utilisateur testé)
    enseignant_b = Enseignant(
        id=uuid.uuid4(),
        nom="Autre",
        prenom="Prof",
        email=f"autre-{suffix}@ecole.local",
        school_id=sid,
    )
    db.add(enseignant_b)
    db.flush()

    eval_b = Evaluation(
        id=uuid.uuid4(),
        id_classe=classe_b.id,
        id_matiere=matiere.id,
        id_trimestre=trim.id,
        id_enseignant=enseignant_b.id,
        type_evaluation="devoir",
        libelle="Devoir classe B",
        date_evaluation=date(2025, 10, 1),
        coefficient=1,
        statut_publication="publie",
        statut_saisie="en_cours",
        school_id=sid,
    )
    db.add(eval_b)
    db.commit()

    return {
        "email": user.email,
        "password": "Enseignant123!",
        "eleve_a": eleve_a.id,
        "eleve_b": eleve_b.id,
        "eval_b": eval_b.id,
    }


class TestTeacherIdor:
    def test_teacher_cannot_get_eleve_other_class(self, client, teacher_idor_setup):
        headers = _auth(client, teacher_idor_setup["email"], teacher_idor_setup["password"])
        res = client.get(f"/api/eleves/{teacher_idor_setup['eleve_b']}", headers=headers)
        assert res.status_code == 403

    def test_teacher_can_get_eleve_own_class(self, client, teacher_idor_setup):
        headers = _auth(client, teacher_idor_setup["email"], teacher_idor_setup["password"])
        res = client.get(f"/api/eleves/{teacher_idor_setup['eleve_a']}", headers=headers)
        assert res.status_code == 200

    def test_teacher_cannot_get_evaluation_other_class(self, client, teacher_idor_setup):
        headers = _auth(client, teacher_idor_setup["email"], teacher_idor_setup["password"])
        res = client.get(
            f"/api/notes/evaluations/{teacher_idor_setup['eval_b']}",
            headers=headers,
        )
        assert res.status_code == 403

    def test_teacher_cannot_get_notes_grid_other_class(self, client, teacher_idor_setup):
        headers = _auth(client, teacher_idor_setup["email"], teacher_idor_setup["password"])
        res = client.get(
            f"/api/notes/evaluations/{teacher_idor_setup['eval_b']}/notes",
            headers=headers,
        )
        assert res.status_code == 403

    def test_teacher_cannot_list_absences_other_student(self, client, teacher_idor_setup):
        headers = _auth(client, teacher_idor_setup["email"], teacher_idor_setup["password"])
        res = client.get(
            f"/api/absences/?id_eleve={teacher_idor_setup['eleve_b']}",
            headers=headers,
        )
        assert res.status_code == 403

    def test_teacher_cannot_create_absence_other_student(self, client, teacher_idor_setup):
        headers = _auth(client, teacher_idor_setup["email"], teacher_idor_setup["password"])
        res = client.post(
            "/api/absences/",
            headers=headers,
            json={
                "id_eleve": str(teacher_idor_setup["eleve_b"]),
                "date_absence": "2025-10-10",
                "type_absence": "absence",
                "justifiee": False,
            },
        )
        assert res.status_code == 403

    def test_teacher_can_create_absence_own_student(self, client, teacher_idor_setup):
        headers = _auth(client, teacher_idor_setup["email"], teacher_idor_setup["password"])
        res = client.post(
            "/api/absences/",
            headers=headers,
            json={
                "id_eleve": str(teacher_idor_setup["eleve_a"]),
                "date_absence": "2025-10-11",
                "type_absence": "absence",
                "justifiee": False,
            },
        )
        assert res.status_code in (200, 201), res.get_json()
