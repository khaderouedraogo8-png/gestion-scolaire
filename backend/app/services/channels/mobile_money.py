"""Paiement Mobile Money — mode NON CONFIGURÉ si clés absentes.

Opérateurs cibles : Orange Money, Wave, Moov Money, MTN MoMo.
Ne jamais prétendre qu'un paiement MM a réussi si l'intégration est mockée.
"""
from __future__ import annotations

from dataclasses import dataclass

from flask import current_app

OPERATORS = ("orange", "wave", "moov", "mtn")


@dataclass(frozen=True)
class MobileMoneyStatus:
    configured: bool
    status: str  # CONFIGURED | NON_CONFIGURE
    operators: dict[str, bool]
    message: str


def mobile_money_status() -> MobileMoneyStatus:
    operators = {}
    for op in OPERATORS:
        key = f"MM_{op.upper()}_API_KEY"
        operators[op] = bool((current_app.config.get(key) or "").strip())
    configured = any(operators.values())
    if configured:
        return MobileMoneyStatus(
            configured=True,
            status="CONFIGURED",
            operators=operators,
            message="Au moins un opérateur Mobile Money est configuré.",
        )
    return MobileMoneyStatus(
        configured=False,
        status="NON_CONFIGURE",
        operators=operators,
        message=(
            "Mobile Money non configuré — définir MM_ORANGE_API_KEY / "
            "MM_WAVE_API_KEY / MM_MOOV_API_KEY / MM_MTN_API_KEY. "
            "Les encaissements MM restent manuels (libellé mode_paiement)."
        ),
    )


def initier_paiement(
    *,
    operateur: str,
    montant: float,
    telephone: str,
    reference: str,
) -> tuple[bool, str, dict | None]:
    """Initie un paiement MM. Retourne (ok, code, payload)."""
    status = mobile_money_status()
    op = (operateur or "").strip().lower()
    if op not in OPERATORS:
        return False, "OPERATEUR_INVALIDE", None
    if not status.configured or not status.operators.get(op):
        return False, "NON_CONFIGURE", {
            "status": "NON_CONFIGURE",
            "message": status.message,
            "operateur": op,
        }
    # Adaptateur HTTP réel non branché — refuser plutôt que faker un succès.
    current_app.logger.info(
        "Mobile Money %s CONFIGURED mais adaptateur non implémenté — ref=%s montant=%s tel=%s",
        op,
        reference,
        montant,
        telephone,
    )
    return False, "ADAPTER_NOT_IMPLEMENTED", {
        "status": "ADAPTER_NOT_IMPLEMENTED",
        "operateur": op,
        "reference": reference,
    }
