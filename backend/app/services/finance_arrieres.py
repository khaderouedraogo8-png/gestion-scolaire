"""Calcul des arriérés scolaires par élève."""
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

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
    WHERE i.id_annee = :id_annee
      AND i.school_id = :school_id
      AND i.statut IN ('inscrit', 'reinscrit')
"""
_ARREARS_FILTER_CLASSE = "AND i.id_classe = :id_classe\n"
_ARREARS_GROUP = "GROUP BY i.id_eleve, e.matricule, e.nom, e.prenom"


def list_arrieres(
    db: Session,
    id_annee: uuid.UUID,
    id_classe: uuid.UUID | None = None,
    school_id: uuid.UUID | None = None,
) -> list[dict]:
    """Retourne les élèves avec un solde impayé pour l'année donnée."""
    if school_id is None:
        from app.services.tenant import get_current_school_id

        school_id = get_current_school_id()
    params: dict = {"id_annee": id_annee, "school_id": school_id}
    sql = _ARREARS_QUERY
    if id_classe:
        sql += _ARREARS_FILTER_CLASSE
        params["id_classe"] = id_classe
    sql += _ARREARS_GROUP

    rows = db.execute(
        text(sql),
        params,
    ).fetchall()

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
            })
    return arrieres
