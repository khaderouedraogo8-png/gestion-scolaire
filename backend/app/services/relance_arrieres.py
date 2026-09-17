"""Relances automatiques aux parents — calendrier J-7 / J-1 / J+3 par échéance."""
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Notification
from app.services.envoi_notification import (
    creer_notification,
    traiter_file_notifications,
)
from app.services.finance_arrieres import list_arrieres, list_echeances_impayees

# Fenêtres de relance relatives à date_echeance (jours)
RELANCE_OFFSETS = (-7, -1, 3)


def _fenetre_pour_jours(jours_relatifs: int | None) -> str | None:
    """Mappe l'écart (échéance - today) vers une fenêtre de relance."""
    if jours_relatifs is None:
        return None
    # jours_relatifs = date_echeance - today → J-7 => +7, J-1 => +1, J+3 => -3
    mapping = {7: "J-7", 1: "J-1", -3: "J+3"}
    return mapping.get(jours_relatifs)


def relancer_arrieres(
    db: Session,
    id_annee: uuid.UUID,
    canal: str = "email",
    min_jours_entre_relances: int = 1,
    auto_envoyer: bool = False,
    school_id: uuid.UUID | None = None,
    as_of: date | None = None,
    mode: str = "calendaire",
) -> dict:
    """
    Crée des notifications retard_paiement.

    mode=calendaire : uniquement échéances en fenêtre J-7 / J-1 / J+3.
    mode=global : comportement legacy (tous les arriérés, dédup N jours).
    """
    if school_id is None:
        from app.services.tenant import get_current_school_id

        school_id = get_current_school_id()

    as_of = as_of or date.today()
    crees = 0
    ignores = 0
    detail_fenetres = {"J-7": 0, "J-1": 0, "J+3": 0, "global": 0}

    if mode == "calendaire":
        items = list_echeances_impayees(db, id_annee, school_id=school_id, as_of=as_of)
        for item in items:
            fenetre = _fenetre_pour_jours(item.get("jours_relatifs"))
            if not fenetre:
                continue
            # idempotency_key ≤ 120 chars en DB
            short_eid = str(item["id_echeance"]).replace("-", "")[:12]
            short_eleve = str(item["id_eleve"]).replace("-", "")[:12]
            idem = f"rel:{short_eleve}:{short_eid}:{fenetre}"
            existing = (
                db.query(Notification)
                .filter(
                    Notification.school_id == school_id,
                    Notification.idempotency_key == idem,
                )
                .first()
            )
            if existing:
                ignores += 1
                continue

            contenu = (
                f"Rappel ({fenetre}) — échéance « {item['libelle'] or 'Tranche'} » "
                f"({item['date_echeance']}) pour {item['prenom']} {item['nom']} "
                f"(matricule {item['matricule']}) : reste {item['reste']:,.0f} FCFA "
                f"({item['motif']}). Merci de régulariser auprès du secrétariat."
            )
            creer_notification(
                canal=canal,
                type_notification="retard_paiement",
                contenu=contenu,
                id_eleve=item["id_eleve"],
                school_id=school_id,
                idempotency_key=idem,
            )
            crees += 1
            detail_fenetres[fenetre] += 1
    else:
        arrieres = list_arrieres(db, id_annee, school_id=school_id, as_of=as_of)
        seuil = datetime.now(UTC) - timedelta(days=min_jours_entre_relances)
        for item in arrieres:
            id_eleve = item["id_eleve"]
            recente = (
                db.query(Notification)
                .filter(
                    Notification.school_id == school_id,
                    Notification.id_eleve == id_eleve,
                    Notification.type_notification == "retard_paiement",
                    Notification.created_at >= seuil,
                )
                .first()
            )
            if recente:
                ignores += 1
                continue
            contenu = (
                f"Bonjour, des frais scolaires restent impayés pour {item['prenom']} {item['nom']} "
                f"(matricule {item['matricule']}) : arriéré de {item['arriere']:,.0f} FCFA. "
                f"Merci de régulariser votre situation auprès du secrétariat."
            )
            creer_notification(
                canal=canal,
                type_notification="retard_paiement",
                contenu=contenu,
                id_eleve=id_eleve,
                school_id=school_id,
            )
            crees += 1
            detail_fenetres["global"] += 1

    envoyees = 0
    if auto_envoyer and crees:
        envoyees = traiter_file_notifications(school_id=school_id)

    return {
        "arrieres_total": crees + ignores,
        "notifications_crees": crees,
        "ignores_recents": ignores,
        "envoyees": envoyees,
        "mode": mode,
        "as_of": as_of.isoformat(),
        "fenetres": detail_fenetres,
        "canal": canal,
    }
