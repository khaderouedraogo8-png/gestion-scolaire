"""Canal WhatsApp Business — Meta Cloud API + sandbox.

Statuts: CONFIGURED | SANDBOX | NON_CONFIGURE
Ne jamais simuler un succès en NON_CONFIGURE.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import error, request

from flask import current_app


@dataclass(frozen=True)
class ChannelStatus:
    configured: bool
    status: str
    message: str


def whatsapp_status() -> ChannelStatus:
    token = (current_app.config.get("WHATSAPP_API_TOKEN") or "").strip()
    phone_id = (current_app.config.get("WHATSAPP_PHONE_NUMBER_ID") or "").strip()
    sandbox = bool(current_app.config.get("WHATSAPP_SANDBOX"))
    if token and phone_id:
        return ChannelStatus(
            configured=True,
            status="CONFIGURED",
            message="WhatsApp Business API configuré.",
        )
    if sandbox:
        return ChannelStatus(
            configured=True,
            status="SANDBOX",
            message="WhatsApp en mode SANDBOX — envois simulés (aucun appel Meta).",
        )
    return ChannelStatus(
        configured=False,
        status="NON_CONFIGURE",
        message=(
            "WhatsApp non configuré — définir WHATSAPP_API_TOKEN et "
            "WHATSAPP_PHONE_NUMBER_ID, ou WHATSAPP_SANDBOX=1."
        ),
    )


def envoyer_whatsapp(destinataire: str, contenu: str) -> tuple[bool, str]:
    status = whatsapp_status()
    if status.status == "NON_CONFIGURE":
        current_app.logger.warning(
            "WhatsApp NON_CONFIGURE — destinataire=%s ignoré", destinataire
        )
        return False, "NON_CONFIGURE"

    if status.status == "SANDBOX":
        current_app.logger.info(
            "WhatsApp SANDBOX → %s : %s", destinataire, contenu[:120]
        )
        return True, "SANDBOX_OK"

    token = (current_app.config.get("WHATSAPP_API_TOKEN") or "").strip()
    phone_id = (current_app.config.get("WHATSAPP_PHONE_NUMBER_ID") or "").strip()
    url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": destinataire.lstrip("+").replace(" ", ""),
        "type": "text",
        "text": {"body": contenu[:4096]},
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            current_app.logger.info("WhatsApp OK status=%s body=%s", resp.status, body[:200])
            return True, "SENT"
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        current_app.logger.error("WhatsApp HTTP %s: %s", exc.code, detail)
        return False, f"HTTP_{exc.code}"
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("WhatsApp erreur: %s", exc)
        return False, "ERROR"


class WhatsAppNotificationAdapter:
    def envoyer(self, destinataire: str, contenu: str, sujet: str | None = None) -> bool:
        ok, _code = envoyer_whatsapp(destinataire, contenu)
        return ok
