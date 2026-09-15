"""Réponses d'erreur API cohérentes — jamais de stack trace / secrets côté client."""
from __future__ import annotations

import logging

from flask import jsonify
from marshmallow import ValidationError as MarshmallowValidationError
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

# Messages stables FR — évite les descriptions Werkzeug verbeuses / en anglais
_SAFE_HTTP_MESSAGES = {
    400: "Requête invalide.",
    401: "Authentification requise.",
    403: "Accès refusé.",
    404: "Ressource introuvable.",
    405: "Méthode non autorisée.",
    409: "Conflit.",
    413: "Fichier trop volumineux.",
    422: "Données invalides.",
    429: "Trop de requêtes. Réessayez dans quelques instants.",
}


def error_body(code: str, message: str, *, details=None) -> dict:
    """Format d'erreur stable (rétro-compatible via clé `message`)."""
    payload = {
        "success": False,
        "message": message,
        "error": {"code": code, "message": message},
    }
    if details is not None:
        payload["error"]["details"] = details
    return payload


def abort_api(status: int, code: str, message: str, *, details=None) -> None:
    """Abort HTTP avec enveloppe PR7 + code métier explicite (pas un 2e format)."""
    from flask import abort, jsonify, make_response

    abort(make_response(jsonify(error_body(code, message, details=details)), status))


def register_error_handlers(app) -> None:
    """Enregistre les handlers globaux (après init Flask-Smorest / JWT)."""

    @app.errorhandler(MarshmallowValidationError)
    def handle_marshmallow(err: MarshmallowValidationError):
        return jsonify(
            error_body(
                "VALIDATION_ERROR",
                "Données invalides.",
                details=err.messages,
            )
        ), 422

    @app.errorhandler(HTTPException)
    def handle_http(err: HTTPException):
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            413: "PAYLOAD_TOO_LARGE",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMITED",
        }
        status = err.code or 500
        err_code = code_map.get(status, "HTTP_ERROR")
        safe = _SAFE_HTTP_MESSAGES.get(status)
        description = (err.description or "").strip()
        # Ne pas renvoyer la prose Werkzeug anglaise par défaut
        werkzeug_default = getattr(type(err), "description", None)
        if (
            description
            and description != err.name
            and description != werkzeug_default
            and description != safe
        ):
            message = description
        else:
            message = safe or err.name or "Erreur HTTP"

        details = None
        data = getattr(err, "data", None)
        if isinstance(data, dict) and data.get("messages") is not None:
            details = data["messages"]
            message = _SAFE_HTTP_MESSAGES.get(422, message)

        return jsonify(error_body(err_code, message, details=details)), status

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        logger.exception("Erreur serveur non gérée: %s", err)
        return jsonify(
            error_body(
                "INTERNAL_ERROR",
                "Une erreur interne est survenue. Réessayez plus tard.",
            )
        ), 500

    # JWT : même envelope que le reste de l'API (sinon {"msg": ...} brut)
    try:
        from app.extensions import jwt
    except Exception:  # pragma: no cover
        return

    @jwt.unauthorized_loader
    def _jwt_unauthorized(_reason: str):
        return jsonify(error_body("UNAUTHORIZED", "Authentification requise.")), 401

    @jwt.invalid_token_loader
    def _jwt_invalid(_reason: str):
        return jsonify(error_body("UNAUTHORIZED", "Jeton invalide.")), 401

    @jwt.expired_token_loader
    def _jwt_expired(_jwt_header, _jwt_payload):
        return jsonify(error_body("UNAUTHORIZED", "Jeton expiré.")), 401

    @jwt.needs_fresh_token_loader
    def _jwt_fresh(_jwt_header, _jwt_payload):
        return jsonify(error_body("UNAUTHORIZED", "Jeton frais requis.")), 401

    @jwt.revoked_token_loader
    def _jwt_revoked(_jwt_header, _jwt_payload):
        return jsonify(error_body("UNAUTHORIZED", "Jeton révoqué.")), 401
