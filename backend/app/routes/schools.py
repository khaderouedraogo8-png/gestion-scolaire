"""Routes école (tenant) — fondation Phase 1, pas de CRUD public."""
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from marshmallow import Schema, fields

from app.services.tenant import get_current_school

blp = Blueprint("schools", __name__, description="Écoles (tenant SaaS)")


class SchoolSchema(Schema):
    id = fields.UUID(dump_only=True)
    name = fields.String()
    code = fields.String()
    email = fields.String(allow_none=True)
    phone = fields.String(allow_none=True)
    address = fields.String(allow_none=True)
    city = fields.String(allow_none=True)
    country = fields.String(allow_none=True)
    logo = fields.String(allow_none=True)
    is_active = fields.Boolean()


@blp.route("/current")
class CurrentSchool(MethodView):
    @jwt_required()
    @blp.response(200, SchoolSchema)
    def get(self):
        """Retourne l'école du contexte authentifié (pas un id client)."""
        return get_current_school()
