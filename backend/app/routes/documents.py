"""Module 6 — Routes documents administratifs."""
import os
import uuid

from flask import jsonify, request, send_file
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import require_role
from app.extensions import get_db
from app.models import DocumentAdministratif, Eleve
from app.schemas.documents import (
    CarteScolaireGenerateSchema,
    DiplomeGenerateSchema,
    DocumentAdministratifSchema,
    DocumentGenerateSchema,
    VerifierQRSchema,
)
from app.services.generation_carte_qr import generer_carte_scolaire, verifier_qr_data
from app.services.generation_documents import (
    generer_attestation_scolarite,
    generer_certificat_scolarite,
    generer_diplome,
)
from app.services.tenant import get_or_404_tenant, tenant_query
from app.utils.pagination import paginate_query, pagination_payload, parse_pagination

blp = Blueprint("documents", __name__, url_prefix="/documents", description="Documents administratifs")


def _serialize_document(db, doc):
    data = DocumentAdministratifSchema().dump(doc)
    eleve = tenant_query(Eleve).filter(Eleve.id == doc.id_eleve).first()
    if eleve:
        data["prenom"] = eleve.prenom
        data["nom"] = eleve.nom
        data["eleve"] = {"prenom": eleve.prenom, "nom": eleve.nom, "matricule": eleve.matricule}
    return data


@blp.route("/")
class DocumentsResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def get(self):
        db = get_db()
        q = tenant_query(DocumentAdministratif)
        id_eleve = request.args.get("id_eleve")
        type_doc = request.args.get("type_document")
        if id_eleve:
            get_or_404_tenant(Eleve, id_eleve)
            q = q.filter(DocumentAdministratif.id_eleve == uuid.UUID(id_eleve))
        if type_doc:
            q = q.filter(DocumentAdministratif.type_document == type_doc)
        page, per_page = parse_pagination()
        items, total, pages = paginate_query(
            q.order_by(DocumentAdministratif.date_emission.desc()), page, per_page
        )
        return jsonify(
            pagination_payload(
                [_serialize_document(db, d) for d in items],
                page=page,
                per_page=per_page,
                total=total,
                pages=pages,
            )
        )


@blp.route("/carte-scolaire")
class CarteScolaireResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(CarteScolaireGenerateSchema)
    def post(self, data):
        user = get_current_user()
        try:
            doc = generer_carte_scolaire(
                uuid.UUID(data["id_eleve"]),
                uuid.UUID(data["id_annee"]),
                user.id,
                data.get("date_expiration"),
            )
            return jsonify(_serialize_document(get_db(), doc)), 201
        except ValueError as e:
            return jsonify({"message": str(e)}), 400


@blp.route("/attestation")
class AttestationResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(DocumentGenerateSchema)
    def post(self, data):
        user = get_current_user()
        try:
            doc = generer_attestation_scolarite(
                uuid.UUID(data["id_eleve"]),
                uuid.UUID(data["id_annee"]),
                user.id,
            )
            return jsonify(_serialize_document(get_db(), doc)), 201
        except ValueError as e:
            return jsonify({"message": str(e)}), 400


@blp.route("/certificat")
class CertificatResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(DocumentGenerateSchema)
    def post(self, data):
        user = get_current_user()
        try:
            doc = generer_certificat_scolarite(
                uuid.UUID(data["id_eleve"]),
                uuid.UUID(data["id_annee"]),
                user.id,
            )
            return jsonify(_serialize_document(get_db(), doc)), 201
        except ValueError as e:
            return jsonify({"message": str(e)}), 400


@blp.route("/diplome")
class DiplomeResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(DiplomeGenerateSchema)
    def post(self, data):
        user = get_current_user()
        try:
            doc = generer_diplome(
                uuid.UUID(data["id_eleve"]),
                uuid.UUID(data["id_annee"]),
                user.id,
                data.get("mention"),
            )
            return jsonify(_serialize_document(get_db(), doc)), 201
        except ValueError as e:
            return jsonify({"message": str(e)}), 400


@blp.route("/<uuid:id_document>/pdf")
class DocumentPDF(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def get(self, id_document):
        get_db()
        doc = get_or_404_tenant(DocumentAdministratif, id_document)
        if not doc.pdf_url or not os.path.isfile(doc.pdf_url):
            return jsonify({"message": "PDF introuvable"}), 404
        return send_file(doc.pdf_url, mimetype="application/pdf", as_attachment=True)


@blp.route("/verifier-qr")
class VerifierQR(MethodView):
    @blp.arguments(VerifierQRSchema)
    def post(self, data):
        qr_data = data["qr_data"]
        valid, payload = verifier_qr_data(qr_data)
        if not valid:
            return jsonify({"valide": False, "message": "QR code invalide ou falsifié"}), 400
        return jsonify({"valide": True, "data": payload})
