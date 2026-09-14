"""Réponses d'erreur API cohérentes — jamais de stack trace / secrets côté client."""
from __future__ import annotations

import logging

from flask import jsonify
from marshmallow import ValidationError as MarshmallowValidationError
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


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


def register_error_handlers(app) -> None:
    """Enregistre les handlers globaux (après init Flask-Smorest)."""

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
        err_code = code_map.get(err.code or 500, "HTTP_ERROR")
        message = err.description or err.name or "Erreur HTTP"
        if err.code == 429:
            message = "Trop de requêtes. Réessayez dans quelques instants."
        return jsonify(error_body(err_code, message)), err.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        logger.exception("Erreur serveur non gérée: %s", err)
        return jsonify(
            error_body(
                "INTERNAL_ERROR",
                "Une erreur interne est survenue. Réessayez plus tard.",
            )
        ), 500
