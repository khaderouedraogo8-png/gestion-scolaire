"""Intégration LMS e-learning — devoirs, remises, quiz scoring, ressources."""
from __future__ import annotations

import uuid
from datetime import date

from app.models import Eleve, Inscription


def _eleve(db, school_id, classe_id, annee_id, user_id=None):
    e = Eleve(
        id=uuid.uuid4(),
        matricule=f"LMS-{uuid.uuid4().hex[:6].upper()}",
        nom="Traoré",
        prenom="Awa",
        date_naissance=date(2012, 5, 1),
        sexe="F",
        school_id=school_id,
        id_utilisateur=user_id,
    )
    db.add(e)
    db.flush()
    db.add(
        Inscription(
            id=uuid.uuid4(),
            id_eleve=e.id,
            id_classe=classe_id,
            id_annee=annee_id,
            statut="inscrit",
            date_inscription=date.today(),
            school_id=school_id,
        )
    )
    db.commit()
    return e


def test_lms_devoir_remise_note_stats(client, auth_headers, db, annee_classe, default_school):
    sid = default_school.id
    eleve = _eleve(db, sid, annee_classe["classe"].id, annee_classe["annee"].id)

    created = client.post(
        "/api/elearning/devoirs",
        headers=auth_headers,
        json={
            "titre": "Dissertation",
            "consignes": "Rédiger 20 lignes",
            "id_classe": str(annee_classe["classe"].id),
            "note_max": "20",
            "publie": True,
        },
    )
    assert created.status_code == 201, created.get_json()
    devoir_id = created.get_json()["id"]

    remise = client.post(
        "/api/elearning/remises",
        headers=auth_headers,
        json={
            "id_devoir": devoir_id,
            "id_eleve": str(eleve.id),
            "contenu": "Ma copie…",
        },
    )
    assert remise.status_code == 201, remise.get_json()
    remise_id = remise.get_json()["id"]
    assert remise.get_json()["statut"] == "remise"

    note = client.put(
        f"/api/elearning/remises/{remise_id}",
        headers=auth_headers,
        json={"note": "14.5", "commentaire": "Bien"},
    )
    assert note.status_code == 200, note.get_json()
    assert note.get_json()["statut"] == "note"
    assert note.get_json()["note"] == "14.50" or float(note.get_json()["note"]) == 14.5

    stats = client.get(f"/api/elearning/devoirs/{devoir_id}/stats", headers=auth_headers)
    assert stats.status_code == 200
    body = stats.get_json()
    assert body["nb_remises"] == 1
    assert body["nb_notees"] == 1
    assert body["moyenne"] == 14.5


def test_lms_quiz_passer_auto_score(client, auth_headers, db, annee_classe, default_school):
    sid = default_school.id
    eleve = _eleve(db, sid, annee_classe["classe"].id, annee_classe["annee"].id)

    quiz = client.post(
        "/api/elearning/quiz",
        headers=auth_headers,
        json={
            "titre": "QCM Maths",
            "id_classe": str(annee_classe["classe"].id),
            "publie": True,
            "note_max": "20",
            "tentatives_max": 2,
            "afficher_correction": True,
            "questions": [
                {"q": "2+2?", "choices": ["3", "4", "5"], "answer": 1, "points": 1},
                {"q": "3+1?", "choices": ["3", "4"], "answer": 1, "points": 1},
            ],
        },
    )
    assert quiz.status_code == 201, quiz.get_json()
    quiz_id = quiz.get_json()["id"]

    attempt = client.post(
        f"/api/elearning/quiz/{quiz_id}/passer",
        headers=auth_headers,
        json={"id_eleve": str(eleve.id), "reponses": [1, 0]},
    )
    assert attempt.status_code == 201, attempt.get_json()
    body = attempt.get_json()
    assert body["nb_correctes"] == 1
    assert body["nb_questions"] == 2
    assert float(body["note"]) == 10.0
    assert body["tentatives_restantes"] == 1

    tentatives = client.get(
        f"/api/elearning/quiz/{quiz_id}/tentatives?id_eleve={eleve.id}",
        headers=auth_headers,
    )
    assert tentatives.status_code == 200
    assert len(tentatives.get_json()) == 1


def test_lms_ressource_et_progression(client, auth_headers, annee_classe):
    cid = str(annee_classe["classe"].id)
    res = client.post(
        "/api/elearning/ressources",
        headers=auth_headers,
        json={
            "titre": "Cours fractions",
            "type_ressource": "pdf",
            "url": "https://example.com/fractions.pdf",
            "id_classe": cid,
            "publie": True,
        },
    )
    assert res.status_code == 201, res.get_json()

    bad = client.post(
        "/api/elearning/ressources",
        headers=auth_headers,
        json={"titre": "Bad", "url": "ftp://evil", "publie": True},
    )
    assert bad.status_code == 400

    prog = client.get(f"/api/elearning/progression?id_classe={cid}", headers=auth_headers)
    assert prog.status_code == 200
    assert prog.get_json()["nb_ressources"] >= 1
