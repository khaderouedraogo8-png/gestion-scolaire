"""Envoi de notifications — pattern adaptateur NotificationProvider."""
import json
import smtplib
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from email.mime.text import MIMEText
from urllib import error, request

from flask import current_app

from app.extensions import get_db
from app.models import Notification


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
        req = request.Request(
            api_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}" if api_key else "",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=15) as resp:
                return 200 <= resp.status < 300
        except error.URLError as exc:
            current_app.logger.warning("SMS API error → %s : %s", destinataire, exc)
            return False


def get_provider(canal: str) -> NotificationProvider:
    if canal == "email":
        return SMTPProvider()
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
) -> Notification:
    """Crée une notification en file d'attente."""
    db = get_db()
    if id_eleve and not id_parent:
        id_parent = _resolve_parent_id(db, id_eleve)
    notif = Notification(
        id=uuid.uuid4(),
        id_eleve=id_eleve,
        id_parent=id_parent,
        canal=canal,
        type_notification=type_notification,
        contenu=contenu,
        statut="en_attente",
    )
    db.add(notif)
    db.commit()
    return notif


def envoyer_notification(notif: Notification, destinataire: str) -> bool:
    """Tente l'envoi d'une notification avec retry."""
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


def traiter_file_notifications(limit: int = 50) -> int:
    """Traite les notifications en attente. Retourne le nombre envoyées."""
    db = get_db()
    pending = (
        db.query(Notification)
        .filter(Notification.statut == "en_attente", Notification.tentative_count < 3)
        .limit(limit)
        .all()
    )
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
            parent = db.query(ParentTuteur).filter(ParentTuteur.id == id_parent).first()
            if parent:
                destinataire = parent.email if notif.canal == "email" else parent.telephone
        if destinataire and envoyer_notification(notif, destinataire):
            sent += 1
    return sent
