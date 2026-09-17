"""Module 4 — Routes emploi du temps, enseignants, affectations."""
import uuid

from flask import abort, jsonify, request, send_file
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import get_enseignant_for_user, require_role
from app.extensions import get_db
from app.models import (
    AffectationEnseignant,
    AnneeScolaire,
    Classe,
    CreneauEmploiTemps,
    EdtPublication,
    Enseignant,
    Matiere,
    RemplacementEnseignant,
    Salle,
)
from app.schemas.emploi_temps import (
    AffectationEnseignantSchema,
    CreneauEmploiTempsSchema,
    EnseignantSchema,
    SalleSchema,
)
from app.services.generation_pedagogique import generer_pdf_fiche_enseignant
from app.services.tenant import (
    apply_tenant_school,
    assert_same_school,
    get_current_school_id,
    get_or_404_tenant,
    tenant_query,
)
from marshmallow import Schema, fields

blp = Blueprint("emploi_temps", __name__, url_prefix="/emploi-temps", description="Emploi du temps")

JOURS = {1: "Lundi", 2: "Mardi", 3: "Mercredi", 4: "Jeudi", 5: "Vendredi", 6: "Samedi", 7: "Dimanche"}


def _creneaux_tenant_query(db):
    return (
        db.query(CreneauEmploiTemps)
        .join(AffectationEnseignant, CreneauEmploiTemps.id_affectation == AffectationEnseignant.id)
        .filter(AffectationEnseignant.school_id == get_current_school_id())
    )


def _get_creneau_tenant(db, id_creneau):
    creneau = _creneaux_tenant_query(db).filter(CreneauEmploiTemps.id == id_creneau).first()
    if not creneau:
        abort(404)
    return creneau


def _serialize_affectation(db, aff):
    data = AffectationEnseignantSchema().dump(aff)
    ens = tenant_query(Enseignant).filter(Enseignant.id == aff.id_enseignant).first()
    cls = tenant_query(Classe).filter(Classe.id == aff.id_classe).first()
    mat = tenant_query(Matiere).filter(Matiere.id == aff.id_matiere).first()
    data["enseignant_nom"] = f"{ens.prenom} {ens.nom}" if ens else None
    data["classe_nom"] = cls.libelle if cls else None
    data["matiere_nom"] = mat.libelle if mat else None
    if ens:
        data["enseignant"] = {"prenom": ens.prenom, "nom": ens.nom}
    if cls:
        data["classe"] = {"libelle": cls.libelle}
    if mat:
        data["matiere"] = {"libelle": mat.libelle}
    return data


def _serialize_creneau(db, creneau):
    data = CreneauEmploiTempsSchema().dump(creneau)
    data["jour_libelle"] = JOURS.get(creneau.jour_semaine, str(creneau.jour_semaine))
    data["heure_debut"] = creneau.heure_debut.strftime("%H:%M") if creneau.heure_debut else None
    data["heure_fin"] = creneau.heure_fin.strftime("%H:%M") if creneau.heure_fin else None
    aff = tenant_query(AffectationEnseignant).filter(
        AffectationEnseignant.id == creneau.id_affectation
    ).first()
    if aff:
        data.update(_serialize_affectation(db, aff))
    if creneau.id_salle:
        salle = tenant_query(Salle).filter(Salle.id == creneau.id_salle).first()
        data["salle_libelle"] = salle.libelle if salle else None
    return data


@blp.route("/enseignants")
class EnseignantsResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    @blp.response(200, EnseignantSchema(many=True))
    def get(self):
        return tenant_query(Enseignant).order_by(Enseignant.nom).all()

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(EnseignantSchema)
    @blp.response(201, EnseignantSchema)
    def post(self, data):
        db = get_db()
        enseignant = apply_tenant_school(Enseignant(id=uuid.uuid4(), **data))
        db.add(enseignant)
        db.commit()
        return enseignant, 201


@blp.route("/enseignants/<uuid:id_enseignant>")
class EnseignantDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    def get(self, id_enseignant):
        db = get_db()
        user = get_current_user()
        enseignant = get_or_404_tenant(Enseignant, id_enseignant)
        if user.role == "enseignant":
            linked = get_enseignant_for_user(user)
            if not linked or linked.id != enseignant.id:
                return jsonify({"message": "Accès refusé"}), 403
        id_annee = request.args.get("id_annee")
        affectations_q = tenant_query(AffectationEnseignant).filter(
            AffectationEnseignant.id_enseignant == id_enseignant
        )
        if id_annee:
            affectations_q = affectations_q.filter(
                AffectationEnseignant.id_annee == uuid.UUID(id_annee)
            )
        affectations = [_serialize_affectation(db, a) for a in affectations_q.all()]
        volume_total = sum(float(a.get("volume_horaire_hebdo") or 0) for a in affectations)
        aff_ids = [a["id"] for a in affectations]
        creneaux = []
        if aff_ids:
            for c in _creneaux_tenant_query(db).filter(
                CreneauEmploiTemps.id_affectation.in_([uuid.UUID(i) for i in aff_ids])
            ).all():
                creneaux.append(_serialize_creneau(db, c))
        data = EnseignantSchema().dump(enseignant)
        data["affectations"] = affectations
        data["creneaux"] = creneaux
        data["volume_horaire_total"] = volume_total
        return jsonify(data)

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(EnseignantSchema)
    @blp.response(200, EnseignantSchema)
    def put(self, data, id_enseignant):
        db = get_db()
        enseignant = get_or_404_tenant(Enseignant, id_enseignant)
        for key, value in data.items():
            setattr(enseignant, key, value)
        db.commit()
        return enseignant


@blp.route("/enseignants/<uuid:id_enseignant>/pdf")
class EnseignantPdf(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    def get(self, id_enseignant):
        id_annee = request.args.get("id_annee")
        if not id_annee:
            return jsonify({"message": "id_annee requis"}), 400
        try:
            path = generer_pdf_fiche_enseignant(id_enseignant, uuid.UUID(id_annee))
            return send_file(path, mimetype="application/pdf", as_attachment=False, download_name="fiche_enseignant.pdf")
        except RuntimeError as e:
            return jsonify({"message": str(e)}), 503


@blp.route("/affectations")
class AffectationsResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    def get(self):
        db = get_db()
        q = tenant_query(AffectationEnseignant)
        id_annee = request.args.get("id_annee")
        id_classe = request.args.get("id_classe")
        id_enseignant = request.args.get("id_enseignant")
        if id_annee:
            q = q.filter(AffectationEnseignant.id_annee == uuid.UUID(id_annee))
        if id_classe:
            q = q.filter(AffectationEnseignant.id_classe == uuid.UUID(id_classe))
        if id_enseignant:
            q = q.filter(AffectationEnseignant.id_enseignant == uuid.UUID(id_enseignant))
        items = [_serialize_affectation(db, a) for a in q.all()]
        return jsonify({"items": items, "total": len(items)})

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(AffectationEnseignantSchema)
    @blp.response(201, AffectationEnseignantSchema)
    def post(self, data):
        db = get_db()
        assert_same_school(
            get_or_404_tenant(Enseignant, data["id_enseignant"]),
            get_or_404_tenant(Classe, data["id_classe"]),
            get_or_404_tenant(Matiere, data["id_matiere"]),
            get_or_404_tenant(AnneeScolaire, data["id_annee"]),
        )
        affectation = apply_tenant_school(AffectationEnseignant(id=uuid.uuid4(), **data))
        db.add(affectation)
        db.commit()
        return affectation, 201


@blp.route("/affectations/<uuid:id_affectation>")
class AffectationDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    def delete(self, id_affectation):
        db = get_db()
        aff = get_or_404_tenant(AffectationEnseignant, id_affectation)
        _creneaux_tenant_query(db).filter(
            CreneauEmploiTemps.id_affectation == id_affectation
        ).delete(synchronize_session=False)
        db.delete(aff)
        db.commit()
        return jsonify({"message": "Affectation supprimée"})


@blp.route("/salles")
class SallesResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    @blp.response(200, SalleSchema(many=True))
    def get(self):
        get_db()
        return tenant_query(Salle).order_by(Salle.libelle).all()

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(SalleSchema)
    @blp.response(201, SalleSchema)
    def post(self, data):
        db = get_db()
        salle = apply_tenant_school(Salle(id=uuid.uuid4(), **data))
        db.add(salle)
        db.commit()
        return salle, 201


@blp.route("/creneaux")
class CreneauxResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    def get(self):
        db = get_db()
        q = _creneaux_tenant_query(db)
        id_affectation = request.args.get("id_affectation")
        id_classe = request.args.get("id_classe")
        id_annee = request.args.get("id_annee")
        if id_affectation:
            q = q.filter(CreneauEmploiTemps.id_affectation == uuid.UUID(id_affectation))
        creneaux = q.all()
        if id_classe or id_annee:
            filtered = []
            for c in creneaux:
                aff = tenant_query(AffectationEnseignant).filter(
                    AffectationEnseignant.id == c.id_affectation
                ).first()
                if not aff:
                    continue
                if id_classe and str(aff.id_classe) != id_classe:
                    continue
                if id_annee and str(aff.id_annee) != id_annee:
                    continue
                filtered.append(c)
            creneaux = filtered
        return jsonify([_serialize_creneau(db, c) for c in creneaux])

    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(CreneauEmploiTempsSchema)
    @blp.response(201, CreneauEmploiTempsSchema)
    def post(self, data):
        db = get_db()
        get_or_404_tenant(AffectationEnseignant, data["id_affectation"])
        if data.get("id_salle"):
            get_or_404_tenant(Salle, data["id_salle"])
        creneau = CreneauEmploiTemps(id=uuid.uuid4(), **data)
        db.add(creneau)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            if "no_chevauchement_salle" in str(e):
                return jsonify({"message": "Conflit de salle — créneau chevauchant"}), 409
            raise
        return creneau, 201


@blp.route("/creneaux/<uuid:id_creneau>")
class CreneauDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(CreneauEmploiTempsSchema)
    @blp.response(200, CreneauEmploiTempsSchema)
    def put(self, data, id_creneau):
        db = get_db()
        creneau = _get_creneau_tenant(db, id_creneau)
        if data.get("id_affectation"):
            get_or_404_tenant(AffectationEnseignant, data["id_affectation"])
        if data.get("id_salle"):
            get_or_404_tenant(Salle, data["id_salle"])
        for key, value in data.items():
            setattr(creneau, key, value)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            if "no_chevauchement_salle" in str(e):
                return jsonify({"message": "Conflit de salle — créneau chevauchant"}), 409
            raise
        return creneau

    @jwt_required()
    @require_role("administrateur", "directeur")
    def delete(self, id_creneau):
        db = get_db()
        creneau = _get_creneau_tenant(db, id_creneau)
        db.delete(creneau)
        db.commit()
        return jsonify({"message": "Créneau supprimé"})


class RemplacementSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_enseignant_absent = fields.UUID(required=True)
    id_enseignant_remplacant = fields.UUID(allow_none=True)
    id_creneau = fields.UUID(allow_none=True)
    date_remplacement = fields.Date(required=True)
    motif = fields.String(allow_none=True)
    statut = fields.String(load_default="planifie")
    created_at = fields.DateTime(dump_only=True)


class PublishEdtSchema(Schema):
    id_annee = fields.UUID(required=True)
    libelle = fields.String(allow_none=True)
    semaine = fields.Integer(allow_none=True)
    date_debut = fields.Date(allow_none=True)
    date_fin = fields.Date(allow_none=True)


@blp.route("/conflits")
class EdtConflits(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def get(self):
        """Détecte conflits enseignant (double booking) et classe (même créneau)."""
        db = get_db()
        id_annee = request.args.get("id_annee")
        creneaux = _creneaux_tenant_query(db).all()
        enriched = []
        for c in creneaux:
            aff = tenant_query(AffectationEnseignant).filter(
                AffectationEnseignant.id == c.id_affectation
            ).first()
            if not aff:
                continue
            if id_annee and str(aff.id_annee) != id_annee:
                continue
            enriched.append({
                "creneau": c,
                "id_enseignant": aff.id_enseignant,
                "id_classe": aff.id_classe,
                "id_annee": aff.id_annee,
            })

        conflits_ens = []
        conflits_classe = []
        for i, a in enumerate(enriched):
            for b in enriched[i + 1 :]:
                ca, cb = a["creneau"], b["creneau"]
                if ca.jour_semaine != cb.jour_semaine:
                    continue
                if not (ca.heure_debut < cb.heure_fin and cb.heure_debut < ca.heure_fin):
                    continue
                if a["id_enseignant"] == b["id_enseignant"]:
                    conflits_ens.append({
                        "type": "enseignant",
                        "id_enseignant": str(a["id_enseignant"]),
                        "creneaux": [str(ca.id), str(cb.id)],
                        "jour": ca.jour_semaine,
                    })
                if a["id_classe"] == b["id_classe"]:
                    conflits_classe.append({
                        "type": "classe",
                        "id_classe": str(a["id_classe"]),
                        "creneaux": [str(ca.id), str(cb.id)],
                        "jour": ca.jour_semaine,
                    })
        return jsonify({
            "conflits_enseignant": conflits_ens,
            "conflits_classe": conflits_classe,
            "total": len(conflits_ens) + len(conflits_classe),
        })


@blp.route("/remplacements")
class RemplacementsResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def get(self):
        rows = tenant_query(RemplacementEnseignant).order_by(
            RemplacementEnseignant.date_remplacement.desc()
        ).all()
        return jsonify(RemplacementSchema(many=True).dump(rows))

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(RemplacementSchema)
    @blp.response(201, RemplacementSchema)
    def post(self, data):
        db = get_db()
        get_or_404_tenant(Enseignant, data["id_enseignant_absent"])
        if data.get("id_enseignant_remplacant"):
            get_or_404_tenant(Enseignant, data["id_enseignant_remplacant"])
        row = RemplacementEnseignant(id=uuid.uuid4(), **data)
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return row, 201


@blp.route("/remplacements/<uuid:id_remplacement>")
class RemplacementDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(RemplacementSchema(partial=True))
    def put(self, data, id_remplacement):
        db = get_db()
        row = get_or_404_tenant(RemplacementEnseignant, id_remplacement)
        for k, v in data.items():
            setattr(row, k, v)
        db.commit()
        return jsonify(RemplacementSchema().dump(row))

    @jwt_required()
    @require_role("administrateur", "directeur")
    def delete(self, id_remplacement):
        db = get_db()
        row = get_or_404_tenant(RemplacementEnseignant, id_remplacement)
        db.delete(row)
        db.commit()
        return jsonify({"message": "Remplacement supprimé"})


@blp.route("/publier")
class EdtPublier(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur")
    @blp.arguments(PublishEdtSchema)
    def post(self, data):
        db = get_db()
        user = get_current_user()
        get_or_404_tenant(AnneeScolaire, data["id_annee"])
        # Désactiver publications précédentes de la même année
        prev = (
            tenant_query(EdtPublication)
            .filter(
                EdtPublication.id_annee == data["id_annee"],
                EdtPublication.actif.is_(True),
            )
            .all()
        )
        version = 1
        for p in prev:
            p.actif = False
            version = max(version, (p.version or 1) + 1)
        pub = EdtPublication(
            id=uuid.uuid4(),
            id_annee=data["id_annee"],
            libelle=data.get("libelle") or f"EDT v{version}",
            semaine=data.get("semaine"),
            date_debut=data.get("date_debut"),
            date_fin=data.get("date_fin"),
            version=version,
            publie_par=user.id,
            actif=True,
        )
        apply_tenant_school(pub)
        db.add(pub)
        db.commit()
        return jsonify({
            "id": str(pub.id),
            "version": pub.version,
            "libelle": pub.libelle,
            "publie_le": pub.publie_le.isoformat() if pub.publie_le else None,
        }), 201


@blp.route("/publications")
class EdtPublications(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    def get(self):
        rows = tenant_query(EdtPublication).order_by(EdtPublication.publie_le.desc()).all()
        return jsonify([
            {
                "id": str(r.id),
                "id_annee": str(r.id_annee),
                "libelle": r.libelle,
                "version": r.version,
                "actif": r.actif,
                "publie_le": r.publie_le.isoformat() if r.publie_le else None,
            }
            for r in rows
        ])
