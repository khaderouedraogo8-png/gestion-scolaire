"""Calcul des arriérés scolaires par élève (échéances échues uniquement)."""
import uuid
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

# total_du = somme des échéances dont date_echeance <= today
_ARREARS_QUERY = """
    SELECT
        i.id_eleve,
        e.matricule,
        e.nom,
        e.prenom,
        COALESCE(SUM(ec.montant), 0) AS total_du,
        COALESCE((
            SELECT SUM(p.montant_verse)
            FROM paiement p
            WHERE p.id_eleve = i.id_eleve
              AND p.id_annee = :id_annee
              AND p.school_id = :school_id
              AND p.annule = false
        ), 0) AS total_paye
    FROM inscription i
    JOIN eleve e ON e.id = i.id_eleve AND e.school_id = :school_id
    JOIN classe c ON c.id = i.id_classe AND c.school_id = :school_id
    JOIN frais_scolaire fs ON fs.id_niveau = c.id_niveau
        AND fs.id_annee = i.id_annee
        AND fs.school_id = :school_id
    JOIN echeance_paiement ec ON ec.id_frais = fs.id
        AND ec.date_echeance <= :as_of
    WHERE i.id_annee = :id_annee
      AND i.school_id = :school_id
      AND i.statut IN ('inscrit', 'reinscrit')
"""
_ARREARS_FILTER_CLASSE = "AND i.id_classe = :id_classe\n"
_ARREARS_GROUP = "GROUP BY i.id_eleve, e.matricule, e.nom, e.prenom"

# Détail par échéance pour relances calendaires
_ECHEANCES_DUES_QUERY = """
    SELECT
        i.id_eleve,
        e.matricule,
        e.nom,
        e.prenom,
        ec.id AS id_echeance,
        ec.libelle,
        ec.montant,
        ec.date_echeance,
        fs.motif,
        COALESCE((
            SELECT SUM(p.montant_verse)
            FROM paiement p
            WHERE p.id_eleve = i.id_eleve
              AND p.id_annee = :id_annee
              AND p.school_id = :school_id
              AND p.annule = false
              AND (p.id_echeance = ec.id OR p.id_echeance IS NULL)
        ), 0) AS paye_echeance
    FROM inscription i
    JOIN eleve e ON e.id = i.id_eleve AND e.school_id = :school_id
    JOIN classe c ON c.id = i.id_classe AND c.school_id = :school_id
    JOIN frais_scolaire fs ON fs.id_niveau = c.id_niveau
        AND fs.id_annee = i.id_annee
        AND fs.school_id = :school_id
    JOIN echeance_paiement ec ON ec.id_frais = fs.id
    WHERE i.id_annee = :id_annee
      AND i.school_id = :school_id
      AND i.statut IN ('inscrit', 'reinscrit')
"""


def list_arrieres(
    db: Session,
    id_annee: uuid.UUID,
    id_classe: uuid.UUID | None = None,
    school_id: uuid.UUID | None = None,
    as_of: date | None = None,
) -> list[dict]:
    """Retourne les élèves avec un solde impayé (échéances échues à as_of)."""
    if school_id is None:
        from app.services.tenant import get_current_school_id

        school_id = get_current_school_id()
    as_of = as_of or date.today()
    params: dict = {"id_annee": id_annee, "school_id": school_id, "as_of": as_of}
    sql = _ARREARS_QUERY
    if id_classe:
        sql += _ARREARS_FILTER_CLASSE
        params["id_classe"] = id_classe
    sql += _ARREARS_GROUP

    rows = db.execute(text(sql), params).fetchall()

    arrieres = []
    for r in rows:
        total_du = float(r[4])
        total_paye = float(r[5])
        reste = total_du - total_paye
        if reste > 0:
            arrieres.append({
                "id_eleve": r[0],
                "matricule": r[1],
                "nom": r[2],
                "prenom": r[3],
                "total_du": total_du,
                "total_paye": total_paye,
                "arriere": round(reste, 2),
                "as_of": as_of.isoformat(),
            })
    return arrieres


def list_echeances_impayees(
    db: Session,
    id_annee: uuid.UUID,
    school_id: uuid.UUID | None = None,
    as_of: date | None = None,
) -> list[dict]:
    """Échéances avec reste dû (pour relances J-7 / J-1 / J+3)."""
    if school_id is None:
        from app.services.tenant import get_current_school_id

        school_id = get_current_school_id()
    as_of = as_of or date.today()
    rows = db.execute(
        text(_ECHEANCES_DUES_QUERY),
        {"id_annee": id_annee, "school_id": school_id},
    ).fetchall()
    out = []
    for r in rows:
        montant = float(r[6])
        # Approximation : si paiements sans id_echeance, on ne double-compte pas
        # trop agressivement — le reste global reste dans list_arrieres.
        paye = float(r[9])
        # Pour les paiements sans id_echeance, paye_echeance inclut tout → plafonner
        reste = max(0.0, montant - min(paye, montant))
        if reste <= 0:
            continue
        out.append({
            "id_eleve": r[0],
            "matricule": r[1],
            "nom": r[2],
            "prenom": r[3],
            "id_echeance": r[4],
            "libelle": r[5],
            "montant": montant,
            "date_echeance": r[7],
            "motif": r[8],
            "reste": round(reste, 2),
            "jours_relatifs": (r[7] - as_of).days if r[7] else None,
        })
    return out
