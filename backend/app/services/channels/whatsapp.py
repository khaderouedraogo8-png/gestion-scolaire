"""Canal WhatsApp Business — mode NON CONFIGURÉ si clés absentes.

Ne jamais simuler un envoi réussi quand l'intégration n'est pas branchée.
"""
from __future__ import annotations

from dataclasses import dataclass

from flask import current_app


@dataclass(frozen=True)
class ChannelStatus:
    configured: bool
    status: str  # CONFIGURED | NON_CONFIGURE
    message: str


def whatsapp_status() -> ChannelStatus:
    token = (current_app.config.get("WHATSAPP_API_TOKEN") or "").strip()
    phone_id = (current_app.config.get("WHATSAPP_PHONE_NUMBER_ID") or "").strip()
    if token and phone_id:
        return ChannelStatus(
            configured=True,
            status="CONFIGURED",
            message="WhatsApp Business API configuré.",
        )
    return ChannelStatus(
        configured=False,
        status="NON_CONFIGURE",
        message=(
            "WhatsApp non configuré — définir WHATSAPP_API_TOKEN et "
            "WHATSAPP_PHONE_NUMBER_ID. Aucun message ne sera envoyé."
        ),
    )


def envoyer_whatsapp(destinataire: str, contenu: str) -> tuple[bool, str]:
    """Envoie un message WhatsApp. Retourne (ok, detail).

    Si non configuré : (False, 'NON_CONFIGURE') — jamais de faux succès.
    """
    status = whatsapp_status()
    if not status.configured:
        current_app.logger.warning(
            "WhatsApp NON_CONFIGURE — destinataire=%s ignoré", destinataire
        )
        return False, "NON_CONFIGURE"

    # Intégration réelle à brancher sur l'API Meta Cloud.
    # Placeholder HTTP volontairement non appelé tant que le contrat n'est pas validé.
    current_app.logger.info(
        "WhatsApp CONFIGURED mais adaptateur HTTP non encore branché — "
        "destinataire=%s contenu=%s",
        destinataire,
        contenu[:80],
    )
    return False, "ADAPTER_NOT_IMPLEMENTED"


class WhatsAppNotificationAdapter:
    """Adaptateur compatible NotificationProvider — refuse le faux succès."""

    def envoyer(self, destinataire: str, contenu: str, sujet: str | None = None) -> bool:
        ok, _code = envoyer_whatsapp(destinataire, contenu)
        return ok
