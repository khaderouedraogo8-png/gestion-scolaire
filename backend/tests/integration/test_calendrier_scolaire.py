"""Tests calendrier scolaire — blocage des dates pour évaluations."""
import uuid
from datetime import date, timedelta

from app.auth.jwt_handler import hash_password
from app.models import Enseignant, EvenementCalendrier, Matiere, Trimestre, Utilisateur


def test_evaluation_blocked_on_holiday(client, db, annee_classe):
    annee = annee_classe["annee"]
    classe = annee_classe["classe"]
    suffix = uuid.uuid4().hex[:8]

    admin = Utilisateur(
        id=uuid.uuid4(),
        nom="Admin",
        prenom="Cal",
        email=f"admin-cal-{suffix}@ecole.local",
        mot_de_passe_hash=hash_password("Admin123!"),
        role="administrateur",
        actif=True,
        doit_changer_mdp=False,
    )
    db.add(admin)
    db.flush()

    trimestre = db.query(Trimestre).filter(Trimestre.id_annee == annee.id).first()
    matiere = Matiere(libelle=f"Hist-{suffix}", code=f"H{suffix[:4]}")
    db.add(matiere)
    db.flush()

    enseignant = Enseignant(
        id=uuid.uuid4(),
        nom="Prof",
        prenom="Cal",
        email=f"prof-cal-{suffix}@ecole.local",
    )
    db.add(enseignant)
    db.flush()

    blocked_date = date.today() + timedelta(days=30)
    db.add(
        EvenementCalendrier(
            id=uuid.uuid4(),
            id_annee=annee.id,
            type_evenement="ferie",
            libelle="Fête test",
            date_debut=blocked_date,
            date_fin=blocked_date,
            bloque_programmation=True,
        )
    )
    db.commit()

    login = client.post(
        "/api/login",
        json={"email": f"admin-cal-{suffix}@ecole.local", "password": "Admin123!"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}

    resp = client.post(
        "/api/notes/evaluations",
        headers=headers,
        json={
            "id_classe": str(classe.id),
            "id_matiere": str(matiere.id),
            "id_trimestre": str(trimestre.id),
            "id_enseignant": str(enseignant.id),
            "type_evaluation": "examen",
            "coefficient": 2,
            "date_evaluation": blocked_date.isoformat(),
            "libelle": "Compo bloquée",
        },
    )
    assert resp.status_code == 400
    assert "bloquée" in resp.get_json()["message"].lower()

    ok_date = blocked_date + timedelta(days=1)
    ok = client.post(
        "/api/notes/evaluations",
        headers=headers,
        json={
            "id_classe": str(classe.id),
            "id_matiere": str(matiere.id),
            "id_trimestre": str(trimestre.id),
            "id_enseignant": str(enseignant.id),
            "type_evaluation": "devoir",
            "coefficient": 1,
            "date_evaluation": ok_date.isoformat(),
            "libelle": "Devoir OK",
        },
    )
    assert ok.status_code == 201
