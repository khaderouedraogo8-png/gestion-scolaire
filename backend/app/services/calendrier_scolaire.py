"""Vérification calendrier scolaire — dates bloquées pour programmation."""
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models import AnneeScolaire, Classe, EvenementCalendrier, Inscription, Trimestre
from app.services.tenant import get_current_school_id, get_or_404_tenant, tenant_query


def date_est_bloquee(db: Session, id_annee: uuid.UUID, d: date) -> tuple[bool, str | None]:
    """Retourne (True, libellé) si la date tombe sur un événement bloquant."""
    get_or_404_tenant(AnneeScolaire, id_annee)
    event = (
        db.query(EvenementCalendrier)
        .join(AnneeScolaire, EvenementCalendrier.id_annee == AnneeScolaire.id)
        .filter(
            EvenementCalendrier.id_annee == id_annee,
            EvenementCalendrier.bloque_programmation.is_(True),
            EvenementCalendrier.date_debut <= d,
            EvenementCalendrier.date_fin >= d,
            AnneeScolaire.school_id == get_current_school_id(),
        )
        .first()
    )
    if event:
        return True, event.libelle
    return False, None


def id_annee_pour_classe(db: Session, id_classe: uuid.UUID) -> uuid.UUID | None:
    classe = get_or_404_tenant(Classe, id_classe)
    return classe.id_annee


def id_annee_pour_trimestre(db: Session, id_trimestre: uuid.UUID) -> uuid.UUID | None:
    trim = (
        db.query(Trimestre)
        .join(AnneeScolaire, Trimestre.id_annee == AnneeScolaire.id)
        .filter(
            Trimestre.id == id_trimestre,
            AnneeScolaire.school_id == get_current_school_id(),
        )
        .first()
    )
    return trim.id_annee if trim else None


def notifier_parents_classe(db, id_classe: uuid.UUID, type_notification: str, contenu: str):
    """Envoie une notification à tous les parents de la classe."""
    from app.services.envoi_notification import creer_notification

    get_or_404_tenant(Classe, id_classe)
    inscriptions = (
        tenant_query(Inscription)
        .filter(Inscription.id_classe == id_classe, Inscription.statut.in_(("inscrit", "reinscrit")))
        .all()
    )
    for ins in inscriptions:
        creer_notification("sms", type_notification, contenu, id_eleve=ins.id_eleve)
