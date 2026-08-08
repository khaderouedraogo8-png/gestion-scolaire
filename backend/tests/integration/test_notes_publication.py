"""Tests publication notes — filtrage parent sur statut_saisie."""
import uuid
from datetime import date

from app.auth.jwt_handler import hash_password
from app.models import (
    Eleve,
    EleveParent,
    Enseignant,
    Evaluation,
    Inscription,
    Matiere,
    ParentTuteur,
    Trimestre,
    Utilisateur,
)


def test_parent_cannot_see_notes_en_cours(client, db, annee_classe):
    annee = annee_classe["annee"]
    classe = annee_classe["classe"]
    suffix = uuid.uuid4().hex[:8]

    trimestre = db.query(Trimestre).filter(Trimestre.id_annee == annee.id).first()
    matiere = Matiere(libelle=f"Math-{suffix}", code=f"M{suffix[:4]}")
    db.add(matiere)
    db.flush()

    enseignant = Enseignant(
        id=uuid.uuid4(),
        nom="Prof",
        prenom="Test",
        email=f"prof-{suffix}@ecole.local",
    )
    db.add(enseignant)
    db.flush()

    eleve = Eleve(
        id=uuid.uuid4(),
        matricule=f"NOTES-{suffix}",
        nom="Eleve",
        prenom="Test",
        sexe="M",
    )
    db.add(eleve)
    db.flush()

    db.add(
        Inscription(
            id=uuid.uuid4(),
            id_eleve=eleve.id,
            id_classe=classe.id,
            id_annee=annee.id,
            statut="inscrit",
        )
    )

    evaluation = Evaluation(
        id=uuid.uuid4(),
        id_classe=classe.id,
        id_matiere=matiere.id,
        id_trimestre=trimestre.id,
        id_enseignant=enseignant.id,
        type_evaluation="devoir",
        coefficient=1,
        date_evaluation=date.today(),
        libelle="Devoir test",
        statut_publication="publie",
        statut_saisie="en_cours",
    )
    db.add(evaluation)

    parent_user = Utilisateur(
        id=uuid.uuid4(),
        nom="Parent",
        prenom="Notes",
        email=f"parent-notes-{suffix}@ecole.local",
        mot_de_passe_hash=hash_password("Parent123!"),
        role="parent",
        actif=True,
        doit_changer_mdp=False,
    )
    db.add(parent_user)
    db.flush()

    parent_tuteur = ParentTuteur(
        id=uuid.uuid4(),
        nom="Parent",
        prenom="Notes",
        telephone="70000001",
        id_utilisateur=parent_user.id,
    )
    db.add(parent_tuteur)
    db.flush()

    db.add(
        EleveParent(
            id_eleve=eleve.id,
            id_parent=parent_tuteur.id,
            tuteur_legal=True,
        )
    )
    db.commit()

    login = client.post(
        "/api/login",
        json={"email": f"parent-notes-{suffix}@ecole.local", "password": "Parent123!"},
    )
    token = login.get_json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    forbidden = client.get(f"/api/notes/evaluations/{evaluation.id}/notes", headers=headers)
    assert forbidden.status_code == 403

    evaluation.statut_saisie = "cloturee"
    db.commit()

    ok = client.get(f"/api/notes/evaluations/{evaluation.id}/notes", headers=headers)
    assert ok.status_code == 200
