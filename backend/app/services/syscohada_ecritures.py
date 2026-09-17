"""Génération d'écritures SYSCOHADA à partir des paiements."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import EcritureComptable, Paiement


def _compte_tresorerie(mode_paiement: str | None) -> str:
    mode = (mode_paiement or "").strip().lower()
    caisse_modes = {
        "especes",
        "espèces",
        "cash",
        "caisse",
        "espece",
    }
    if mode in caisse_modes:
        return "571"
    return "521"  # banque / chèque / virement / mobile money


def _compte_produit(motif: str | None) -> str:
    m = (motif or "").strip().lower()
    if any(k in m for k in ("inscription", "reinscription", "réinscription", "inscription")):
        return "7012"
    return "7011"


def creer_ecritures_paiement(
    db: Session,
    paiement: Paiement,
    *,
    saisi_par: uuid.UUID | None = None,
) -> list[EcritureComptable]:
    """Crée les écritures d'encaissement (idempotent via reference PAIEMENT:{id}).

    - Débit 521/571 (banque/caisse) / Crédit 4111 (élèves)
    - Débit 4111 / Crédit 7011|7012 (produit selon motif)
    Effet net : Dr trésorerie / Cr produit.
    """
    piece_ref = f"PAIEMENT:{paiement.id}"
    existing = (
        db.query(EcritureComptable)
        .filter(
            EcritureComptable.school_id == paiement.school_id,
            EcritureComptable.reference == piece_ref,
        )
        .first()
    )
    if existing:
        return (
            db.query(EcritureComptable)
            .filter(
                EcritureComptable.school_id == paiement.school_id,
                EcritureComptable.reference.in_([piece_ref, f"{piece_ref}:REV"]),
            )
            .all()
        )

    montant = Decimal(str(paiement.montant_verse))
    if montant <= 0:
        return []

    date_ecr = (
        paiement.date_paiement.date()
        if getattr(paiement.date_paiement, "date", None)
        else (paiement.date_paiement or date.today())
    )
    if not isinstance(date_ecr, date):
        date_ecr = date.today()

    treso = _compte_tresorerie(paiement.mode_paiement)
    produit = _compte_produit(paiement.motif)
    libelle = f"Paiement {paiement.numero_recu} — {paiement.motif}"

    e1 = EcritureComptable(
        id=uuid.uuid4(),
        school_id=paiement.school_id,
        date_ecriture=date_ecr,
        libelle=libelle,
        compte_debit=treso,
        compte_credit="4111",
        montant=montant,
        reference=piece_ref,
        id_paiement=paiement.id,
        journal="CAISSE" if treso == "571" else "BANQUE",
        saisi_par=saisi_par,
    )
    e2 = EcritureComptable(
        id=uuid.uuid4(),
        school_id=paiement.school_id,
        date_ecriture=date_ecr,
        libelle=f"Produit scolarité — {paiement.numero_recu}",
        compte_debit="4111",
        compte_credit=produit,
        montant=montant,
        reference=f"{piece_ref}:REV",
        id_paiement=paiement.id,
        journal="OD",
        saisi_par=saisi_par,
    )
    db.add(e1)
    db.add(e2)
    return [e1, e2]
