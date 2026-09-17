"""Calcul des arriérés scolaires par élève (échéances échues uniquement)."""
import uuid
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.remises import apply_remise_to_montant, get_remise_cached

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
        ), 0) AS paye_echeance,
        i.id_classe
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
    """Retourne les élèves avec un solde impayé (échéances échues à as_of, après remises)."""
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
    remise_cache: dict = {}

    arrieres = []
    for r in rows:
        total_du_brut = float(r[4])
        total_paye = float(r[5])
        remise = get_remise_cached(db, r[0], school_id, remise_cache)
        total_du = apply_remise_to_montant(total_du_brut, remise)
        reste = total_du - total_paye
        if reste > 0:
            arrieres.append({
                "id_eleve": r[0],
                "matricule": r[1],
                "nom": r[2],
                "prenom": r[3],
                "total_du_brut": round(total_du_brut, 2),
                "total_du": total_du,
                "total_paye": total_paye,
                "arriere": round(reste, 2),
                "remise": {
                    "taux_percent": remise["taux_percent"],
                    "montant_fixe": remise["montant_fixe"],
                    "sources": remise["sources"],
                },
                "as_of": as_of.isoformat(),
            })
    return arrieres


def list_echeances_impayees(
    db: Session,
    id_annee: uuid.UUID,
    school_id: uuid.UUID | None = None,
    as_of: date | None = None,
) -> list[dict]:
    """Échéances avec reste dû après remise (pour relances / aging)."""
    if school_id is None:
        from app.services.tenant import get_current_school_id

        school_id = get_current_school_id()
    as_of = as_of or date.today()
    rows = db.execute(
        text(_ECHEANCES_DUES_QUERY),
        {"id_annee": id_annee, "school_id": school_id},
    ).fetchall()
    remise_cache: dict = {}
    out = []
    for r in rows:
        montant_brut = float(r[6])
        paye = float(r[9])
        remise = get_remise_cached(db, r[0], school_id, remise_cache)
        montant = apply_remise_to_montant(montant_brut, remise)
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
            "montant_brut": montant_brut,
            "montant": montant,
            "date_echeance": r[7],
            "motif": r[8],
            "id_classe": r[10],
            "reste": round(reste, 2),
            "jours_relatifs": (r[7] - as_of).days if r[7] else None,
            "remise": {
                "taux_percent": remise["taux_percent"],
                "montant_fixe": remise["montant_fixe"],
            },
        })
    return out
