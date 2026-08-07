"""Journal d'audit pour actions sensibles."""
import uuid

from flask import request

from app.extensions import get_db
from app.models import JournalAudit


def log_audit(
    action: str,
    id_utilisateur: uuid.UUID | None = None,
    table_cible: str | None = None,
    id_enregistrement: uuid.UUID | None = None,
    details: dict | None = None,
):
    """
    Enregistre une entrée dans journal_audit.
    Actions typiques : MODIFICATION_NOTE, VALIDATION_BULLETIN, PAIEMENT_ENCAISSE,
    PAIEMENT_ANNULE, CONNEXION, ECHEC_CONNEXION.
    """
    db = get_db()
    entry = JournalAudit(
        id=uuid.uuid4(),
        id_utilisateur=id_utilisateur,
        action=action,
        table_cible=table_cible,
        id_enregistrement_cible=id_enregistrement,
        ip_origine=request.remote_addr,
        details=details,
    )
    db.add(entry)
    db.commit()
    return entry
