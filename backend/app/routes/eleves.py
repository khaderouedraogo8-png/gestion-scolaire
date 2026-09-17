"""Module 1 — Routes élèves, inscriptions, parents."""
import io
import os
import uuid
from datetime import date

from flask import current_app, jsonify, request, send_file
from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from app.auth.jwt_handler import get_current_user
from app.auth.permissions import (
    can_view_medical_notes,
    filter_eleves_by_role,
    parent_has_eleve_access,
    require_role,
    teacher_has_eleve_access,
)
from app.extensions import get_db
from app.models import (
    AnneeScolaire,
    Classe,
    Eleve,
    EleveFratrie,
    EleveParent,
    Etablissement,
    Fratrie,
    Inscription,
    NiveauEtude,
    ParentTuteur,
)
from app.schemas.eleve import (
    EleveCreateSchema,
    EleveDetailSchema,
    EleveSchema,
    InscriptionCreateSchema,
    InscriptionSchema,
    InscriptionStatutSchema,
    ParentTuteurSchema,
)
from app.services.eleves_import import (
    build_import_template,
    confirm_eleves_import,
    preview_eleves_import,
)
from app.services.tenant import (
    apply_tenant_school,
    assert_same_school,
    get_current_school_id,
    get_or_404_tenant,
    reject_client_school_id,
    tenant_query,
)
from app.utils.audit_logger import log_audit
from app.utils.chiffrement import chiffrer_notes_medicales, dechiffrer_notes_medicales

blp = Blueprint("eleves", __name__, url_prefix="/eleves", description="Gestion des élèves")


def _generer_matricule(db, id_annee: uuid.UUID) -> str:
    """Génère un matricule selon le format configuré dans etablissement."""
    school_id = get_current_school_id()
    etab = db.query(Etablissement).filter(Etablissement.school_id == school_id).first()
    annee = get_or_404_tenant(AnneeScolaire, id_annee)
    format_str = (etab.format_matricule if etab else None) or "{ANNEE}M-{SEQ}"
    annee_court = annee.libelle[:4] if annee else str(date.today().year)
    count = tenant_query(Eleve).count() + 1
    matricule = format_str.replace("{ANNEE}", annee_court).replace("{SEQ}", str(count).zfill(3))
    return matricule


def _get_parents(db, id_eleve):
    return (
        tenant_query(ParentTuteur)
        .add_columns(EleveParent.tuteur_legal)
        .join(EleveParent, EleveParent.id_parent == ParentTuteur.id)
        .filter(EleveParent.id_eleve == id_eleve)
        .all()
    )


def _serialize_inscription(db, inscription):
    data = InscriptionSchema().dump(inscription)
    classe = tenant_query(Classe).filter(Classe.id == inscription.id_classe).first()
    annee = tenant_query(AnneeScolaire).filter(AnneeScolaire.id == inscription.id_annee).first()
    data["classe_nom"] = classe.libelle if classe else None
    data["annee_libelle"] = annee.libelle if annee else None
    return data


def _serialize_eleve_list_item(db, eleve, id_annee=None):
    result = EleveSchema().dump(eleve)
    inscr_q = tenant_query(Inscription).filter(Inscription.id_eleve == eleve.id)
    if id_annee:
        inscr_q = inscr_q.filter(Inscription.id_annee == id_annee)
    inscr = inscr_q.order_by(Inscription.date_inscription.desc()).first()
    if inscr:
        classe = tenant_query(Classe).filter(Classe.id == inscr.id_classe).first()
        result["statut"] = inscr.statut
        result["est_boursier"] = inscr.est_boursier
        result["id_classe"] = str(inscr.id_classe)
        result["id_annee"] = str(inscr.id_annee)
        result["classe_nom"] = classe.libelle if classe else None
        if classe:
            niveau = tenant_query(NiveauEtude).filter(NiveauEtude.id == classe.id_niveau).first()
            if niveau:
                result["niveau_libelle"] = niveau.libelle
                result["cycle"] = niveau.cycle
    return result


@blp.route("/")
class ElevesList(MethodView):
    @jwt_required()
    @require_role(
        "administrateur", "directeur", "secretariat", "enseignant", "agent_comptable", "parent"
    )
    def get(self):
        db = get_db()
        user = get_current_user()
        q = tenant_query(Eleve)
        statut = request.args.get("statut")
        id_classe = request.args.get("id_classe")
        id_annee = request.args.get("id_annee")
        search = request.args.get("q", "").strip()
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(max(int(request.args.get("per_page", 15)), 1), 100)

        if id_classe:
            get_or_404_tenant(Classe, id_classe)
        if id_annee:
            get_or_404_tenant(AnneeScolaire, id_annee)

        if statut == "boursier" or id_classe or (statut and statut != "boursier") or id_annee:
            q = q.join(Inscription).filter(Inscription.school_id == get_current_school_id())
            if id_annee:
                q = q.filter(Inscription.id_annee == uuid.UUID(id_annee))
            if id_classe:
                q = q.filter(Inscription.id_classe == uuid.UUID(id_classe))
            if statut == "boursier":
                q = q.filter(Inscription.est_boursier.is_(True))
            elif statut:
                q = q.filter(Inscription.statut == statut)

        if search:
            like = f"%{search}%"
            q = q.filter(
                or_(
                    Eleve.nom.ilike(like),
                    Eleve.prenom.ilike(like),
                    Eleve.matricule.ilike(like),
                )
            )

        q = filter_eleves_by_role(q, user)
        total = q.count()
        eleves = (
            q.order_by(Eleve.nom, Eleve.prenom)
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        annee_uuid = uuid.UUID(id_annee) if id_annee else None
        if not annee_uuid:
            active = tenant_query(AnneeScolaire).filter(AnneeScolaire.est_active.is_(True)).first()
            annee_uuid = active.id if active else None

        return jsonify({
            "items": [_serialize_eleve_list_item(db, e, annee_uuid) for e in eleves],
            "total": total,
            "page": page,
            "per_page": per_page,
        })

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(EleveCreateSchema)
    @blp.response(201, EleveDetailSchema)
    def post(self, data):
        db = get_db()
        reject_client_school_id(request.json)
        classe = get_or_404_tenant(Classe, data["id_classe"])
        annee = get_or_404_tenant(AnneeScolaire, data["id_annee"])
        assert_same_school(classe, annee)

        matricule = _generer_matricule(db, data["id_annee"])

        eleve = Eleve(
            id=uuid.uuid4(),
            matricule=matricule,
            nom=data["nom"],
            prenom=data["prenom"],
            sexe=data.get("sexe"),
            date_naissance=data.get("date_naissance"),
            lieu_naissance=data.get("lieu_naissance"),
            adresse=data.get("adresse"),
        )
        apply_tenant_school(eleve)
        if data.get("notes_medicales"):
            eleve.notes_medicales_chiffrees = chiffrer_notes_medicales(data["notes_medicales"])

        db.add(eleve)

        inscription = Inscription(
            id=uuid.uuid4(),
            id_eleve=eleve.id,
            id_classe=data["id_classe"],
            id_annee=data["id_annee"],
        )
        apply_tenant_school(inscription)
        assert_same_school(eleve, classe, annee, inscription)
        db.add(inscription)

        for p_data in data.get("parents", []):
            tuteur_legal = p_data.pop("tuteur_legal", False)
            parent = ParentTuteur(id=uuid.uuid4(), **p_data)
            apply_tenant_school(parent)
            db.add(parent)
            db.flush()
            link = EleveParent(id_eleve=eleve.id, id_parent=parent.id, tuteur_legal=tuteur_legal)
            db.add(link)

        db.commit()
        log_audit("CREATION_ELEVE", get_current_user().id, "eleve", eleve.id)
        return eleve, 201


@blp.route("/me/portal")
class EleveMePortal(MethodView):
    """Portail élève authentifié — si lien id_utilisateur ; sinon vue parent liée."""

    @jwt_required()
    @require_role(
        "eleve",
        "parent",
        "administrateur",
        "directeur",
        "secretariat",
    )
    def get(self):
        from app.auth.permissions import get_parent_eleve_ids
        from app.models import Absence, Note

        db = get_db()
        user = get_current_user()

        # Lien direct élève ↔ utilisateur
        eleve_linked = None
        try:
            eleve_linked = (
                tenant_query(Eleve)
                .filter(Eleve.id_utilisateur == user.id)
                .first()
            )
        except Exception:
            db.rollback()
            eleve_linked = None

        def _portal_payload(eleve: Eleve) -> dict:
            active = tenant_query(AnneeScolaire).filter(AnneeScolaire.est_active.is_(True)).first()
            insc = None
            classe_info = None
            if active:
                insc = (
                    tenant_query(Inscription)
                    .filter(
                        Inscription.id_eleve == eleve.id,
                        Inscription.id_annee == active.id,
                        Inscription.statut.in_(("inscrit", "reinscrit", "en_cours")),
                    )
                    .first()
                )
                if insc:
                    classe = tenant_query(Classe).filter(Classe.id == insc.id_classe).first()
                    if classe:
                        classe_info = {"id": str(classe.id), "libelle": classe.libelle}
            notes = (
                tenant_query(Note)
                .filter(Note.id_eleve == eleve.id)
                .order_by(Note.saisi_le.desc())
                .limit(8)
                .all()
            )
            absences = (
                tenant_query(Absence)
                .filter(Absence.id_eleve == eleve.id)
                .order_by(Absence.date_absence.desc())
                .limit(8)
                .all()
            )
            return {
                "id": str(eleve.id),
                "matricule": eleve.matricule,
                "nom": eleve.nom,
                "prenom": eleve.prenom,
                "classe": classe_info,
                "notes_recentes": [
                    {
                        "id": str(n.id),
                        "valeur_note": float(n.valeur_note) if n.valeur_note is not None else None,
                        "absent": bool(getattr(n, "absent", False)),
                    }
                    for n in notes
                ],
                "absences_recentes": [
                    {
                        "id": str(a.id),
                        "date_absence": a.date_absence.isoformat() if a.date_absence else None,
                        "type_absence": a.type_absence,
                        "justifiee": bool(a.justifiee),
                    }
                    for a in absences
                ],
            }

        if eleve_linked:
            return jsonify({
                "mode": "eleve",
                "eleve": _portal_payload(eleve_linked),
                "enfants": [],
            })

        # Fallback parent-linked
        if user.role == "parent":
            enfants = []
            for eid in get_parent_eleve_ids(user):
                e = tenant_query(Eleve).filter(Eleve.id == eid).first()
                if e:
                    enfants.append(_portal_payload(e))
            return jsonify({
                "mode": "parent",
                "eleve": None,
                "enfants": enfants,
            })

        return jsonify({
            "mode": "unlinked",
            "eleve": None,
            "enfants": [],
            "message": "Aucun élève lié à ce compte. Demandez au secrétariat de lier votre fiche.",
        })


@blp.route("/<uuid:id_eleve>")
class EleveDetail(MethodView):
    @jwt_required()
    @require_role(
        "administrateur", "directeur", "secretariat", "enseignant", "agent_comptable", "parent"
    )
    def get(self, id_eleve):
        db = get_db()
        user = get_current_user()
        if user.role == "parent" and not parent_has_eleve_access(user, id_eleve):
            return jsonify({"message": "Accès refusé"}), 403
        if user.role == "enseignant" and not teacher_has_eleve_access(user, id_eleve):
            return jsonify({"message": "Accès refusé"}), 403

        eleve = get_or_404_tenant(Eleve, id_eleve)

        result = EleveSchema().dump(eleve)
        if eleve.photo_url:
            result["photo_url"] = f"/api/eleves/{id_eleve}/photo"
        if can_view_medical_notes(user) and eleve.notes_medicales_chiffrees:
            result["notes_medicales"] = dechiffrer_notes_medicales(eleve.notes_medicales_chiffrees)

        parents = []
        for parent, tuteur_legal in _get_parents(db, id_eleve):
            p = ParentTuteurSchema().dump(parent)
            p["tuteur_legal"] = tuteur_legal
            parents.append(p)
        result["parents"] = parents

        active = tenant_query(AnneeScolaire).filter(AnneeScolaire.est_active.is_(True)).first()
        if active:
            inscr = (
                tenant_query(Inscription)
                .filter(Inscription.id_eleve == id_eleve, Inscription.id_annee == active.id)
                .first()
            )
            if inscr:
                classe = tenant_query(Classe).filter(Classe.id == inscr.id_classe).first()
                result["statut"] = inscr.statut
                result["est_boursier"] = inscr.est_boursier
                result["classe_nom"] = classe.libelle if classe else None

        return result

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(EleveSchema)
    @blp.response(200, EleveSchema)
    def put(self, data, id_eleve):
        db = get_db()
        eleve = get_or_404_tenant(Eleve, id_eleve)
        notes_med = request.json.get("notes_medicales") if request.json else None
        for key, value in data.items():
            if key != "matricule":
                setattr(eleve, key, value)
        if notes_med is not None:
            eleve.notes_medicales_chiffrees = (
                chiffrer_notes_medicales(notes_med) if notes_med else None
            )
        db.commit()
        return eleve


@blp.route("/<uuid:id_eleve>/vue-360")
class EleveVue360(MethodView):
    @jwt_required()
    @require_role(
        "administrateur", "directeur", "secretariat", "enseignant", "agent_comptable", "parent"
    )
    def get(self, id_eleve):
        """Agrégat 360° : identité, absences, notes récentes, solde / échéances."""
        from datetime import date as date_cls

        from app.models import Absence, EcheancePaiement, FraisScolaire, Note
        from app.services.finance_arrieres import list_arrieres

        db = get_db()
        user = get_current_user()
        if user.role == "parent" and not parent_has_eleve_access(user, id_eleve):
            return jsonify({"message": "Accès refusé"}), 403
        if user.role == "enseignant" and not teacher_has_eleve_access(user, id_eleve):
            return jsonify({"message": "Accès refusé"}), 403

        eleve = get_or_404_tenant(Eleve, id_eleve)
        active = tenant_query(AnneeScolaire).filter(AnneeScolaire.est_active.is_(True)).first()
        absences_count = (
            tenant_query(Absence).filter(Absence.id_eleve == id_eleve).count()
        )
        notes = (
            tenant_query(Note)
            .filter(Note.id_eleve == id_eleve)
            .order_by(Note.saisi_le.desc())
            .limit(8)
            .all()
        )
        notes_recentes = []
        for n in notes:
            notes_recentes.append({
                "id": str(n.id),
                "valeur_note": float(n.valeur_note) if n.valeur_note is not None else None,
                "absent": bool(getattr(n, "absent", False)),
                "id_evaluation": str(n.id_evaluation),
            })

        solde = None
        echeances = []
        if active and user.role != "enseignant":
            rows = list_arrieres(
                db, active.id, school_id=get_current_school_id(), as_of=date_cls.today()
            )
            mine = next((r for r in rows if r["id_eleve"] == id_eleve), None)
            if mine:
                solde = {
                    "total_du": mine["total_du"],
                    "total_paye": mine["total_paye"],
                    "arriere": mine["arriere"],
                }
            insc = (
                tenant_query(Inscription)
                .filter(
                    Inscription.id_eleve == id_eleve,
                    Inscription.id_annee == active.id,
                    Inscription.statut.in_(("inscrit", "reinscrit")),
                )
                .first()
            )
            if insc:
                classe = get_or_404_tenant(Classe, insc.id_classe)
                frais_list = (
                    tenant_query(FraisScolaire)
                    .filter(
                        FraisScolaire.id_niveau == classe.id_niveau,
                        FraisScolaire.id_annee == active.id,
                    )
                    .all()
                )
                for frais in frais_list:
                    for ec in (
                        db.query(EcheancePaiement)
                        .filter(EcheancePaiement.id_frais == frais.id)
                        .order_by(EcheancePaiement.date_echeance)
                        .all()
                    ):
                        echeances.append({
                            "id": str(ec.id),
                            "libelle": ec.libelle,
                            "montant": float(ec.montant),
                            "date_echeance": ec.date_echeance.isoformat(),
                            "motif": frais.motif,
                        })

        # Fratrie (Deerflow)
        fratrie_info = None
        link = tenant_query(EleveFratrie).filter(EleveFratrie.id_eleve == id_eleve).first()
        if link:
            fratrie = tenant_query(Fratrie).filter(Fratrie.id == link.id_fratrie).first()
            if fratrie:
                membres = []
                for lf in tenant_query(EleveFratrie).filter(EleveFratrie.id_fratrie == fratrie.id).all():
                    sibling = tenant_query(Eleve).filter(Eleve.id == lf.id_eleve).first()
                    if sibling:
                        membres.append({
                            "id": str(sibling.id),
                            "matricule": sibling.matricule,
                            "nom": sibling.nom,
                            "prenom": sibling.prenom,
                        })
                fratrie_info = {
                    "id": str(fratrie.id),
                    "libelle": fratrie.libelle,
                    "membres": membres,
                }

        return jsonify({
            "eleve": {
                "id": str(eleve.id),
                "matricule": eleve.matricule,
                "nom": eleve.nom,
                "prenom": eleve.prenom,
            },
            "absences_count": absences_count,
            "notes_recentes": notes_recentes,
            "solde": solde,
            "echeances": echeances,
            "fratrie": fratrie_info,
        })


@blp.route("/<uuid:id_eleve>/inscriptions")
class InscriptionsEleve(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "parent")
    def get(self, id_eleve):
        db = get_db()
        user = get_current_user()
        if user.role == "parent" and not parent_has_eleve_access(user, id_eleve):
            return jsonify({"message": "Accès refusé"}), 403
        get_or_404_tenant(Eleve, id_eleve)
        inscriptions = tenant_query(Inscription).filter(Inscription.id_eleve == id_eleve).all()
        return jsonify([_serialize_inscription(db, i) for i in inscriptions])

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(InscriptionCreateSchema)
    @blp.response(201, InscriptionSchema)
    def post(self, data, id_eleve):
        db = get_db()
        reject_client_school_id(request.json)
        eleve = get_or_404_tenant(Eleve, id_eleve)
        classe = get_or_404_tenant(Classe, data["id_classe"])
        annee = get_or_404_tenant(AnneeScolaire, data["id_annee"])
        assert_same_school(eleve, classe, annee)

        existing = (
            tenant_query(Inscription)
            .filter(
                Inscription.id_eleve == id_eleve,
                Inscription.id_annee == data["id_annee"],
            )
            .first()
        )
        if existing:
            return jsonify({"message": "Une inscription existe déjà pour cette année scolaire"}), 409

        inscription = Inscription(id=uuid.uuid4(), id_eleve=id_eleve, **data)
        apply_tenant_school(inscription)
        assert_same_school(eleve, classe, annee, inscription)
        db.add(inscription)
        db.commit()
        return _serialize_inscription(db, inscription), 201


@blp.route("/inscriptions/<uuid:id_inscription>/statut")
class InscriptionStatut(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    @blp.arguments(InscriptionStatutSchema)
    def patch(self, data, id_inscription):
        db = get_db()
        inscription = get_or_404_tenant(Inscription, id_inscription)
        statut = data["statut"]
        inscription.statut = statut
        inscription.date_statut_maj = date.today()
        db.commit()
        return _serialize_inscription(db, inscription)


@blp.route("/<uuid:id_eleve>/upload")
class EleveUpload(MethodView):
    ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "webp"}
    ALLOWED_MIME = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def post(self, id_eleve):
        db = get_db()
        eleve = get_or_404_tenant(Eleve, id_eleve)

        if "file" not in request.files:
            return jsonify({"message": "Fichier requis"}), 400

        file = request.files["file"]
        if not file or not file.filename:
            return jsonify({"message": "Fichier invalide"}), 400

        if not file.filename or ".." in file.filename or file.filename.startswith("/"):
            return jsonify({"message": "Nom de fichier invalide"}), 400
        filename = secure_filename(file.filename)
        if not filename:
            return jsonify({"message": "Nom de fichier invalide"}), 400
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in self.ALLOWED_EXTENSIONS:
            return jsonify({
                "message": "Type de fichier non autorisé (PDF, JPG, PNG, WEBP uniquement)"
            }), 400
        # Bloquer doubles extensions dangereuses (ex. doc.pdf.exe déjà filtré ; doc.php.pdf)
        lowered = file.filename.lower()
        for banned in (".php", ".py", ".js", ".html", ".htm", ".exe", ".sh", ".bat"):
            if banned in lowered.replace(f".{ext}", ""):
                return jsonify({"message": "Type de fichier non autorisé"}), 400

        mime = (file.mimetype or "").split(";")[0].strip().lower()
        if mime and mime not in self.ALLOWED_MIME:
            return jsonify({"message": "Type MIME non autorisé"}), 400

        doc_type = request.form.get("type", "autre")
        upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "eleves", str(id_eleve))
        os.makedirs(upload_dir, exist_ok=True)
        # Nom 100 % serveur — jamais le nom client comme chemin
        safe_name = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(upload_dir, safe_name)
        file.save(filepath)

        pieces = list(eleve.pieces_justificatives or [])
        pieces.append({
            "type": doc_type,
            "url": filepath,
            "filename": safe_name,
            "date_upload": date.today().isoformat(),
        })
        eleve.pieces_justificatives = pieces
        db.commit()
        return jsonify({"message": "Fichier uploadé", "filename": safe_name}), 201


@blp.route("/<uuid:id_eleve>/photo")
class ElevePhoto(MethodView):
    @jwt_required()
    @require_role(
        "administrateur", "directeur", "secretariat", "enseignant", "agent_comptable", "parent"
    )
    def get(self, id_eleve):
        get_db()
        user = get_current_user()
        if user.role == "parent" and not parent_has_eleve_access(user, id_eleve):
            return jsonify({"message": "Accès refusé"}), 403
        if user.role == "enseignant" and not teacher_has_eleve_access(user, id_eleve):
            return jsonify({"message": "Accès refusé"}), 403
        eleve = get_or_404_tenant(Eleve, id_eleve)
        if not eleve.photo_url or not os.path.isfile(eleve.photo_url):
            return jsonify({"message": "Photo introuvable"}), 404
        return send_file(eleve.photo_url)

    ALLOWED_PHOTO_EXT = {"jpg", "jpeg", "png", "webp"}
    ALLOWED_PHOTO_MIME = {"image/jpeg", "image/png", "image/webp"}

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def post(self, id_eleve):
        db = get_db()
        eleve = get_or_404_tenant(Eleve, id_eleve)
        if "file" not in request.files:
            return jsonify({"message": "Fichier requis"}), 400
        file = request.files["file"]
        if not file or not file.filename:
            return jsonify({"message": "Fichier invalide"}), 400
        filename = secure_filename(file.filename)
        # Rejeter path traversal / noms suspects même après secure_filename
        if not filename or ".." in file.filename or "/" in file.filename or "\\" in file.filename:
            return jsonify({"message": "Nom de fichier invalide"}), 400
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in self.ALLOWED_PHOTO_EXT:
            return jsonify({"message": "Photo : JPG, PNG ou WEBP uniquement"}), 400
        mime = (file.mimetype or "").split(";")[0].strip().lower()
        if mime and mime not in self.ALLOWED_PHOTO_MIME:
            return jsonify({"message": "Type MIME photo non autorisé"}), 400
        upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "eleves", str(id_eleve), "photo")
        os.makedirs(upload_dir, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(upload_dir, safe_name)
        file.save(filepath)
        eleve.photo_url = filepath
        db.commit()
        return jsonify({"message": "Photo enregistrée", "photo_url": f"/api/eleves/{id_eleve}/photo"}), 201


@blp.route("/import/template")
class ElevesImportTemplate(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def get(self):
        payload = build_import_template()
        return send_file(
            io.BytesIO(payload),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="modele_import_eleves.xlsx",
        )


@blp.route("/import/preview")
class ElevesImportPreview(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def post(self):
        db = get_db()
        file = request.files.get("file")
        if not file or not file.filename:
            return jsonify({"message": "Fichier requis"}), 400
        try:
            id_annee = uuid.UUID(request.form.get("id_annee") or request.args.get("id_annee"))
        except (TypeError, ValueError):
            return jsonify({"message": "id_annee requis"}), 400
        default_classe = request.form.get("id_classe") or request.args.get("id_classe")
        default_id_classe = None
        if default_classe:
            try:
                default_id_classe = uuid.UUID(default_classe)
            except ValueError:
                return jsonify({"message": "id_classe invalide"}), 400
        result = preview_eleves_import(
            db, file, id_annee=id_annee, default_id_classe=default_id_classe
        )
        return jsonify(result), 200


@blp.route("/import/confirm")
class ElevesImportConfirm(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def post(self):
        db = get_db()
        user = get_current_user()
        body = request.get_json(silent=True) or {}
        reject_client_school_id(body)
        try:
            id_annee = uuid.UUID(str(body.get("id_annee")))
        except (TypeError, ValueError):
            return jsonify({"message": "id_annee requis"}), 400
        rows = body.get("rows") or []
        if not isinstance(rows, list):
            return jsonify({"message": "rows doit être une liste"}), 400
        # N'importer que les lignes OK envoyées par le client (revalidées serveur)
        ok_rows = [r for r in rows if (r.get("status") == "ok" or not r.get("status"))]
        # Flatten: accept either {data: {...}} or flat row
        normalized = []
        for r in ok_rows:
            if "data" in r and isinstance(r["data"], dict):
                item = dict(r["data"])
                item["line"] = r.get("line")
                normalized.append(item)
            else:
                normalized.append(r)
        result = confirm_eleves_import(
            db, id_annee=id_annee, rows=normalized, user_id=user.id
        )
        return jsonify(result), 201


@blp.route("/reincription/batch")
class ReincriptionBatch(MethodView):
    """Alias legacy — préférer /reinscription-batch."""

    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def post(self):
        return _reinscription_batch_handler()


@blp.route("/reinscription-batch")
class ReinscriptionBatch(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat")
    def post(self):
        """Réinscription batch : {id_annee_source, id_annee_cible, id_classe_map?, eleve_ids?}."""
        return _reinscription_batch_handler()


def _reinscription_batch_handler():
    db = get_db()
    body = request.get_json(silent=True) or {}
    reject_client_school_id(body)

    id_annee_source_raw = body.get("id_annee_source")
    id_annee_cible_raw = body.get("id_annee_cible")
    try:
        id_annee_cible = uuid.UUID(str(id_annee_cible_raw))
    except (TypeError, ValueError):
        return jsonify({"message": "id_annee_cible requis"}), 400
    get_or_404_tenant(AnneeScolaire, id_annee_cible)

    # Legacy format : eleves[{id_eleve, id_classe}]
    legacy_items = body.get("eleves")
    if isinstance(legacy_items, list) and legacy_items and not id_annee_source_raw:
        created, skipped, errors = [], [], []
        for item in legacy_items:
            try:
                id_eleve = uuid.UUID(str(item.get("id_eleve")))
                id_classe = uuid.UUID(str(item.get("id_classe")))
            except (TypeError, ValueError):
                errors.append({"item": item, "error": "id_eleve/id_classe invalides"})
                continue
            get_or_404_tenant(Eleve, id_eleve)
            get_or_404_tenant(Classe, id_classe)
            existing = (
                tenant_query(Inscription)
                .filter(
                    Inscription.id_eleve == id_eleve,
                    Inscription.id_annee == id_annee_cible,
                    Inscription.statut.in_(("inscrit", "reinscrit")),
                )
                .first()
            )
            if existing:
                skipped.append({"id_eleve": str(id_eleve), "id_inscription": str(existing.id)})
                continue
            insc = Inscription(
                id=uuid.uuid4(),
                id_eleve=id_eleve,
                id_classe=id_classe,
                id_annee=id_annee_cible,
                statut="reinscrit",
                date_inscription=date.today(),
            )
            apply_tenant_school(insc)
            db.add(insc)
            created.append({"id_eleve": str(id_eleve), "id_inscription": str(insc.id)})
        db.commit()
        return jsonify({
            "created": created,
            "skipped": skipped,
            "errors": errors,
            "count_created": len(created),
        }), 201

    try:
        id_annee_source = uuid.UUID(str(id_annee_source_raw))
    except (TypeError, ValueError):
        return jsonify({"message": "id_annee_source requis"}), 400
    get_or_404_tenant(AnneeScolaire, id_annee_source)

    id_classe_map_raw = body.get("id_classe_map") or {}
    if not isinstance(id_classe_map_raw, dict):
        return jsonify({"message": "id_classe_map doit être un objet"}), 400
    id_classe_map = {}
    for k, v in id_classe_map_raw.items():
        try:
            id_classe_map[uuid.UUID(str(k))] = uuid.UUID(str(v))
        except (TypeError, ValueError):
            return jsonify({"message": f"id_classe_map invalide: {k}→{v}"}), 400

    eleve_ids_raw = body.get("eleve_ids")
    filter_ids = None
    if eleve_ids_raw is not None:
        if not isinstance(eleve_ids_raw, list):
            return jsonify({"message": "eleve_ids doit être une liste"}), 400
        try:
            filter_ids = {uuid.UUID(str(x)) for x in eleve_ids_raw}
        except (TypeError, ValueError):
            return jsonify({"message": "eleve_ids invalides"}), 400

    sources = (
        tenant_query(Inscription)
        .filter(
            Inscription.id_annee == id_annee_source,
            Inscription.statut.in_(("inscrit", "reinscrit")),
        )
        .all()
    )
    created, skipped, errors = [], [], []
    for src in sources:
        if filter_ids is not None and src.id_eleve not in filter_ids:
            continue
        id_classe_cible = id_classe_map.get(src.id_classe, src.id_classe)
        try:
            get_or_404_tenant(Eleve, src.id_eleve)
            get_or_404_tenant(Classe, id_classe_cible)
        except Exception as exc:
            errors.append({"id_eleve": str(src.id_eleve), "error": str(exc)})
            continue
        existing = (
            tenant_query(Inscription)
            .filter(
                Inscription.id_eleve == src.id_eleve,
                Inscription.id_annee == id_annee_cible,
                Inscription.statut.in_(("inscrit", "reinscrit")),
            )
            .first()
        )
        if existing:
            skipped.append({
                "id_eleve": str(src.id_eleve),
                "id_inscription": str(existing.id),
            })
            continue
        insc = Inscription(
            id=uuid.uuid4(),
            id_eleve=src.id_eleve,
            id_classe=id_classe_cible,
            id_annee=id_annee_cible,
            statut="reinscrit",
            est_boursier=bool(src.est_boursier),
            taux_reduction=src.taux_reduction or 0,
            date_inscription=date.today(),
        )
        apply_tenant_school(insc)
        db.add(insc)
        created.append({
            "id_eleve": str(src.id_eleve),
            "id_inscription": str(insc.id),
            "id_classe": str(id_classe_cible),
            "id_classe_source": str(src.id_classe),
        })
    db.commit()
    return jsonify({
        "id_annee_source": str(id_annee_source),
        "id_annee_cible": str(id_annee_cible),
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "count_created": len(created),
        "count_skipped": len(skipped),
    }), 201


@blp.route("/<uuid:id_eleve>/dossier.pdf")
class EleveDossierPdf(MethodView):
    @jwt_required()
    @require_role("administrateur", "directeur", "secretariat", "enseignant", "parent")
    def get(self, id_eleve):
        """Dossier élève PDF (identité, parents, inscriptions, solde, absences, notes)."""
        from datetime import UTC, datetime

        from flask import render_template

        from app.models import Absence, Note
        from app.services.finance_arrieres import list_arrieres
        from app.services.pdf_render import html_to_pdf

        db = get_db()
        user = get_current_user()
        if user.role == "parent" and not parent_has_eleve_access(user, id_eleve):
            return jsonify({"message": "Accès refusé"}), 403
        if user.role == "enseignant" and not teacher_has_eleve_access(user, id_eleve):
            return jsonify({"message": "Accès refusé"}), 403

        eleve = get_or_404_tenant(Eleve, id_eleve)
        etab = (
            db.query(Etablissement)
            .filter(Etablissement.school_id == get_current_school_id())
            .first()
        )

        parents = []
        for parent, tuteur_legal in _get_parents(db, id_eleve):
            parents.append({
                "nom": parent.nom,
                "prenom": parent.prenom,
                "lien_parente": parent.lien_parente,
                "telephone": parent.telephone,
                "email": parent.email,
                "tuteur_legal": tuteur_legal,
            })

        inscriptions = (
            tenant_query(Inscription)
            .filter(Inscription.id_eleve == id_eleve)
            .order_by(Inscription.date_inscription.desc())
            .all()
        )
        insc_rows = []
        for insc in inscriptions:
            classe = tenant_query(Classe).filter(Classe.id == insc.id_classe).first()
            annee = tenant_query(AnneeScolaire).filter(AnneeScolaire.id == insc.id_annee).first()
            insc_rows.append({
                "classe": classe.libelle if classe else "—",
                "annee": annee.libelle if annee else "—",
                "statut": insc.statut,
                "est_boursier": bool(insc.est_boursier),
                "taux_reduction": float(insc.taux_reduction or 0),
            })

        solde = None
        active = tenant_query(AnneeScolaire).filter(AnneeScolaire.est_active.is_(True)).first()
        if active and user.role != "enseignant":
            rows = list_arrieres(
                db, active.id, school_id=get_current_school_id(), as_of=date.today()
            )
            mine = next((r for r in rows if r["id_eleve"] == id_eleve), None)
            if mine:
                solde = {
                    "total_du": mine["total_du"],
                    "total_paye": mine["total_paye"],
                    "arriere": mine["arriere"],
                }
            else:
                solde = {"total_du": 0, "total_paye": 0, "arriere": 0}

        absences_rows = (
            tenant_query(Absence)
            .filter(Absence.id_eleve == id_eleve)
            .order_by(Absence.date_absence.desc())
            .limit(15)
            .all()
        )
        absences = [
            {
                "date": a.date_absence.isoformat() if a.date_absence else "—",
                "type": a.type_absence,
                "motif": a.motif,
                "justifiee": bool(a.justifiee),
            }
            for a in absences_rows
        ]

        notes_rows = (
            tenant_query(Note)
            .filter(Note.id_eleve == id_eleve)
            .order_by(Note.saisi_le.desc())
            .limit(15)
            .all()
        )
        notes = [
            {
                "id_evaluation": str(n.id_evaluation),
                "libelle": None,
                "valeur": float(n.valeur_note) if n.valeur_note is not None else None,
                "absent": bool(getattr(n, "absent", False)),
            }
            for n in notes_rows
        ]

        html = render_template(
            "dossier_eleve.html",
            etablissement=etab,
            eleve=eleve,
            parents=parents,
            inscriptions=insc_rows,
            solde=solde,
            absences=absences,
            notes=notes,
            date_generation=datetime.now(UTC),
        )
        upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "dossiers")
        os.makedirs(upload_dir, exist_ok=True)
        path = os.path.join(upload_dir, f"dossier_{id_eleve}.pdf")
        html_to_pdf(html, path)
        return send_file(path, as_attachment=True, download_name=f"dossier_{eleve.matricule}.pdf")
