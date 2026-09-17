"""Tests d'intégration — finance."""
import uuid


class TestFinance:
    def test_create_frais(self, client, auth_headers, annee_classe):
        motif = f"Scolarité-{uuid.uuid4().hex[:8]}"
        response = client.post(
            "/api/finance/frais",
            headers=auth_headers,
            json={
                "id_niveau": str(annee_classe["niveau"].id),
                "id_annee": str(annee_classe["annee"].id),
                "motif": motif,
                "montant_total": 150000,
            },
        )
        assert response.status_code == 201, response.get_json()

    def test_encaissement_et_annulation(self, client, auth_headers, db, annee_classe, default_school):
        from app.models import Eleve, Inscription

        sid = default_school.id
        matricule = f"2025M-{uuid.uuid4().hex[:6].upper()}"
        eleve = Eleve(
            id=uuid.uuid4(),
            matricule=matricule,
            nom="Test",
            prenom="Finance",
            school_id=sid,
        )
        db.add(eleve)
        inscription = Inscription(
            id=uuid.uuid4(),
            id_eleve=eleve.id,
            id_classe=annee_classe["classe"].id,
            id_annee=annee_classe["annee"].id,
            school_id=sid,
        )
        db.add(inscription)
        db.commit()

        pay_resp = client.post(
            "/api/finance/paiements",
            headers=auth_headers,
            json={
                "id_eleve": str(eleve.id),
                "id_annee": str(annee_classe["annee"].id),
                "motif": "Scolarité",
                "montant_verse": 50000,
                "mode_paiement": "Espèces",
            },
        )
        assert pay_resp.status_code == 201
        paiement = pay_resp.get_json()
        assert paiement["numero_recu"].startswith("REC-")
        assert paiement["annule"] is False

        # Annulation (pas de DELETE)
        annul_resp = client.post(
            f"/api/finance/paiements/{paiement['id']}/annuler",
            headers=auth_headers,
            json={"motif_annulation": "Erreur de saisie"},
        )
        assert annul_resp.status_code == 200
        assert annul_resp.get_json()["annule"] is True
