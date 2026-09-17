"""Envoi de notifications — pattern adaptateur NotificationProvider."""
import json
import smtplib
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from email.mime.text import MIMEText
from http.client import HTTPConnection, HTTPSConnection
from urllib.parse import urlparse

from flask import current_app

from app.extensions import get_db
from app.models import Eleve, Notification
from app.services.tenant import apply_tenant_school, get_or_404_tenant


class NotificationProvider(ABC):
    """Interface abstraite pour les fournisseurs SMS/Email."""

    @abstractmethod
    def envoyer(self, destinataire: str, contenu: str, sujet: str | None = None) -> bool:
        pass


class SMTPProvider(NotificationProvider):
    """Fournisseur email via SMTP."""

    def envoyer(self, destinataire: str, contenu: str, sujet: str | None = None) -> bool:
        try:
            msg = MIMEText(contenu, "plain", "utf-8")
            msg["Subject"] = sujet or "Notification — Gestion Scolaire"
            msg["From"] = current_app.config["SMTP_FROM"]
            msg["To"] = destinataire

            with smtplib.SMTP(
                current_app.config["SMTP_HOST"], current_app.config["SMTP_PORT"]
            ) as server:
                if current_app.config["SMTP_USER"]:
                    server.starttls()
                    server.login(
                        current_app.config["SMTP_USER"],
                        current_app.config["SMTP_PASSWORD"],
                    )
                server.send_message(msg)
            return True
        except Exception:
            return False


class SMSProviderStub(NotificationProvider):
    """Stub SMS — log en dev si aucune API configurée."""

    def envoyer(self, destinataire: str, contenu: str, sujet: str | None = None) -> bool:
        current_app.logger.info("SMS stub → %s : %s", destinataire, contenu[:80])
        return True


class HTTPAPIProvider(NotificationProvider):
    """Fournisseur SMS HTTP générique (POST JSON)."""

    def envoyer(self, destinataire: str, contenu: str, sujet: str | None = None) -> bool:
        api_url = current_app.config.get("SMS_API_URL", "")
        api_key = current_app.config.get("SMS_API_KEY", "")
        if not api_url:
            return SMSProviderStub().envoyer(destinataire, contenu, sujet)

        payload = json.dumps({
            "to": destinataire,
            "message": contenu,
            "sender": current_app.config.get("SMS_SENDER", "ECOLE"),
        }).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else "",
        }
        try:
            status = _post_json(api_url, payload, headers)
            return 200 <= status < 300
        except OSError as exc:
            current_app.logger.warning("SMS API error → %s : %s", destinataire, exc)
            return False


def _post_json(url: str, payload: bytes, headers: dict, timeout: int = 15) -> int:
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        raise ValueError("Invalid SMS API URL")
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    conn_cls = HTTPSConnection if parsed.scheme == "https" else HTTPConnection
    conn = conn_cls(parsed.netloc, timeout=timeout)
    try:
        conn.request("POST", path, body=payload, headers=headers)
        return conn.getresponse().status
    finally:
        conn.close()


def get_provider(canal: str) -> NotificationProvider:
    if canal == "email":
        return SMTPProvider()
    if canal == "whatsapp":
        from app.services.channels.whatsapp import WhatsAppNotificationAdapter

        return WhatsAppNotificationAdapter()
    if current_app.config.get("SMS_API_URL"):
        return HTTPAPIProvider()
    return SMSProviderStub()


def _resolve_parent_id(db, id_eleve: uuid.UUID | None) -> uuid.UUID | None:
    """Retourne le parent tuteur légal ou le premier parent lié à l'élève."""
    if not id_eleve:
        return None
    from app.models import EleveParent

    link = (
        db.query(EleveParent)
        .filter(EleveParent.id_eleve == id_eleve, EleveParent.tuteur_legal.is_(True))
        .first()
    )
    if not link:
        link = db.query(EleveParent).filter(EleveParent.id_eleve == id_eleve).first()
    return link.id_parent if link else None


def creer_notification(
    canal: str,
    type_notification: str,
    contenu: str,
    id_eleve: uuid.UUID | None = None,
    id_parent: uuid.UUID | None = None,
    school_id: uuid.UUID | None = None,
    idempotency_key: str | None = None,
) -> Notification:
    """Crée une notification en file d'attente (ou disponible si canal=interne)."""
    db = get_db()
    if id_eleve and school_id is None:
        get_or_404_tenant(Eleve, id_eleve)
    elif id_eleve and school_id is not None:
        eleve = (
            db.query(Eleve)
            .filter(Eleve.id == id_eleve, Eleve.school_id == school_id)
            .first()
        )
        if not eleve:
            from flask import abort

            abort(404)
    if id_eleve and not id_parent:
        id_parent = _resolve_parent_id(db, id_eleve)

    # Canal interne : notification inbox uniquement (pas d'envoi SMTP/SMS).
    statut = "envoye" if canal == "interne" else "en_attente"
    envoye_le = datetime.now(UTC) if canal == "interne" else None

    notif = apply_tenant_school(
        Notification(
            id=uuid.uuid4(),
            id_eleve=id_eleve,
            id_parent=id_parent,
            canal=canal,
            type_notification=type_notification,
            contenu=contenu,
            statut=statut,
            envoye_le=envoye_le,
            idempotency_key=idempotency_key,
        ),
        school_id=school_id,
    )
    db.add(notif)
    db.commit()
    return notif


def envoyer_notification(notif: Notification, destinataire: str) -> bool:
    """Tente l'envoi d'une notification avec retry."""
    if notif.canal == "interne":
        return True
    provider = get_provider(notif.canal)
    sujet = f"Notification — {notif.type_notification}"
    success = provider.envoyer(destinataire, notif.contenu or "", sujet)

    db = get_db()
    notif.tentative_count = (notif.tentative_count or 0) + 1
    if success:
        notif.statut = "envoye"
        notif.envoye_le = datetime.now(UTC)
    else:
        notif.statut = "echec" if notif.tentative_count >= 3 else "en_attente"
    db.commit()
    return success


def traiter_file_notifications(
    limit: int = 50,
    school_id: uuid.UUID | None = None,
) -> int:
    """Traite les notifications en attente. Retourne le nombre envoyées.

    Sans JWT (cron) : passer school_id, ou traiter toutes les écoles actives.
    """
    db = get_db()
    if school_id is None:
        try:
            from app.services.tenant import get_current_school_id

            school_id = get_current_school_id()
        except Exception:
            school_id = None

    q = (
        db.query(Notification)
        .filter(
            Notification.statut == "en_attente",
            Notification.tentative_count < 3,
            Notification.canal != "interne",
        )
    )
    if school_id is not None:
        q = q.filter(Notification.school_id == school_id)
    pending = q.limit(limit).all()
    sent = 0
    for notif in pending:
        from app.models import ParentTuteur

        destinataire = None
        id_parent = notif.id_parent
        if not id_parent and notif.id_eleve:
            id_parent = _resolve_parent_id(db, notif.id_eleve)
            if id_parent:
                notif.id_parent = id_parent
                db.commit()
        if id_parent:
            parent = (
                db.query(ParentTuteur)
                .filter(
                    ParentTuteur.id == id_parent,
                    ParentTuteur.school_id == notif.school_id,
                )
                .first()
            )
            if parent:
                destinataire = parent.email if notif.canal == "email" else parent.telephone
        if destinataire and envoyer_notification(notif, destinataire):
            sent += 1
    return sent
