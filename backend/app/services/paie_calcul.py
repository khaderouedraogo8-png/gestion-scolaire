"""Calcul de paie et écritures SYSCOHADA associées."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from flask import current_app
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import (
    AffectationEnseignant,
    EcritureComptable,
    Enseignant,
    PaieLigne,
    PaiePeriode,
    RhContrat,
)
from app.services.tenant import apply_tenant_school, tenant_query


def _money(value: Decimal | float | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _semaines_periode(debut: date, fin: date) -> Decimal:
    days = max((fin - debut).days + 1, 1)
    return _money(Decimal(days) / Decimal(7))


def _heures_defaut(db: Session, enseignant_id: uuid.UUID, periode: PaiePeriode) -> Decimal:
    volumes = (
        tenant_query(AffectationEnseignant)
        .filter(AffectationEnseignant.id_enseignant == enseignant_id)
        .all()
    )
    hebdo = sum(
        (Decimal(str(a.volume_horaire_hebdo or 0)) for a in volumes),
        Decimal(0),
    )
    if hebdo <= 0:
        return Decimal(0)
    return _money(hebdo * _semaines_periode(periode.date_debut, periode.date_fin))


def calculer_paie_periode(
    db: Session,
    periode: PaiePeriode,
    *,
    taux_retenue: float | None = None,
    heures_map: dict[str, float] | None = None,
    saisi_par: uuid.UUID | None = None,
    replace_lignes: bool = True,
) -> dict:
    """Calcule les lignes de paie + écritures SYSCOHADA pour une période.

    Pour chaque enseignant ayant un RhContrat actif (salaire fixe) ou un
    taux_horaire : brut = salaire_base ou heures × taux ; retenues = % CNSS-like
    (défaut 5.5 %) ; net = brut − retenues.
    """
    cfg = current_app.config
    taux = Decimal(str(taux_retenue if taux_retenue is not None else cfg.get("PAIE_TAUX_RETENUE", 0.055)))
    compte_charge = cfg.get("PAIE_COMPTE_CHARGE", "661")
    compte_personnel = cfg.get("PAIE_COMPTE_PERSONNEL", "421")
    compte_social = cfg.get("PAIE_COMPTE_CHARGES_SOCIALES", "431")
    heures_map = heures_map or {}

    today = date.today()
    contrats = (
        tenant_query(RhContrat)
        .filter(
            RhContrat.statut == "actif",
            RhContrat.id_enseignant.isnot(None),
            RhContrat.date_debut <= periode.date_fin,
            or_(RhContrat.date_fin.is_(None), RhContrat.date_fin >= periode.date_debut),
        )
        .all()
    )
    contrat_by_ens = {c.id_enseignant: c for c in contrats if c.id_enseignant}

    enseignants = tenant_query(Enseignant).all()
    cibles: list[tuple[Enseignant, RhContrat | None]] = []
    for ens in enseignants:
        contrat = contrat_by_ens.get(ens.id)
        if contrat or ens.taux_horaire is not None:
            cibles.append((ens, contrat))

    if replace_lignes:
        existing = (
            tenant_query(PaieLigne).filter(PaieLigne.id_periode == periode.id).all()
        )
        for row in existing:
            db.delete(row)
        db.flush()

    lignes: list[PaieLigne] = []
    total_brut = Decimal(0)
    total_retenues = Decimal(0)
    total_net = Decimal(0)

    for ens, contrat in cibles:
        mode = "fixe"
        heures = Decimal(0)
        brut = Decimal(0)
        if contrat and contrat.salaire_base is not None:
            brut = _money(contrat.salaire_base)
            mode = "salaire_fixe"
        elif ens.taux_horaire is not None:
            key = str(ens.id)
            if key in heures_map:
                heures = _money(heures_map[key])
            else:
                heures = _heures_defaut(db, ens.id, periode)
            brut = _money(Decimal(str(ens.taux_horaire)) * heures)
            mode = "horaire"
        else:
            continue

        if brut <= 0:
            continue

        retenues = _money(brut * taux)
        net = _money(brut - retenues)
        details = {
            "mode": mode,
            "heures": float(heures),
            "taux_horaire": float(ens.taux_horaire) if ens.taux_horaire is not None else None,
            "taux_retenue": float(taux),
            "id_contrat": str(contrat.id) if contrat else None,
            "nom": ens.nom,
            "prenom": ens.prenom,
        }
        ligne = PaieLigne(
            id=uuid.uuid4(),
            id_periode=periode.id,
            id_utilisateur=ens.id_utilisateur,
            id_enseignant=ens.id,
            matricule=None,
            brut=brut,
            retenues=retenues,
            net=net,
            details=details,
        )
        apply_tenant_school(ligne)
        db.add(ligne)
        lignes.append(ligne)
        total_brut += brut
        total_retenues += retenues
        total_net += net

    # Écritures SYSCOHADA (idempotentes via référence PAIE:{periode_id})
    piece = f"PAIE:{periode.id}"
    old_ecr = (
        db.query(EcritureComptable)
        .filter(
            EcritureComptable.school_id == periode.school_id,
            EcritureComptable.reference.like(f"{piece}%"),
        )
        .all()
    )
    for e in old_ecr:
        db.delete(e)
    db.flush()

    ecritures: list[EcritureComptable] = []
    if total_brut > 0:
        e_brut = EcritureComptable(
            id=uuid.uuid4(),
            school_id=periode.school_id,
            date_ecriture=periode.date_fin or today,
            libelle=f"Paie {periode.libelle} — charges personnel",
            compte_debit=compte_charge,
            compte_credit=compte_personnel,
            montant=total_brut,
            reference=piece,
            journal="PAIE",
            saisi_par=saisi_par,
        )
        db.add(e_brut)
        ecritures.append(e_brut)
    if total_retenues > 0:
        e_ret = EcritureComptable(
            id=uuid.uuid4(),
            school_id=periode.school_id,
            date_ecriture=periode.date_fin or today,
            libelle=f"Paie {periode.libelle} — retenues sociales",
            compte_debit=compte_personnel,
            compte_credit=compte_social,
            montant=total_retenues,
            reference=f"{piece}:RET",
            journal="PAIE",
            saisi_par=saisi_par,
        )
        db.add(e_ret)
        ecritures.append(e_ret)

    db.commit()
    for ligne in lignes:
        db.refresh(ligne)

    return {
        "periode": periode,
        "lignes": lignes,
        "totaux": {
            "brut": float(total_brut),
            "retenues": float(total_retenues),
            "net": float(total_net),
            "nb_lignes": len(lignes),
        },
        "taux_retenue": float(taux),
        "ecritures": [
            {
                "id": str(e.id),
                "compte_debit": e.compte_debit,
                "compte_credit": e.compte_credit,
                "montant": float(e.montant),
                "reference": e.reference,
            }
            for e in ecritures
        ],
    }
