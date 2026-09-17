"""Module 5 — Routes absences et discipline (contrôle d'accès objet)."""
import os
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from flask import current_app, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from marshmallow import Schema, fields
from werkzeug.utils import secure_filename

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import (
    get_parent_eleve_ids,
    get_teacher_class_ids,
    parent_has_eleve_access,
    require_role,
    teacher_has_eleve_access,
)
from app.extensions import get_db
from app.models import (
    Absence,
    AbsenceJustificatif,
    AlerteDecrochage,
    AnneeScolaire,
    Classe,
    Eleve,
    IncidentDisciplinaire,
    Inscription,
)
from app.schemas.absences import AbsenceSchema, IncidentDisciplinaireSchema
from app.services.envoi_notification import creer_notification
from app.services.tenant import (
    apply_tenant_school,
    get_or_404_tenant,
    reject_client_school_id,
    tenant_query,
)
from app.utils.pagination import empty_pagination, paginate_query, pagination_payload, parse_pagination

blp = Blueprint("absences", __name__, url_prefix="/absences", description="Absences et discipline")


def _serialize_absence(db, absence):
    data = AbsenceSchema().dump(absence)
    eleve = tenant_query(Eleve).filter(Eleve.id == absence.id_eleve).first()
    if eleve:
        data["prenom"] = eleve.prenom
        data["nom"] = eleve.nom
        data["matricule"] = eleve.matricule
        data["eleve"] = {"prenom": eleve.prenom, "nom": eleve.nom, "matricule": eleve.matricule}
    return data


def _serialize_incident(db, incident):
    data = IncidentDisciplinaireSchema().dump(incident)
    eleve = tenant_query(Eleve).filter(Eleve.id == incident.id_eleve).first()
    if eleve:
        data["prenom"] = eleve.prenom
        data["nom"] = eleve.nom
        data["matricule"] = eleve.matricule
        data["eleve"] = {"prenom": eleve.prenom, "nom": eleve.nom, "matricule": eleve.matricule}
    return data


def _eleve_ids_for_classe(db, id_classe, id_annee=None):
    q = tenant_query(Inscription).with_entities(Inscription.id_eleve).filter(
        Inscription.id_classe == id_classe,
        Inscription.statut.in_(("inscrit", "reinscrit")),
    )
    if id_annee:
        q = q.filter(Inscription.id_annee == id_annee)
    return [r[0] for r in q.all()]


@blp.route("/")
class AbsencesResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "parent")
    def get(self):
        db = get_db()
        user = get_current_user()
        q = tenant_query(Absence)
        id_eleve = request.args.get("id_eleve")
        id_classe = request.args.get("id_classe")
        date_debut = request.args.get("date_debut")
        date_fin = request.args.get("date_fin")

        # Isolation objet : parent → ses enfants ; enseignant → ses classes uniquement
        # (pas de filtre année active : l'affectation classe suffit pour l'autorisation)
        allowed_eleve_ids = None
        if user.role == "parent":
            allowed_eleve_ids = get_parent_eleve_ids(user)
            if not allowed_eleve_ids:
                return jsonify(empty_pagination())
            q = q.filter(Absence.id_eleve.in_(allowed_eleve_ids))
        elif user.role == "enseignant":
            class_ids = get_teacher_class_ids(user)
            if not class_ids:
                return jsonify(empty_pagination())
            allowed_eleve_ids = []
            for cid in class_ids:
                allowed_eleve_ids.extend(_eleve_ids_for_classe(db, cid, id_annee=None))
            allowed_eleve_ids = list(set(allowed_eleve_ids))
            if not allowed_eleve_ids and not id_eleve:
                return jsonify(empty_pagination())
            if allowed_eleve_ids:
                q = q.filter(Absence.id_eleve.in_(allowed_eleve_ids))

        if id_classe:
            cid = uuid.UUID(id_classe)
            get_or_404_tenant(Classe, cid)
            if user.role == "enseignant" and cid not in set(get_teacher_class_ids(user)):
                return jsonify({"message": "Accès refusé"}), 403
            inscr_eleve_ids = _eleve_ids_for_classe(db, cid, id_annee=None)
            if not inscr_eleve_ids:
                return jsonify(empty_pagination())
            q = q.filter(Absence.id_eleve.in_(inscr_eleve_ids))

        if id_eleve:
            eid = uuid.UUID(id_eleve)
            get_or_404_tenant(Eleve, eid)
            # Toujours vérifier l'objet AVANT de renvoyer une liste vide
            if user.role == "parent" and not parent_has_eleve_access(user, eid):
                return jsonify({"message": "Accès refusé"}), 403
            if user.role == "enseignant" and not teacher_has_eleve_access(user, eid):
                return jsonify({"message": "Accès refusé"}), 403
            if allowed_eleve_ids is not None and eid not in allowed_eleve_ids:
                return jsonify({"message": "Accès refusé"}), 403
            q = q.filter(Absence.id_eleve == eid)

        if date_debut:
            q = q.filter(Absence.date_absence >= date_debut)
        if date_fin:
            q = q.filter(Absence.date_absence <= date_fin)
        page, per_page = parse_pagination()
        items, total, pages = paginate_query(
            q.order_by(Absence.date_absence.desc()), page, per_page
        )
        return jsonify(
            pagination_payload(
                [_serialize_absence(db, a) for a in items],
                page=page,
                per_page=per_page,
                total=total,
                pages=pages,
            )
        )

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    @blp.arguments(AbsenceSchema)
    @blp.response(201, AbsenceSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        user = get_current_user()
        id_eleve = data["id_eleve"]
        get_or_404_tenant(Eleve, id_eleve)
        if user.role == "enseignant" and not teacher_has_eleve_access(user, id_eleve):
            return jsonify({"message": "Accès refusé — élève hors de vos classes"}), 403

        absence = Absence(id=uuid.uuid4(), signale_par=user.id, **data)
        apply_tenant_school(absence)
        db.add(absence)
        db.commit()

        eleve = tenant_query(Eleve).filter(Eleve.id == id_eleve).first()
        nom_eleve = f"{eleve.prenom} {eleve.nom}" if eleve else "Votre enfant"
        contenu = f"{nom_eleve} : absence enregistrée le {data['date_absence']}."
        # Notifier tous les tuteurs liés (email + inbox). SMS si demandé via ?canal=
        canal = (request.args.get("canal") or "email").strip().lower()
        if canal not in ("email", "sms", "whatsapp", "interne"):
            canal = "email"
        if canal == "whatsapp":
            from app.services.channels.whatsapp import whatsapp_status

            if not whatsapp_status().configured:
                canal = "email"
        from app.models import EleveParent

        links = db.query(EleveParent).filter(EleveParent.id_eleve == id_eleve).all()
        if links:
            for link in links:
                creer_notification(
                    canal=canal,
                    type_notification="absence",
                    contenu=contenu,
                    id_eleve=id_eleve,
                    id_parent=link.id_parent,
                )
                if canal != "interne":
                    creer_notification(
                        canal="interne",
                        type_notification="absence",
                        contenu=contenu,
                        id_eleve=id_eleve,
                        id_parent=link.id_parent,
                    )
        else:
            creer_notification(
                canal=canal,
                type_notification="absence",
                contenu=contenu,
                id_eleve=id_eleve,
            )
        return absence, 201


@blp.route("/<uuid:id_absence>")
class AbsenceDetail(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    @blp.arguments(AbsenceSchema)
    def put(self, data, id_absence):
        db = get_db()
        user = get_current_user()
        absence = get_or_404_tenant(Absence, id_absence)
        if user.role == "enseignant" and not teacher_has_eleve_access(user, absence.id_eleve):
            return jsonify({"message": "Accès refusé"}), 403
        for key, value in data.items():
            if key not in ("id_eleve",):
                setattr(absence, key, value)
        db.commit()
        return jsonify(_serialize_absence(db, absence))


@blp.route("/discipline")
class DisciplineResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    def get(self):
        db = get_db()
        user = get_current_user()
        q = tenant_query(IncidentDisciplinaire)
        id_eleve = request.args.get("id_eleve")

        if user.role == "enseignant":
            class_ids = get_teacher_class_ids(user)
            if not class_ids:
                return jsonify(empty_pagination())
            annee = tenant_query(AnneeScolaire).filter(AnneeScolaire.est_active.is_(True)).first()
            allowed = []
            for cid in class_ids:
                allowed.extend(_eleve_ids_for_classe(db, cid, annee.id if annee else None))
            if not allowed:
                return jsonify(empty_pagination())
            q = q.filter(IncidentDisciplinaire.id_eleve.in_(set(allowed)))

        if id_eleve:
            eid = uuid.UUID(id_eleve)
            get_or_404_tenant(Eleve, eid)
            if user.role == "enseignant" and not teacher_has_eleve_access(user, eid):
                return jsonify({"message": "Accès refusé"}), 403
            q = q.filter(IncidentDisciplinaire.id_eleve == eid)
        page, per_page = parse_pagination()
        items, total, pages = paginate_query(
            q.order_by(IncidentDisciplinaire.date_incident.desc()), page, per_page
        )
        return jsonify(
            pagination_payload(
                [_serialize_incident(db, i) for i in items],
                page=page,
                per_page=per_page,
                total=total,
                pages=pages,
            )
        )

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    @blp.arguments(IncidentDisciplinaireSchema)
    @blp.response(201, IncidentDisciplinaireSchema)
    def post(self, data):
        reject_client_school_id(request.get_json(silent=True))
        db = get_db()
        user = get_current_user()
        get_or_404_tenant(Eleve, data["id_eleve"])
        if user.role == "enseignant" and not teacher_has_eleve_access(user, data["id_eleve"]):
            return jsonify({"message": "Accès refusé — élève hors de vos classes"}), 403
        incident = IncidentDisciplinaire(id=uuid.uuid4(), declare_par=user.id, **data)
        apply_tenant_school(incident)
        db.add(incident)
        db.commit()
        return incident, 201


class JustificatifSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_absence = fields.UUID(required=True)
    fichier_url = fields.String(allow_none=True)
    motif = fields.String(allow_none=True)
    valide = fields.Boolean(dump_only=True)
    valide_par = fields.UUID(dump_only=True, allow_none=True)
    date_depot = fields.DateTime(dump_only=True)
    valide_le = fields.DateTime(dump_only=True, allow_none=True)


class AlerteSchema(Schema):
    id = fields.UUID(dump_only=True)
    id_eleve = fields.UUID(required=True)
    type_alerte = fields.String(required=True)
    niveau = fields.String(load_default="moyen")
    score = fields.Decimal(as_string=True, allow_none=True)
    statut = fields.String(load_default="ouverte")
    details = fields.Dict(allow_none=True)
    traite_par = fields.UUID(dump_only=True, allow_none=True)
    traite_le = fields.DateTime(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)


@blp.route("/<uuid:id_absence>/justificatifs")
class AbsenceJustificatifs(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "parent")
    def get(self, id_absence):
        get_or_404_tenant(Absence, id_absence)
        rows = (
            tenant_query(AbsenceJustificatif)
            .filter(AbsenceJustificatif.id_absence == id_absence)
            .order_by(AbsenceJustificatif.date_depot.desc())
            .all()
        )
        return jsonify(JustificatifSchema(many=True).dump(rows))

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "parent")
    def post(self, id_absence):
        """Upload justificatif (multipart) ou JSON motif + fichier_url."""
        db = get_db()
        absence = get_or_404_tenant(Absence, id_absence)
        user = get_current_user()
        if user.role == "parent" and not parent_has_eleve_access(user, absence.id_eleve):
            return jsonify({"message": "Accès refusé"}), 403

        motif = None
        fichier_url = None
        if request.content_type and "multipart/form-data" in request.content_type:
            motif = request.form.get("motif")
            if "file" in request.files and request.files["file"].filename:
                f = request.files["file"]
                filename = secure_filename(f.filename)
                ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
                upload_dir = os.path.join(
                    current_app.config["UPLOAD_FOLDER"], "justificatifs", str(id_absence)
                )
                os.makedirs(upload_dir, exist_ok=True)
                safe = f"{uuid.uuid4().hex}.{ext}"
                path = os.path.join(upload_dir, safe)
                f.save(path)
                fichier_url = path
        else:
            body = request.get_json(silent=True) or {}
            motif = body.get("motif")
            fichier_url = body.get("fichier_url")

        row = AbsenceJustificatif(
            id=uuid.uuid4(),
            id_absence=id_absence,
            fichier_url=fichier_url,
            motif=motif,
            valide=False,
        )
        apply_tenant_school(row)
        db.add(row)
        db.commit()
        return jsonify(JustificatifSchema().dump(row)), 201


@blp.route("/justificatifs/<uuid:id_justificatif>/valider")
class JustificatifValider(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def post(self, id_justificatif):
        db = get_db()
        user = get_current_user()
        row = get_or_404_tenant(AbsenceJustificatif, id_justificatif)
        row.valide = True
        row.valide_par = user.id
        row.valide_le = datetime.now(UTC)
        absence = get_or_404_tenant(Absence, row.id_absence)
        absence.justifiee = True
        if row.motif and not absence.motif:
            absence.motif = row.motif
        db.commit()
        return jsonify(JustificatifSchema().dump(row))


@blp.route("/alertes-decrochage")
class AlertesDecrochageResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    def get(self):
        q = tenant_query(AlerteDecrochage)
        statut = request.args.get("statut")
        if statut:
            q = q.filter(AlerteDecrochage.statut == statut)
        rows = q.order_by(AlerteDecrochage.created_at.desc()).all()
        return jsonify(AlerteSchema(many=True).dump(rows))


@blp.route("/alertes-decrochage/scan")
class AlertesDecrochageScan(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def post(self):
        """Scan absences récentes → ouvre alertes décrochage si seuil dépassé."""
        db = get_db()
        body = request.get_json(silent=True) or {}
        seuil = int(body.get("seuil_absences") or 5)
        fenetre_jours = int(body.get("fenetre_jours") or 30)
        since = datetime.now(UTC).date() - timedelta(days=fenetre_jours)

        eleves = tenant_query(Eleve).all()
        created = []
        for eleve in eleves:
            count = (
                tenant_query(Absence)
                .filter(
                    Absence.id_eleve == eleve.id,
                    Absence.date_absence >= since,
                    Absence.justifiee.is_(False),
                )
                .count()
            )
            if count < seuil:
                continue
            existing = (
                tenant_query(AlerteDecrochage)
                .filter(
                    AlerteDecrochage.id_eleve == eleve.id,
                    AlerteDecrochage.statut == "ouverte",
                    AlerteDecrochage.type_alerte == "absences_repetees",
                )
                .first()
            )
            if existing:
                existing.score = Decimal(count)
                existing.details = {"absences": count, "fenetre_jours": fenetre_jours}
                continue
            alerte = AlerteDecrochage(
                id=uuid.uuid4(),
                id_eleve=eleve.id,
                type_alerte="absences_repetees",
                niveau="eleve" if count >= seuil * 2 else "moyen",
                score=Decimal(count),
                statut="ouverte",
                details={"absences": count, "fenetre_jours": fenetre_jours, "seuil": seuil},
            )
            apply_tenant_school(alerte)
            db.add(alerte)
            created.append(alerte)
        db.commit()
        return jsonify({
            "created": len(created),
            "alertes": AlerteSchema(many=True).dump(created),
        }), 201


@blp.route("/appel")
class AppelMobileResource(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant")
    def post(self):
        """Appel de présence rapide par classe (mobile-friendly).

        Body: { id_classe, date_absence?, presents: [id_eleve], absents: [{id_eleve, type_absence?}] }
        """
        db = get_db()
        user = get_current_user()
        body = request.get_json(silent=True) or {}
        id_classe = body.get("id_classe")
        if not id_classe:
            return jsonify({"message": "id_classe requis"}), 400
        classe = get_or_404_tenant(Classe, uuid.UUID(id_classe))
        if user.role == "enseignant":
            allowed = get_teacher_class_ids(user)
            if classe.id not in allowed:
                return jsonify({"message": "Classe hors périmètre"}), 403
        jour = body.get("date_absence")
        if jour:
            from datetime import date as date_cls
            jour = date_cls.fromisoformat(jour)
        else:
            jour = datetime.now(UTC).date()

        presents = {uuid.UUID(x) for x in (body.get("presents") or [])}
        absents_raw = body.get("absents") or []
        created = []
        for item in absents_raw:
            if isinstance(item, str):
                eid = uuid.UUID(item)
                typ = "absence"
            else:
                eid = uuid.UUID(item["id_eleve"])
                typ = item.get("type_absence") or "absence"
            if eid in presents:
                continue
            existing = (
                tenant_query(Absence)
                .filter(Absence.id_eleve == eid, Absence.date_absence == jour)
                .first()
            )
            if existing:
                continue
            row = Absence(
                id=uuid.uuid4(),
                id_eleve=eid,
                date_absence=jour,
                type_absence=typ,
                justifiee=False,
                saisi_par=user.id,
            )
            apply_tenant_school(row)
            db.add(row)
            created.append(str(row.id))
        db.commit()
        return jsonify({
            "message": f"Appel enregistré — {len(created)} absence(s)",
            "date": jour.isoformat(),
            "id_classe": str(classe.id),
            "absences_crees": created,
            "presents": len(presents),
        }), 201
