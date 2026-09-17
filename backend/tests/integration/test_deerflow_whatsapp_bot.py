"""Bot WhatsApp parent — commandes + webhooks sandbox."""
import uuid
from datetime import date

import pytest

from app.auth.jwt_handler import hash_password
from app.models import (
    Eleve,
    EleveParent,
    ParentTuteur,
    Utilisateur,
)


@pytest.fixture
def parent_with_phone(db, default_school, annee_classe):
    user = Utilisateur(
        id=uuid.uuid4(),
        nom="Parent",
        prenom="WhatsApp",
        email=f"wa.parent.{uuid.uuid4().hex[:8]}@ecole.local",
        mot_de_passe_hash=hash_password("Parent123!"),
        role="parent",
        actif=True,
        doit_changer_mdp=False,
        school_id=default_school.id,
    )
    db.add(user)
    db.flush()
    parent = ParentTuteur(
        id=uuid.uuid4(),
        school_id=default_school.id,
        id_utilisateur=user.id,
        nom="Parent",
        prenom="WhatsApp",
        telephone="+22670001122",
        email=user.email,
    )
    db.add(parent)
    eleve = Eleve(
        id=uuid.uuid4(),
        school_id=default_school.id,
        matricule=f"WA{uuid.uuid4().hex[:6].upper()}",
        nom="Enfant",
        prenom="Test",
        sexe="M",
        date_naissance=date(2012, 1, 15),
    )
    db.add(eleve)
    db.flush()
    db.add(EleveParent(id_eleve=eleve.id, id_parent=parent.id, tuteur_legal=True))
    from app.models import Inscription

    insc = Inscription(
        id=uuid.uuid4(),
        school_id=default_school.id,
        id_eleve=eleve.id,
        id_classe=annee_classe["classe"].id,
        id_annee=annee_classe["annee"].id,
        statut="inscrit",
    )
    db.add(insc)
    db.commit()
    return {"user": user, "parent": parent, "eleve": eleve}


def test_parse_commands():
    from app.services.whatsapp_bot import parse_command

    assert parse_command("solde") == "SOLDE"
    assert parse_command("NOTES s'il vous plaît") == "NOTES"
    assert parse_command("ÉCHÉANCES") == "ECHEANCES"
    assert parse_command("help") == "AIDE"
    assert parse_command("inconnu") == "AIDE"


def test_webhook_sandbox_unknown_phone(client, monkeypatch, app):
    monkeypatch.setitem(app.config, "WHATSAPP_SANDBOX", True)
    r = client.post(
        "/api/webhooks/whatsapp",
        json={"from": "+22669999999", "text": "AIDE"},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["parent_found"] is False
    assert "SOLDE" in body["reply"] or "Commandes" in body["reply"] or "AIDE" in body["reply"]
    assert body.get("sent") is False


def test_webhook_sandbox_aide(client, monkeypatch, app, parent_with_phone):
    monkeypatch.setitem(app.config, "WHATSAPP_SANDBOX", True)
    r = client.post(
        "/api/webhooks/whatsapp",
        json={"from": "+22670001122", "text": "AIDE"},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    assert body["parent_found"] is True
    assert body["command"] == "AIDE"
    assert "SOLDE" in body["reply"]
    assert body["eleves_count"] >= 1


def test_webhook_sandbox_solde_notes_absences(client, monkeypatch, app, parent_with_phone):
    monkeypatch.setitem(app.config, "WHATSAPP_SANDBOX", True)
    for cmd in ("SOLDE", "NOTES", "ECHEANCES", "ABSENCES"):
        r = client.post(
            "/api/webhooks/whatsapp",
            json={"from": "22670001122", "text": cmd},
        )
        assert r.status_code == 200, cmd
        body = r.get_json()
        assert body["parent_found"] is True
        assert body["command"] == cmd
        assert body["reply"]
        assert body.get("sent") is False


def test_notifications_inbound_alias(client, parent_with_phone):
    r = client.post(
        "/api/notifications/whatsapp-bot/inbound",
        json={"from": "+22670001122", "text": "AIDE"},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["command"] == "AIDE"
    assert body["parent_found"] is True


def test_handle_inbound_send_sandbox(app, monkeypatch, parent_with_phone):
    monkeypatch.setitem(app.config, "WHATSAPP_SANDBOX", True)
    monkeypatch.setitem(app.config, "WHATSAPP_API_TOKEN", "")
    monkeypatch.setitem(app.config, "WHATSAPP_PHONE_NUMBER_ID", "")
    with app.app_context():
        from app.services.whatsapp_bot import handle_inbound

        result = handle_inbound("+22670001122", "SOLDE", send=True)
        assert result["parent_found"] is True
        assert result["sent"] is True
        assert result.get("send_code") == "SANDBOX_OK"


def test_dashboard_secretaire(client, auth_headers):
    r = client.get("/api/dashboard/secretaire", headers=auth_headers)
    assert r.status_code == 200
    body = r.get_json()
    assert body["role"] == "secretaire"
    assert "inscriptions_en_cours" in body
    assert "dossiers_admission_incomplets" in body
    assert "encaissements_jour" in body


def test_dashboard_comptable_depth(client, auth_headers):
    r = client.get("/api/dashboard/comptable", headers=auth_headers)
    assert r.status_code == 200
    body = r.get_json()
    assert "encaissements_jour" in body
    assert "impayes" in body
    assert "echeances_7j" in body
    assert "mm_pending" in body


def test_dashboard_surveillant_depth(client, auth_headers):
    r = client.get("/api/dashboard/surveillant", headers=auth_headers)
    assert r.status_code == 200
    body = r.get_json()
    assert "retards_aujourd_hui" in body
    assert "alertes_decrochage" in body
    assert "incidents_14j" in body
