"""Relances automatiques aux parents pour arriérés de paiement."""
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Notification
from app.services.envoi_notification import (
    creer_notification,
    traiter_file_notifications,
)
from app.services.finance_arrieres import list_arrieres


def relancer_arrieres(
    db: Session,
    id_annee: uuid.UUID,
    canal: str = "email",
    min_jours_entre_relances: int = 7,
    auto_envoyer: bool = False,
) -> dict:
    """
    Crée des notifications de type retard_paiement pour chaque élève en arriéré.
    Évite les doublons si une relance a déjà été créée/envoyée récemment.
    """
    arrieres = list_arrieres(db, id_annee)
    seuil = datetime.now(UTC) - timedelta(days=min_jours_entre_relances)
    crees = 0
    ignores = 0

    for item in arrieres:
        id_eleve = item["id_eleve"]
        recente = (
            db.query(Notification)
            .filter(
                Notification.id_eleve == id_eleve,
                Notification.type_notification == "retard_paiement",
                Notification.created_at >= seuil,
            )
            .first()
        )
        if recente:
            ignores += 1
            continue

        montant = item["arriere"]
        contenu = (
            f"Bonjour, des frais scolaires restent impayés pour {item['prenom']} {item['nom']} "
            f"(matricule {item['matricule']}) : arriéré de {montant:,.0f} FCFA. "
            f"Merci de régulariser votre situation auprès du secrétariat."
        )
        creer_notification(
            canal=canal,
            type_notification="retard_paiement",
            contenu=contenu,
            id_eleve=id_eleve,
        )
        crees += 1

    envoyees = 0
    if auto_envoyer and crees:
        envoyees = traiter_file_notifications()

    return {
        "arrieres_total": len(arrieres),
        "notifications_crees": crees,
        "ignores_recents": ignores,
        "envoyees": envoyees,
    }
