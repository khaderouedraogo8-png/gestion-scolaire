"""Journal d'audit — consultation."""

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint

from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import JournalAudit, Utilisateur

blp = Blueprint("audit", __name__, description="Journal d'audit")


def _serialize_entry(db, entry):
    data = {
        "id": str(entry.id),
        "action": entry.action,
        "table_cible": entry.table_cible,
        "id_enregistrement_cible": str(entry.id_enregistrement_cible)
        if entry.id_enregistrement_cible
        else None,
        "ip_origine": str(entry.ip_origine) if entry.ip_origine else None,
        "details": entry.details,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }
    if entry.id_utilisateur:
        user = db.query(Utilisateur).filter(Utilisateur.id == entry.id_utilisateur).first()
        if user:
            data["utilisateur"] = f"{user.prenom} {user.nom}"
            data["email"] = user.email
    return data


@blp.route("")
class AuditList(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    def get(self):
        db = get_db()
        q = db.query(JournalAudit).order_by(JournalAudit.created_at.desc())
        action = request.args.get("action")
        if action:
            q = q.filter(JournalAudit.action == action)
        limit = min(int(request.args.get("limit", 100)), 500)
        offset = int(request.args.get("offset", 0))
        total = q.count()
        items = [_serialize_entry(db, e) for e in q.offset(offset).limit(limit).all()]
        return jsonify({"items": items, "total": total})
