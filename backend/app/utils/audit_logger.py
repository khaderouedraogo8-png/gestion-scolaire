"""Journal d'audit pour actions sensibles."""
import uuid

from flask import has_request_context, request

from app.extensions import get_db
from app.models import JournalAudit, Utilisateur


def log_audit(
    action: str,
    id_utilisateur: uuid.UUID | None = None,
    table_cible: str | None = None,
    id_enregistrement: uuid.UUID | None = None,
    details: dict | None = None,
    school_id: uuid.UUID | None = None,
):
    """
    Enregistre une entrée dans journal_audit.
    Actions typiques : MODIFICATION_NOTE, VALIDATION_BULLETIN, PAIEMENT_ENCAISSE,
    PAIEMENT_ANNULE, CONNEXION, ECHEC_CONNEXION.
    """
    db = get_db()

    if school_id is None and id_utilisateur:
        user = db.query(Utilisateur).filter(Utilisateur.id == id_utilisateur).first()
        if user and user.school_id:
            school_id = user.school_id

    if school_id is None:
        try:
            from app.services.tenant import get_current_school_id

            school_id = get_current_school_id()
        except Exception:
            school_id = None

    if school_id is None:
        # Sans tenant résolvable : ne pas écrire (évite IntegrityError NOT NULL)
        return None

    entry = JournalAudit(
        id=uuid.uuid4(),
        school_id=school_id,
        id_utilisateur=id_utilisateur,
        action=action,
        table_cible=table_cible,
        id_enregistrement_cible=id_enregistrement,
        ip_origine=request.remote_addr if has_request_context() else None,
        details=details,
    )
    db.add(entry)
    db.commit()
    return entry
