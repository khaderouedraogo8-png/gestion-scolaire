"""Paiement Mobile Money — adapters HTTP + sandbox.

Opérateurs : Orange Money, Wave, Moov Money, MTN MoMo.
Statuts: CONFIGURED | SANDBOX | NON_CONFIGURE
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from urllib import error, request

from flask import current_app

OPERATORS = ("orange", "wave", "moov", "mtn")


@dataclass(frozen=True)
class MobileMoneyStatus:
    configured: bool
    status: str
    operators: dict[str, bool]
    message: str
    sandbox: bool = False


def mobile_money_status() -> MobileMoneyStatus:
    operators = {}
    for op in OPERATORS:
        key = f"MM_{op.upper()}_API_KEY"
        operators[op] = bool((current_app.config.get(key) or "").strip())
    sandbox = bool(current_app.config.get("MM_SANDBOX"))
    configured = any(operators.values())
    if configured:
        return MobileMoneyStatus(
            configured=True,
            status="CONFIGURED",
            operators=operators,
            message="Au moins un opérateur Mobile Money est configuré.",
            sandbox=False,
        )
    if sandbox:
        return MobileMoneyStatus(
            configured=True,
            status="SANDBOX",
            operators={op: True for op in OPERATORS},
            message="Mobile Money en mode SANDBOX — paiements simulés.",
            sandbox=True,
        )
    return MobileMoneyStatus(
        configured=False,
        status="NON_CONFIGURE",
        operators=operators,
        message=(
            "Mobile Money non configuré — définir MM_ORANGE_API_KEY / "
            "MM_WAVE_API_KEY / MM_MOOV_API_KEY / MM_MTN_API_KEY, ou MM_SANDBOX=1."
        ),
        sandbox=False,
    )


def initier_paiement(
    *,
    operateur: str,
    montant: float,
    telephone: str,
    reference: str,
) -> tuple[bool, str, dict | None]:
    status = mobile_money_status()
    op = (operateur or "").strip().lower()
    if op not in OPERATORS:
        return False, "OPERATEUR_INVALIDE", None
    if status.status == "NON_CONFIGURE":
        return False, "NON_CONFIGURE", {
            "status": "NON_CONFIGURE",
            "message": status.message,
            "operateur": op,
        }
    if status.status == "SANDBOX" or status.sandbox:
        ref = reference or f"SBX-{uuid.uuid4().hex[:12]}"
        current_app.logger.info(
            "MM SANDBOX %s montant=%s tel=%s ref=%s", op, montant, telephone, ref
        )
        return True, "SANDBOX_OK", {
            "status": "PENDING_SANDBOX",
            "operateur": op,
            "reference": ref,
            "montant": montant,
            "telephone": telephone,
        }

    if not status.operators.get(op):
        return False, "NON_CONFIGURE", {
            "status": "NON_CONFIGURE",
            "message": f"Opérateur {op} non configuré.",
            "operateur": op,
        }

    api_key = (current_app.config.get(f"MM_{op.upper()}_API_KEY") or "").strip()
    base_url = (
        current_app.config.get(f"MM_{op.upper()}_API_URL")
        or current_app.config.get("MM_API_BASE_URL")
        or ""
    ).strip()
    if not base_url:
        return False, "URL_MANQUANTE", {
            "status": "URL_MANQUANTE",
            "message": f"Définir MM_{op.upper()}_API_URL pour l'opérateur {op}.",
            "operateur": op,
        }

    payload = {
        "amount": montant,
        "currency": "XOF",
        "msisdn": telephone,
        "reference": reference,
        "operator": op,
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        base_url.rstrip("/") + "/payments",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Api-Key": api_key,
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = {"raw": body[:500]}
            return True, "INITIATED", {
                "status": "PENDING",
                "operateur": op,
                "reference": reference,
                "provider": parsed,
            }
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        current_app.logger.error("MM %s HTTP %s: %s", op, exc.code, detail)
        return False, f"HTTP_{exc.code}", {"status": "ERROR", "detail": detail}
    except Exception as exc:
        current_app.logger.exception("MM erreur")
        return False, "ERROR", {"status": "ERROR", "detail": str(exc)}
