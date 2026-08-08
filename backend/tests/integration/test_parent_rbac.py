"""Tests RBAC parent — accès restreint aux enfants liés."""
import uuid

from app.auth.jwt_handler import hash_password
from app.models import (
    Eleve,
    EleveParent,
    Inscription,
    ParentTuteur,
    Utilisateur,
)


def test_parent_cannot_access_unlinked_eleve(client, db, annee_classe):
    """Un parent authentifié reçoit 403 sur un élève qui n'est pas le sien."""
    annee = annee_classe["annee"]
    classe = annee_classe["classe"]
    suffix = uuid.uuid4().hex[:8]

    eleve_mien = Eleve(
        id=uuid.uuid4(),
        matricule=f"TEST-P-{suffix}-A",
        nom="ParentTest",
        prenom="Enfant",
        sexe="M",
    )
    eleve_autre = Eleve(
        id=uuid.uuid4(),
        matricule=f"TEST-P-{suffix}-B",
        nom="Autre",
        prenom="Eleve",
        sexe="F",
    )
    db.add_all([eleve_mien, eleve_autre])
    db.flush()

    for eleve in (eleve_mien, eleve_autre):
        db.add(
            Inscription(
                id=uuid.uuid4(),
                id_eleve=eleve.id,
                id_classe=classe.id,
                id_annee=annee.id,
                statut="inscrit",
            )
        )

    parent_user = Utilisateur(
        id=uuid.uuid4(),
        nom="Parent",
        prenom="Demo",
        email=f"parent-test-{suffix}@ecole.local",
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
        prenom="Demo",
        telephone="70000000",
        id_utilisateur=parent_user.id,
    )
    db.add(parent_tuteur)
    db.flush()

    db.add(
        EleveParent(
            id_eleve=eleve_mien.id,
            id_parent=parent_tuteur.id,
            tuteur_legal=True,
        )
    )
    db.commit()

    login = client.post(
        "/api/login",
        json={"email": f"parent-test-{suffix}@ecole.local", "password": "Parent123!"},
    )
    assert login.status_code == 200
    token = login.get_json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ok = client.get(f"/api/eleves/{eleve_mien.id}", headers=headers)
    assert ok.status_code == 200

    forbidden = client.get(f"/api/eleves/{eleve_autre.id}", headers=headers)
    assert forbidden.status_code == 403
