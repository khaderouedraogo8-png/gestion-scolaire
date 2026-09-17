"""Tests Deerflow depth — remises, SYSCOHADA, aging, réinscription, dossier PDF."""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.models import (
    AnneeScolaire,
    EcheancePaiement,
    EcritureComptable,
    Eleve,
    EleveFratrie,
    FraisScolaire,
    Fratrie,
    Inscription,
    RemiseRegle,
)
from app.services.remises import apply_remise_to_montant, compute_remise_eleve
from app.services.syscohada_ecritures import creer_ecritures_paiement


def _make_eleve(db, sid, classe, annee, *, suffix=None, boursier=False, taux=0):
    suffix = suffix or uuid.uuid4().hex[:6].upper()
    eleve = Eleve(
        id=uuid.uuid4(),
        matricule=f"2025M-D{suffix}",
        nom="Diallo",
        prenom=f"Awa{suffix[:3]}",
        date_naissance=date(2012, 5, 1),
        sexe="F",
        school_id=sid,
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
            est_boursier=boursier,
            taux_reduction=taux,
            date_inscription=date.today(),
            school_id=sid,
        )
    )
    return eleve


def test_compute_remise_fratrie_bourse_manuelle(db, annee_classe, default_school):
    sid = default_school.id
    annee = annee_classe["annee"]
    classe = annee_classe["classe"]

    e1 = _make_eleve(db, sid, classe, annee, suffix=f"F1{uuid.uuid4().hex[:4].upper()}", taux=5)
    e2 = _make_eleve(db, sid, classe, annee, suffix=f"F2{uuid.uuid4().hex[:4].upper()}", boursier=True)
    fratrie = Fratrie(id=uuid.uuid4(), school_id=sid, libelle="Famille Test")
    db.add(fratrie)
    db.flush()
    db.add(EleveFratrie(id=uuid.uuid4(), school_id=sid, id_eleve=e1.id, id_fratrie=fratrie.id))
    db.add(EleveFratrie(id=uuid.uuid4(), school_id=sid, id_eleve=e2.id, id_fratrie=fratrie.id))

    db.add(
        RemiseRegle(
            id=uuid.uuid4(),
            school_id=sid,
            code=f"FRAT-{uuid.uuid4().hex[:6]}",
            libelle="Fratrie 10%",
            type_remise="pourcent",
            valeur=Decimal(10),
            condition_type="fratrie",
            condition_valeur="2",
            actif=True,
            priorite=10,
        )
    )
    db.add(
        RemiseRegle(
            id=uuid.uuid4(),
            school_id=sid,
            code=f"BOUR-{uuid.uuid4().hex[:6]}",
            libelle="Bourse 20%",
            type_remise="pourcent",
            valeur=Decimal(20),
            condition_type="bourse",
            condition_valeur=None,
            actif=True,
            priorite=5,
        )
    )
    db.commit()

    r1 = compute_remise_eleve(db, e1.id, sid)
    assert r1["fratrie_count"] == 2
    assert r1["taux_percent"] >= 10  # fratrie + manuelle 5%
    assert any(s["condition_type"] == "fratrie" for s in r1["sources"])
    assert any(s.get("code") == "INSCRIPTION_TAUX" or s["condition_type"] == "manuelle" for s in r1["sources"])

    r2 = compute_remise_eleve(db, e2.id, sid)
    assert r2["est_boursier"] is True
    assert any(s["condition_type"] == "bourse" for s in r2["sources"])
    assert apply_remise_to_montant(100000, {"taux_percent": 10, "montant_fixe": 0}) == 90000.0


def test_remises_eleve_endpoint_and_arrieres(client, auth_headers, db, annee_classe, default_school):
    sid = default_school.id
    annee = annee_classe["annee"]
    classe = annee_classe["classe"]
    niveau = annee_classe["niveau"]
    suffix = uuid.uuid4().hex[:6].upper()
    eleve = _make_eleve(db, sid, classe, annee, suffix=suffix, taux=10)

    frais = FraisScolaire(
        id=uuid.uuid4(),
        id_niveau=niveau.id,
        id_annee=annee.id,
        motif=f"Scol-REM-{suffix}",
        montant_total=Decimal(100000),
        school_id=sid,
    )
    db.add(frais)
    db.flush()
    db.add(
        EcheancePaiement(
            id=uuid.uuid4(),
            id_frais=frais.id,
            libelle="T1",
            montant=Decimal(100000),
            date_echeance=date.today() - timedelta(days=5),
        )
    )
    db.commit()

    prev = client.get(f"/api/finance/remises/eleve/{eleve.id}", headers=auth_headers)
    assert prev.status_code == 200, prev.get_json()
    body = prev.get_json()
    assert body["taux_percent"] >= 10
    assert "sources" in body

    arr = client.get(
        f"/api/finance/arrieres?id_annee={annee.id}",
        headers=auth_headers,
    )
    assert arr.status_code == 200
    rows = arr.get_json()
    mine = next((r for r in rows if r["id_eleve"] == str(eleve.id)), None)
    assert mine is not None
    assert "remise" in mine
    assert mine["remise"]["taux_percent"] >= 10
    # Après 10% de remise manuelle
    assert mine["total_du"] == round(mine["total_du_brut"] * 0.9, 2)
    assert mine["arriere"] == mine["total_du"]  # aucun paiement


def test_syscohada_auto_ecriture_and_grand_livre(
    client, auth_headers, db, annee_classe, default_school
):
    sid = default_school.id
    annee = annee_classe["annee"]
    classe = annee_classe["classe"]
    eleve = _make_eleve(db, sid, classe, annee, suffix=uuid.uuid4().hex[:6].upper())
    db.commit()

    pay = client.post(
        "/api/finance/paiements",
        headers=auth_headers,
        json={
            "id_eleve": str(eleve.id),
            "id_annee": str(annee.id),
            "motif": "Scolarité",
            "montant_verse": 25000,
            "mode_paiement": "Espèces",
        },
    )
    assert pay.status_code == 201, pay.get_json()
    pid = pay.get_json()["id"]

    piece = f"PAIEMENT:{pid}"
    ecritures = (
        db.query(EcritureComptable)
        .filter(EcritureComptable.reference.like(f"{piece}%"))
        .all()
    )
    assert len(ecritures) >= 1
    assert any(e.compte_debit == "571" for e in ecritures)
    assert any(e.compte_credit == "4111" for e in ecritures)
    assert any(e.compte_credit == "7011" for e in ecritures)

    # Idempotence
    from app.models import Paiement

    paiement = db.query(Paiement).filter(Paiement.id == uuid.UUID(pid)).one()
    before = db.query(EcritureComptable).filter(EcritureComptable.id_paiement == paiement.id).count()
    creer_ecritures_paiement(db, paiement)
    db.commit()
    after = db.query(EcritureComptable).filter(EcritureComptable.id_paiement == paiement.id).count()
    assert after == before

    gl = client.get(
        "/api/comptabilite/grand-livre?compte=571",
        headers=auth_headers,
    )
    assert gl.status_code == 200
    data = gl.get_json()
    assert data["nb_lignes"] >= 1
    assert data["total_debit"] >= 25000

    bilan = client.get("/api/comptabilite/etats/bilan", headers=auth_headers)
    assert bilan.status_code == 200
    assert "actif" in bilan.get_json()
    assert "actif_detail" in bilan.get_json()

    cr = client.get("/api/comptabilite/etats/compte-resultat", headers=auth_headers)
    assert cr.status_code == 200
    assert cr.get_json()["total_produits"] >= 25000


def test_recouvrement_aging_buckets(client, auth_headers, db, annee_classe, default_school):
    sid = default_school.id
    annee = annee_classe["annee"]
    classe = annee_classe["classe"]
    niveau = annee_classe["niveau"]
    suffix = uuid.uuid4().hex[:6].upper()
    eleve = _make_eleve(db, sid, classe, annee, suffix=suffix)

    frais = FraisScolaire(
        id=uuid.uuid4(),
        id_niveau=niveau.id,
        id_annee=annee.id,
        motif=f"Scol-AGE-{suffix}",
        montant_total=Decimal(80000),
        school_id=sid,
    )
    db.add(frais)
    db.flush()
    # 45 jours de retard → bucket J31-60
    db.add(
        EcheancePaiement(
            id=uuid.uuid4(),
            id_frais=frais.id,
            libelle="T-old",
            montant=Decimal(80000),
            date_echeance=date.today() - timedelta(days=45),
        )
    )
    db.commit()

    r = client.get(
        f"/api/finance/recouvrement/detail?id_annee={annee.id}",
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "aging" in data
    for key in ("J0-30", "J31-60", "J61-90", "J90+"):
        assert key in data["aging"]
    assert data["aging"]["J31-60"]["montant"] >= 80000
    assert "by_classe" in data
    assert "by_motif" in data
    assert "top_debiteurs" in data
    assert any(d["id_eleve"] == str(eleve.id) for d in data["top_debiteurs"])


def test_reinscription_batch(client, auth_headers, db, annee_classe, default_school):
    sid = default_school.id
    annee = annee_classe["annee"]
    classe = annee_classe["classe"]
    suffix = uuid.uuid4().hex[:6].upper()
    eleve = _make_eleve(db, sid, classe, annee, suffix=suffix, boursier=True, taux=15)

    annee_cible = AnneeScolaire(
        id=uuid.uuid4(),
        school_id=sid,
        libelle=f"2026-2027-{suffix}",
        date_debut=date(2026, 9, 1),
        date_fin=date(2027, 6, 30),
        est_active=False,
    )
    db.add(annee_cible)
    db.commit()

    r = client.post(
        "/api/eleves/reinscription-batch",
        headers=auth_headers,
        json={
            "id_annee_source": str(annee.id),
            "id_annee_cible": str(annee_cible.id),
            "eleve_ids": [str(eleve.id)],
        },
    )
    assert r.status_code == 201, r.get_json()
    data = r.get_json()
    assert data["count_created"] == 1

    insc = (
        db.query(Inscription)
        .filter(
            Inscription.id_eleve == eleve.id,
            Inscription.id_annee == annee_cible.id,
        )
        .one()
    )
    assert insc.statut == "reinscrit"
    assert insc.est_boursier is True
    assert float(insc.taux_reduction) == 15.0

    # Idempotent skip
    r2 = client.post(
        "/api/eleves/reinscription-batch",
        headers=auth_headers,
        json={
            "id_annee_source": str(annee.id),
            "id_annee_cible": str(annee_cible.id),
            "eleve_ids": [str(eleve.id)],
        },
    )
    assert r2.status_code == 201
    assert r2.get_json()["count_created"] == 0
    assert r2.get_json()["count_skipped"] == 1


def test_dossier_pdf_endpoint(client, auth_headers, db, annee_classe, default_school, monkeypatch):
    sid = default_school.id
    annee = annee_classe["annee"]
    classe = annee_classe["classe"]
    eleve = _make_eleve(db, sid, classe, annee, suffix=uuid.uuid4().hex[:6].upper())
    db.commit()

    def _fake_pdf(html, filepath):
        with open(filepath, "wb") as f:
            f.write(b"%PDF-1.4 fake dossier")

    monkeypatch.setattr("app.services.pdf_render.html_to_pdf", _fake_pdf)
    # Also patch the import path used inside the view
    monkeypatch.setattr(
        "app.routes.eleves.html_to_pdf",
        _fake_pdf,
        raising=False,
    )

    # Patch at call site via module used inside get()
    import app.services.pdf_render as pdf_mod

    monkeypatch.setattr(pdf_mod, "html_to_pdf", _fake_pdf)

    r = client.get(f"/api/eleves/{eleve.id}/dossier.pdf", headers=auth_headers)
    assert r.status_code == 200
    assert r.headers.get("Content-Type", "").startswith("application/pdf") or r.data[:4] == b"%PDF"
