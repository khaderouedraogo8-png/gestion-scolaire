"""Webhooks externes (WhatsApp Meta Cloud API + sandbox)."""
from __future__ import annotations

from flask import current_app, jsonify, request
from flask.views import MethodView
from flask_smorest import Blueprint

from app.extensions import limiter
from app.services.whatsapp_bot import extract_meta_inbound, handle_inbound

blp = Blueprint("webhooks", __name__, url_prefix="/webhooks", description="Webhooks externes")


@blp.route("/whatsapp")
class WhatsAppWebhook(MethodView):
    def get(self):
        """Vérification Meta (hub.challenge)."""
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        expected = (current_app.config.get("WHATSAPP_VERIFY_TOKEN") or "").strip()
        if mode == "subscribe" and expected and token == expected:
            return challenge or "", 200
        if mode == "subscribe" and current_app.config.get("WHATSAPP_SANDBOX"):
            return challenge or "", 200
        return jsonify({"message": "Forbidden"}), 403

    @limiter.limit("60 per minute")
    def post(self):
        """Inbound Meta ou sandbox {from, text}.

        Body plat sandbox : renvoie {reply, command, ...} sans appel Meta.
        Meta : traite les messages et envoie via envoyer_whatsapp.
        """
        payload = request.get_json(silent=True) or {}
        sandbox = bool(current_app.config.get("WHATSAPP_SANDBOX"))
        is_flat = "from" in payload and "entry" not in payload

        if is_flat:
            telephone = str(payload.get("from") or "")
            text = str(payload.get("text") or "")
            # Sandbox / test : reply in JSON, no Meta send
            result = handle_inbound(telephone, text, send=False)
            return jsonify(result), 200

        pairs = extract_meta_inbound(payload)
        results = []
        for telephone, text in pairs:
            results.append(handle_inbound(telephone, text, send=True))
        if sandbox and not pairs and payload:
            # Meta-shaped empty payload in sandbox
            return jsonify({"processed": 0, "results": [], "sandbox": True}), 200
        return jsonify({"processed": len(results), "results": results}), 200
