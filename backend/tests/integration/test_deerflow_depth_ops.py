"""Smoke tests Deerflow depth ops — paie calcul, sorties QR, stock alerte."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.models import Enseignant, RhContrat


def test_paie_calculer_brut_retenues_net_et_ecritures(client, auth_headers, db, default_school):
    sid = default_school.id
    ens = Enseignant(
        id=uuid.uuid4(),
        school_id=sid,
        nom="Koné",
        prenom="Ibrahim",
        type_contrat="vacataire",
        taux_horaire=Decimal(5000),
    )
    db.add(ens)
    db.flush()
    db.add(
        RhContrat(
            id=uuid.uuid4(),
            school_id=sid,
            id_enseignant=ens.id,
            type_contrat="CDD",
            date_debut=date.today().replace(day=1),
            date_fin=None,
            salaire_base=Decimal(200000),
            statut="actif",
            poste="Enseignant",
        )
    )
    db.commit()

    r = client.post(
        "/api/comptabilite/paie/periodes",
        headers=auth_headers,
        json={
            "libelle": f"Mars-{uuid.uuid4().hex[:4]}",
            "date_debut": date.today().replace(day=1).isoformat(),
            "date_fin": date.today().isoformat(),
        },
    )
    assert r.status_code == 201, r.get_json()
    periode_id = r.get_json()["id"]

    calc = client.post(
        f"/api/comptabilite/paie/periodes/{periode_id}/calculer",
        headers=auth_headers,
        json={},
    )
    assert calc.status_code == 200, calc.get_json()
    body = calc.get_json()
    assert body["totaux"]["nb_lignes"] >= 1
    assert body["totaux"]["brut"] > 0
    assert abs(body["totaux"]["retenues"] - body["totaux"]["brut"] * 0.055) < 1.0
    assert abs(body["totaux"]["net"] - (body["totaux"]["brut"] - body["totaux"]["retenues"])) < 0.02
    assert any(e["compte_debit"] == "661" and e["compte_credit"] == "421" for e in body["ecritures"])

    lignes = client.get(
        f"/api/comptabilite/paie/lignes?id_periode={periode_id}",
        headers=auth_headers,
    )
    assert lignes.status_code == 200
    assert len(lignes.get_json()) >= 1


def test_front_office_sortie_hmac_et_validate(client, auth_headers, db, annee_classe, default_school):
    from app.models import Eleve, Inscription

    sid = default_school.id
    eleve = Eleve(
        id=uuid.uuid4(),
        matricule=f"2025S-{uuid.uuid4().hex[:6].upper()}",
        nom="Sanogo",
        prenom="Fatou",
        date_naissance=date(2013, 3, 12),
        sexe="F",
        school_id=sid,
    )
    db.add(eleve)
    db.flush()
    db.add(
        Inscription(
            id=uuid.uuid4(),
            id_eleve=eleve.id,
            id_classe=annee_classe["classe"].id,
            id_annee=annee_classe["annee"].id,
            statut="inscrit",
            date_inscription=date.today(),
            school_id=sid,
        )
    )
    db.commit()

    created = client.post(
        "/api/front-office/sorties",
        headers=auth_headers,
        json={"id_eleve": str(eleve.id), "motif": "Rendez-vous médical"},
    )
    assert created.status_code == 201, created.get_json()
    sortie = created.get_json()
    assert sortie.get("token_hmac")
    assert sortie.get("parent_valide") is False
    assert sortie.get("statut") == "en_attente"

    bad = client.patch(
        f"/api/front-office/sorties/{sortie['id']}/validate",
        headers=auth_headers,
        json={"token": "invalid"},
    )
    assert bad.status_code == 400

    ok = client.patch(
        f"/api/front-office/sorties/{sortie['id']}/validate",
        headers=auth_headers,
        json={"token": sortie["token_hmac"], "recupere_par": "Mme Sanogo"},
    )
    assert ok.status_code == 200, ok.get_json()
    validated = ok.get_json()
    assert validated["parent_valide"] is True
    assert validated["statut"] == "sorti"
    assert validated["recupere_par"] == "Mme Sanogo"


def test_inventaire_alertes_stock_bas(client, auth_headers):
    code = f"STK-{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/api/inventaire/articles",
        headers=auth_headers,
        json={
            "code": code,
            "libelle": "Encre imprimante",
            "quantite": 1,
            "seuil_alerte": 5,
        },
    )
    assert r.status_code == 201, r.get_json()

    alertes = client.get("/api/inventaire/alertes", headers=auth_headers)
    assert alertes.status_code == 200, alertes.get_json()
    body = alertes.get_json()
    assert body["nb"] >= 1
    assert any(a["code"] == code for a in body["alertes"])

    ecarts = client.post(
        "/api/inventaire/inventaire-annuel/ecarts",
        headers=auth_headers,
        json={
            "articles": [
                {"id_article": r.get_json()["id"], "quantite_physique": 0},
            ],
            "appliquer_ajustements": False,
        },
    )
    assert ecarts.status_code == 200, ecarts.get_json()
    assert ecarts.get_json()["nb_ecarts_non_nuls"] == 1
