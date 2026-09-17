"""Smoke tests — blueprints Deerflow (import + quelques endpoints authentifiés)."""


def test_deerflow_blueprints_importable():
    from app.routes import (
        admission,
        comptabilite,
        conseil_classe,
        elearning,
        fratries,
        front_office,
        inventaire,
        otp_auth,
        rh,
        vie_scolaire,
    )

    assert admission.blp.name == "admission"
    assert fratries.blp.name == "fratries"
    assert conseil_classe.blp.name == "conseil_classe"
    assert vie_scolaire.blp.name == "vie_scolaire"
    assert rh.blp.name == "rh"
    assert front_office.blp.name == "front_office"
    assert inventaire.blp.name == "inventaire"
    assert elearning.blp.name == "elearning"
    assert comptabilite.blp.name == "comptabilite"
    assert otp_auth.blp.name == "otp_auth"


def test_admission_list_empty(client, auth_headers):
    r = client.get("/api/admission/", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_admission_create_and_statut(client, auth_headers, annee_classe):
    payload = {
        "nom": "Ouédraogo",
        "prenom": "Aïcha",
        "sexe": "F",
        "niveau_demande": "6ème",
        "id_annee": str(annee_classe["annee"].id),
    }
    r = client.post("/api/admission/", headers=auth_headers, json=payload)
    assert r.status_code == 201, r.get_json()
    dossier = r.get_json()
    assert dossier["statut"] == "brouillon"

    r2 = client.patch(
        f"/api/admission/{dossier['id']}/statut",
        headers=auth_headers,
        json={"statut": "soumis"},
    )
    assert r2.status_code == 200
    assert r2.get_json()["statut"] == "soumis"


def test_fratries_and_remises_list(client, auth_headers):
    assert client.get("/api/fratries/", headers=auth_headers).status_code == 200
    assert client.get("/api/fratries/remises", headers=auth_headers).status_code == 200


def test_inventaire_articles(client, auth_headers):
    import uuid as uuid_mod

    code = f"CAH-{uuid_mod.uuid4().hex[:8]}"
    r = client.post(
        "/api/inventaire/articles",
        headers=auth_headers,
        json={"code": code, "libelle": "Cahier A4", "quantite": 10, "seuil_alerte": 2},
    )
    assert r.status_code == 201, r.get_json()
    assert client.get("/api/inventaire/articles", headers=auth_headers).status_code == 200


def test_vie_scolaire_cantine_list(client, auth_headers):
    r = client.get("/api/vie-scolaire/cantine/abonnements", headers=auth_headers)
    assert r.status_code == 200


def test_comptabilite_etats(client, auth_headers):
    assert client.get("/api/comptabilite/etats/balance", headers=auth_headers).status_code == 200
    assert client.get("/api/comptabilite/etats/bilan", headers=auth_headers).status_code == 200


def test_otp_request_neutral(client, default_school):
    r = client.post(
        "/api/auth/otp/request",
        json={
            "destinataire": "inconnu@example.com",
            "canal": "email",
            "purpose": "login_parent",
            "school_code": default_school.code,
        },
    )
    assert r.status_code == 200
    body = r.get_json()
    assert "expires_in_seconds" in body


def test_emploi_temps_conflits(client, auth_headers):
    r = client.get("/api/emploi-temps/conflits", headers=auth_headers)
    assert r.status_code == 200
    body = r.get_json()
    assert "conflits_enseignant" in body
    assert "conflits_classe" in body


def test_dashboard_comptable_surveillant(client, auth_headers):
    assert client.get("/api/dashboard/comptable", headers=auth_headers).status_code == 200
    assert client.get("/api/dashboard/surveillant", headers=auth_headers).status_code == 200


def test_absences_alertes_list(client, auth_headers):
    r = client.get("/api/absences/alertes-decrochage", headers=auth_headers)
    assert r.status_code == 200


def test_finance_recouvrement_detail(client, auth_headers, annee_classe):
    r = client.get(
        f"/api/finance/recouvrement/detail?id_annee={annee_classe['annee'].id}",
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.get_json()
    assert "taux_recouvrement" in body
