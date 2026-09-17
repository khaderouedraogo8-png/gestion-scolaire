"""Tests UEMOA Vague A — intégrité finance, échéanciers, intégrations NON_CONFIGURE."""
import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.models import EcheancePaiement, Eleve, FraisScolaire, Inscription, Notification


def test_frais_duplicate_rejected(client, auth_headers, db, annee_classe, default_school):
    annee = annee_classe["annee"]
    niveau = annee_classe["niveau"]
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "id_niveau": str(niveau.id),
        "id_annee": str(annee.id),
        "motif": f"Scolarité-UQ-{suffix}",
        "montant_total": 90000,
    }
    r1 = client.post("/api/finance/frais", json=payload, headers=auth_headers)
    assert r1.status_code == 201, r1.get_json()
    r2 = client.post("/api/finance/frais", json=payload, headers=auth_headers)
    assert r2.status_code == 409


def test_frais_with_echeances_three_tranches(client, auth_headers, db, annee_classe):
    annee = annee_classe["annee"]
    niveau = annee_classe["niveau"]
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "id_niveau": str(niveau.id),
        "id_annee": str(annee.id),
        "motif": f"Scolarité-3T-{suffix}",
        "montant_total": "90000",
        "nb_tranches": 3,
    }
    r = client.post("/api/finance/frais/with-echeances", json=payload, headers=auth_headers)
    assert r.status_code == 201, r.get_json()
    data = r.get_json()
    assert len(data["echeances"]) == 3
    total = sum(float(e["montant"]) for e in data["echeances"])
    assert abs(total - 90000) < 0.1


def test_integrations_non_configure(client, auth_headers):
    r = client.get("/api/finance/integrations", headers=auth_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data["whatsapp"]["status"] == "NON_CONFIGURE"
    assert data["mobile_money"]["status"] == "NON_CONFIGURE"


def test_syscohada_plan_seeds(client, auth_headers):
    r = client.get("/api/finance/syscohada/plan", headers=auth_headers)
    assert r.status_code == 200
    rows = r.get_json()
    assert len(rows) >= 3
    assert any(x["compte"] == "7011" for x in rows)


def test_setup_progress(client, auth_headers):
    r = client.get("/api/etablissement/setup-progress", headers=auth_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] == 5
    assert "steps" in data


def test_relance_calendaire_j_minus_7(client, auth_headers, db, annee_classe, default_school):
    annee = annee_classe["annee"]
    classe = annee_classe["classe"]
    niveau = annee_classe["niveau"]
    sid = default_school.id
    suffix = uuid.uuid4().hex[:6].upper()
    eleve = Eleve(
        id=uuid.uuid4(),
        matricule=f"2025M-CAL{suffix}",
        nom="Sanou",
        prenom="Bintou",
        date_naissance=date(2011, 3, 2),
        sexe="F",
        school_id=sid,
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
            school_id=sid,
        )
    )
    frais = FraisScolaire(
        id=uuid.uuid4(),
        id_niveau=niveau.id,
        id_annee=annee.id,
        motif=f"Scol-CAL-{suffix}",
        montant_total=Decimal(60000),
        school_id=sid,
    )
    db.add(frais)
    db.flush()
    db.add(
        EcheancePaiement(
            id=uuid.uuid4(),
            id_frais=frais.id,
            libelle="T1",
            montant=Decimal(60000),
            date_echeance=date.today() + timedelta(days=7),
        )
    )
    db.commit()

    response = client.post(
        "/api/finance/arrieres/relancer",
        json={"id_annee": str(annee.id), "auto_envoyer": False, "mode": "calendaire"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["fenetres"]["J-7"] >= 1
    notifs = db.query(Notification).filter(Notification.id_eleve == eleve.id).all()
    assert any(n.type_notification == "retard_paiement" for n in notifs)


def test_whatsapp_relance_refused_when_not_configured(client, auth_headers, annee_classe):
    annee = annee_classe["annee"]
    response = client.post(
        "/api/finance/arrieres/relancer",
        json={
            "id_annee": str(annee.id),
            "canal": "whatsapp",
            "auto_envoyer": False,
            "mode": "global",
        },
        headers=auth_headers,
    )
    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["code"] == "WHATSAPP_NON_CONFIGURE"
