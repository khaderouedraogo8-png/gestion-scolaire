"""Tests relances arriérés."""
import uuid
from datetime import date
from decimal import Decimal

from app.models import (
    EcheancePaiement,
    Eleve,
    FraisScolaire,
    Inscription,
    Notification,
)


def test_relancer_arrieres_creates_notifications(client, auth_headers, db, annee_classe):
    annee = annee_classe["annee"]
    classe = annee_classe["classe"]
    niveau = annee_classe["niveau"]

    suffix = uuid.uuid4().hex[:6].upper()
    eleve = Eleve(
        id=uuid.uuid4(),
        matricule=f"2025M-REL{suffix}",
        nom="Diallo",
        prenom="Awa",
        date_naissance=date(2012, 5, 1),
        sexe="F",
    )
    db.add(eleve)
    db.flush()

    db.add(
        Inscription(
            id=uuid.uuid4(),
            id_eleve=eleve.id,
            id_annee=annee.id,
            id_classe=classe.id,
            statut="inscrit",
            date_inscription=date.today(),
        )
    )

    frais = FraisScolaire(
        id=uuid.uuid4(),
        id_niveau=niveau.id,
        id_annee=annee.id,
        motif="Scolarité",
        montant_total=Decimal(100000),
    )
    db.add(frais)
    db.flush()

    db.add(
        EcheancePaiement(
            id=uuid.uuid4(),
            id_frais=frais.id,
            libelle="T1",
            montant=Decimal(100000),
            date_echeance=date(2025, 10, 1),
        )
    )
    db.commit()

    response = client.post(
        "/api/finance/arrieres/relancer",
        json={"id_annee": str(annee.id), "auto_envoyer": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["notifications_crees"] >= 1

    notifs = db.query(Notification).filter(Notification.id_eleve == eleve.id).all()
    assert len(notifs) >= 1
    assert notifs[0].type_notification == "retard_paiement"


def test_relancer_arrieres_skips_recent(client, auth_headers, db, annee_classe):
    annee = annee_classe["annee"]
    classe = annee_classe["classe"]
    niveau = annee_classe["niveau"]

    suffix = uuid.uuid4().hex[:6].upper()
    eleve = Eleve(
        id=uuid.uuid4(),
        matricule=f"2025M-RL2{suffix}",
        nom="Koné",
        prenom="Ibra",
        date_naissance=date(2012, 3, 1),
        sexe="M",
    )
    db.add(eleve)
    db.flush()

    db.add(
        Inscription(
            id=uuid.uuid4(),
            id_eleve=eleve.id,
            id_annee=annee.id,
            id_classe=classe.id,
            statut="inscrit",
            date_inscription=date.today(),
        )
    )

    frais = FraisScolaire(
        id=uuid.uuid4(),
        id_niveau=niveau.id,
        id_annee=annee.id,
        motif="Scolarité",
        montant_total=Decimal(50000),
    )
    db.add(frais)
    db.flush()

    db.add(
        EcheancePaiement(
            id=uuid.uuid4(),
            id_frais=frais.id,
            libelle="T1",
            montant=Decimal(50000),
            date_echeance=date(2025, 10, 1),
        )
    )
    db.commit()

    payload = {"id_annee": str(annee.id), "auto_envoyer": False}
    r1 = client.post("/api/finance/arrieres/relancer", json=payload, headers=auth_headers)
    r2 = client.post("/api/finance/arrieres/relancer", json=payload, headers=auth_headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.get_json()["ignores_recents"] >= 1
