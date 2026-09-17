"""Module 7 — Routes notifications."""
from datetime import UTC, datetime

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import Notification, ParentTuteur
from app.schemas.documents import NotificationCreateSchema, NotificationSchema
from app.services.envoi_notification import (
    creer_notification,
    traiter_file_notifications,
)
from app.services.tenant import get_or_404_tenant, tenant_query

blp = Blueprint("notifications", __name__, url_prefix="/notifications", description="Notifications")


def _parent_for_user(user) -> ParentTuteur | None:
    db = get_db()
    q = db.query(ParentTuteur).filter(ParentTuteur.id_utilisateur == user.id)
    if user.school_id:
        q = q.filter(ParentTuteur.school_id == user.school_id)
    return q.first()


@blp.route("/")
class NotificationsResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.response(200, NotificationSchema(many=True))
    def get(self):
        q = tenant_query(Notification)
        statut = request.args.get("statut")
        if statut:
            q = q.filter(Notification.statut == statut)
        type_notif = request.args.get("type_notification")
        if type_notif:
            q = q.filter(Notification.type_notification == type_notif)
        return q.order_by(Notification.created_at.desc()).limit(100).all()

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(NotificationCreateSchema)
    @blp.response(201, NotificationSchema)
    def post(self, data):
        notif = creer_notification(**data)
        return notif, 201


@blp.route("/me")
class ParentInboxResource(MethodView):
    """Boîte de réception parent — uniquement ses notifications."""

    @jwt_required()
    @require_role("parent")
    def get(self):
        user = get_current_user()
        parent = _parent_for_user(user)
        if not parent:
            return jsonify({"items": [], "total": 0, "non_lues": 0})

        q = (
            tenant_query(Notification)
            .filter(Notification.id_parent == parent.id)
            .order_by(Notification.created_at.desc())
        )
        # Inbox : notifications internes + copies email/sms destinées au parent
        rows = q.limit(100).all()
        # Dédupliquer par type+contenu+jour pour ne pas afficher double interne+email
        seen = set()
        items = []
        for n in rows:
            dedupe = (n.type_notification, (n.contenu or "")[:80], n.created_at.date() if n.created_at else None)
            if n.canal != "interne" and dedupe in seen:
                continue
            if n.canal == "interne":
                seen.add(dedupe)
            items.append({
                "id": str(n.id),
                "type_notification": n.type_notification,
                "contenu": n.contenu,
                "canal": n.canal,
                "statut": n.statut,
                "lu": n.lu_le is not None,
                "lu_le": n.lu_le.isoformat() if n.lu_le else None,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "id_eleve": str(n.id_eleve) if n.id_eleve else None,
            })
        non_lues = sum(1 for i in items if not i["lu"])
        return jsonify({"items": items, "total": len(items), "non_lues": non_lues})


@blp.route("/me/<uuid:id_notification>/lu")
class ParentMarkReadResource(MethodView):
    @jwt_required()
    @require_role("parent")
    def post(self, id_notification):
        user = get_current_user()
        parent = _parent_for_user(user)
        if not parent:
            return jsonify({"message": "Accès refusé"}), 403
        notif = get_or_404_tenant(Notification, id_notification)
        if notif.id_parent != parent.id:
            return jsonify({"message": "Accès refusé"}), 403
        if notif.lu_le is None:
            notif.lu_le = datetime.now(UTC)
            get_db().commit()
        return jsonify({
            "id": str(notif.id),
            "lu": True,
            "lu_le": notif.lu_le.isoformat() if notif.lu_le else None,
        })


@blp.route("/digest-absences")
class DigestAbsencesResource(MethodView):
    """Déclenche manuellement le digest hebdomadaire (admin/direction)."""

    @jwt_required()
    @require_role("administrateur", "directeur")
    def post(self):
        from app.services.digest_absences import digest_absences_hebdo
        from app.services.tenant import get_current_school_id

        db = get_db()
        body = request.get_json(silent=True) or {}
        canal = body.get("canal", "email")
        auto_envoyer = bool(body.get("auto_envoyer", False))
        result = digest_absences_hebdo(
            db,
            get_current_school_id(),
            canal=canal,
            auto_envoyer=auto_envoyer,
        )
        return jsonify(result)


@blp.route("/traiter")
class TraiterNotifications(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    def post(self):
        sent = traiter_file_notifications()
        return jsonify({"message": f"{sent} notification(s) envoyée(s)", "envoyees": sent})


@blp.route("/<uuid:id_notification>/retry")
class RetryNotification(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def post(self, id_notification):
        db = get_db()
        notif = get_or_404_tenant(Notification, id_notification)
        if notif.canal == "interne":
            return jsonify({"message": "Notification interne — pas de retry"}), 400
        notif.statut = "en_attente"
        notif.tentative_count = 0
        db.commit()
        return NotificationSchema().dump(notif)


@blp.route("/whatsapp-bot/inbound")
class WhatsAppBotInboundSandbox(MethodView):
    """Sandbox bot parent — POST {from, text} → {reply} sans Meta."""

    def post(self):
        from app.services.whatsapp_bot import handle_inbound

        payload = request.get_json(silent=True) or {}
        telephone = str(payload.get("from") or payload.get("telephone") or "")
        text = str(payload.get("text") or payload.get("message") or "")
        if not telephone:
            return jsonify({"message": "Champ 'from' requis"}), 400
        result = handle_inbound(telephone, text, send=False)
        return jsonify(result), 200
