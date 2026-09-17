"""Inventaire — articles et mouvements."""
from __future__ import annotations

import uuid

from flask import jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from marshmallow import Schema, fields, validate

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import InventaireArticle, InventaireMouvement
from app.services.tenant import (
    apply_tenant_school,
    get_or_404_tenant,
    reject_client_school_id,
    tenant_query,
)

blp = Blueprint("inventaire", __name__, description="Inventaire")


class ArticleSchema(Schema):
    id = fields.UUID(dump_only=True)
    code = fields.String(required=True)
    libelle = fields.String(required=True)
    categorie = fields.String(allow_none=True)
    quantite = fields.Integer(load_default=0)
    seuil_alerte = fields.Integer(load_default=0)
    unite = fields.String(allow_none=True)
    actif = fields.Boolean(load_default=True)
    created_at = fields.DateTime(dump_only=True)


class MouvementSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_article = fields.UUID(required=True)
    type_mouvement = fields.String(required=True, validate=validate.OneOf(["entree", "sortie", "ajustement"]))
    quantite = fields.Integer(required=True)
    motif = fields.String(allow_none=True)
    date_mouvement = fields.DateTime(dump_only=True)
    effectue_par = fields.UUID(dump_only=True, allow_none=True)


@blp.route("/articles")
class ArticlesResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "agent_comptable")
    def get(self):
        q = tenant_query(InventaireArticle)
        if request.args.get("alerte") in ("1", "true"):
            q = q.filter(InventaireArticle.quantite <= InventaireArticle.seuil_alerte)
        return jsonify(ArticleSchema(many=True).dump(q.order_by(InventaireArticle.libelle).all()))

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(ArticleSchema)
    @blp.response(201, ArticleSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        row = InventaireArticle(id=uuid.uuid4(), **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/articles/<uuid:id_article>")
class ArticleDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "agent_comptable")
    def get(self, id_article):
        return jsonify(ArticleSchema().dump(get_or_404_tenant(InventaireArticle, id_article)))

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(ArticleSchema(partial=True))
    def put(self, data, id_article):
        db = get_db()
        row = get_or_404_tenant(InventaireArticle, id_article)
        for k, v in data.items():
            setattr(row, k, v)
        db.commit()
        return jsonify(ArticleSchema().dump(row))

    @jwt_required()
    @require_role("administrateur", "directeur")
    def delete(self, id_article):
        db = get_db()
        row = get_or_404_tenant(InventaireArticle, id_article)
        db.delete(row)
        db.commit()
        return jsonify({"message": "Article supprimé"})


@blp.route("/mouvements")
class MouvementsResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "agent_comptable")
    def get(self):
        q = tenant_query(InventaireMouvement)
        id_article = request.args.get("id_article")
        if id_article:
            q = q.filter(InventaireMouvement.id_article == uuid.UUID(id_article))
        rows = q.order_by(InventaireMouvement.date_mouvement.desc()).limit(200).all()
        return jsonify(MouvementSchema(many=True).dump(rows))

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(MouvementSchema)
    @blp.response(201, MouvementSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        user = get_current_user()
        article = get_or_404_tenant(InventaireArticle, data["id_article"])
        qty = int(data["quantite"])
        typ = data["type_mouvement"]
        if typ == "entree":
            article.quantite += qty
        elif typ == "sortie":
            if article.quantite < qty:
                return jsonify({"message": "Stock insuffisant"}), 409
            article.quantite -= qty
        elif typ == "ajustement":
            article.quantite = qty
        row = InventaireMouvement(id=uuid.uuid4(), effectue_par=user.id, **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201
