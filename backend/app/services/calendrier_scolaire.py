"""Vérification calendrier scolaire — dates bloquées pour programmation."""
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models import EvenementCalendrier, Inscription, Trimestre


def date_est_bloquee(db: Session, id_annee: uuid.UUID, d: date) -> tuple[bool, str | None]:
    """Retourne (True, libellé) si la date tombe sur un événement bloquant."""
    event = (
        db.query(EvenementCalendrier)
        .filter(
            EvenementCalendrier.id_annee == id_annee,
            EvenementCalendrier.bloque_programmation.is_(True),
            EvenementCalendrier.date_debut <= d,
            EvenementCalendrier.date_fin >= d,
        )
        .first()
    )
    if event:
        return True, event.libelle
    return False, None


def id_annee_pour_classe(db: Session, id_classe: uuid.UUID) -> uuid.UUID | None:
    from app.models import Classe

    classe = db.query(Classe).filter(Classe.id == id_classe).first()
    return classe.id_annee if classe else None


def id_annee_pour_trimestre(db: Session, id_trimestre: uuid.UUID) -> uuid.UUID | None:
    trim = db.query(Trimestre).filter(Trimestre.id == id_trimestre).first()
    return trim.id_annee if trim else None


def notifier_parents_classe(db, id_classe: uuid.UUID, type_notification: str, contenu: str):
    """Envoie une notification à tous les parents de la classe."""
    from app.services.envoi_notification import creer_notification

    inscriptions = (
        db.query(Inscription)
        .filter(Inscription.id_classe == id_classe, Inscription.statut.in_(("inscrit", "reinscrit")))
        .all()
    )
    for ins in inscriptions:
        creer_notification("sms", type_notification, contenu, id_eleve=ins.id_eleve)
