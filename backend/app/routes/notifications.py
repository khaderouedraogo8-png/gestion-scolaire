"""Module 7 — Routes notifications."""

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint

from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import Notification
from app.schemas.documents import NotificationCreateSchema, NotificationSchema
from app.services.envoi_notification import (
    creer_notification,
    traiter_file_notifications,
)
from app.services.tenant import get_or_404_tenant, tenant_query

blp = Blueprint("notifications", __name__, url_prefix="/notifications", description="Notifications")


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
        return q.order_by(Notification.created_at.desc()).limit(100).all()

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(NotificationCreateSchema)
    @blp.response(201, NotificationSchema)
    def post(self, data):
        notif = creer_notification(**data)
        return notif, 201


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
        notif.statut = "en_attente"
        notif.tentative_count = 0
        db.commit()
        return NotificationSchema().dump(notif)
