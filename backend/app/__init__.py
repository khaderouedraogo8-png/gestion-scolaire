"""Factory Flask — enregistrement des extensions et blueprints."""
import os

from flask import Flask

from app.config import config_by_name
from app.extensions import api, cors, init_db, jwt, limiter


def create_app(config_name: str | None = None) -> Flask:
    config_name = config_name or os.getenv("FLASK_ENV", "development")
    if config_name not in config_by_name:
        config_name = "development"

    application = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates_pdf"),
    )
    application.config.from_object(config_by_name[config_name])

    if config_name == "production":
        config_by_name["production"].validate_secrets()
    # Évite les redirections 308 (/api/eleves → /api/eleves/) qui suppriment le header Authorization.
    application.url_map.strict_slashes = False

    if config_name == "production":
        from werkzeug.middleware.proxy_fix import ProxyFix

        application.wsgi_app = ProxyFix(
            application.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
        )

    os.makedirs(application.config["UPLOAD_FOLDER"], exist_ok=True)

    init_db(application)
    jwt.init_app(application)
    limiter.init_app(application)
    cors.init_app(application, origins=application.config["CORS_ORIGINS"], supports_credentials=True)
    api.init_app(application)

    import app.models  # noqa: F401
    from app.routes.absences import blp as absences_blp
    from app.routes.admission import blp as admission_blp
    from app.routes.audit import blp as audit_blp
    from app.routes.auth import blp as auth_blp
    from app.routes.comptabilite import blp as comptabilite_blp
    from app.routes.conseil_classe import blp as conseil_classe_blp
    from app.routes.dashboard import blp as dashboard_blp
    from app.routes.documents import blp as documents_blp
    from app.routes.elearning import blp as elearning_blp
    from app.routes.eleves import blp as eleves_blp
    from app.routes.emploi_temps import blp as emploi_temps_blp
    from app.routes.etablissement import blp as etablissement_blp
    from app.routes.finance import blp as finance_blp
    from app.routes.fratries import blp as fratries_blp
    from app.routes.front_office import blp as front_office_blp
    from app.routes.grading import blp as grading_blp
    from app.routes.inventaire import blp as inventaire_blp
    from app.routes.notes import blp as notes_blp
    from app.routes.notifications import blp as notifications_blp
    from app.routes.otp_auth import blp as otp_auth_blp
    from app.routes.pedagogie import blp as pedagogie_blp
    from app.routes.platform import blp as platform_blp
    from app.routes.rh import blp as rh_blp
    from app.routes.schools import blp as schools_blp
    from app.routes.users import blp as users_blp
    from app.routes.vie_scolaire import blp as vie_scolaire_blp
    from app.routes.webhooks import blp as webhooks_blp

    # Auth : routes plates (/api/login, /api/me, …)
    api.register_blueprint(auth_blp, url_prefix="/api")
    api.register_blueprint(otp_auth_blp, url_prefix="/api/auth")
    api.register_blueprint(users_blp, url_prefix="/api/users")
    api.register_blueprint(schools_blp, url_prefix="/api/schools")
    api.register_blueprint(platform_blp, url_prefix="/api/platform")
    # Modules : préfixe explicite pour éviter les collisions sur /api/
    api.register_blueprint(etablissement_blp, url_prefix="/api/etablissement")
    api.register_blueprint(eleves_blp, url_prefix="/api/eleves")
    api.register_blueprint(notes_blp, url_prefix="/api/notes")
    api.register_blueprint(pedagogie_blp, url_prefix="/api/pedagogie")
    api.register_blueprint(finance_blp, url_prefix="/api/finance")
    api.register_blueprint(emploi_temps_blp, url_prefix="/api/emploi-temps")
    api.register_blueprint(absences_blp, url_prefix="/api/absences")
    api.register_blueprint(documents_blp, url_prefix="/api/documents")
    api.register_blueprint(notifications_blp, url_prefix="/api/notifications")
    api.register_blueprint(dashboard_blp, url_prefix="/api/dashboard")
    api.register_blueprint(audit_blp, url_prefix="/api/audit")
    api.register_blueprint(grading_blp, url_prefix="/api")
    # Deerflow modules A/B
    api.register_blueprint(admission_blp, url_prefix="/api/admission")
    api.register_blueprint(fratries_blp, url_prefix="/api/fratries")
    api.register_blueprint(conseil_classe_blp, url_prefix="/api/conseil-classe")
    api.register_blueprint(vie_scolaire_blp, url_prefix="/api/vie-scolaire")
    api.register_blueprint(rh_blp, url_prefix="/api/rh")
    api.register_blueprint(front_office_blp, url_prefix="/api/front-office")
    api.register_blueprint(inventaire_blp, url_prefix="/api/inventaire")
    api.register_blueprint(elearning_blp, url_prefix="/api/elearning")
    api.register_blueprint(comptabilite_blp, url_prefix="/api/comptabilite")
    api.register_blueprint(webhooks_blp, url_prefix="/api/webhooks")

    from app.utils.errors import register_error_handlers

    register_error_handlers(application)

    @application.cli.command("seed")
    def seed_command():
        """Commande CLI : flask seed"""
        from app.seed import run_seed

        run_seed()
        print("Seed terminé.")

    @application.cli.command("create-super-admin")
    def create_super_admin_command():
        """Bootstrap ops : crée (ou réactive) le premier SUPER_ADMIN plateforme."""
        import uuid as uuid_mod

        import click

        from app.auth.jwt_handler import hash_password
        from app.extensions import get_db
        from app.models import Utilisateur
        from app.models.utilisateur import PLATFORM_ROLE_SUPER_ADMIN
        from app.utils.audit_logger import log_audit

        email = click.prompt("Email", type=str).strip().lower()
        nom = click.prompt("Nom", type=str, default="Super")
        prenom = click.prompt("Prénom", type=str, default="Admin")
        password = click.prompt("Mot de passe", hide_input=True, confirmation_prompt=True)

        db = get_db()
        existing = db.query(Utilisateur).filter(Utilisateur.email == email).first()
        if existing:
            if existing.role == PLATFORM_ROLE_SUPER_ADMIN and existing.school_id is None:
                existing.mot_de_passe_hash = hash_password(password)
                existing.actif = True
                existing.nom = nom
                existing.prenom = prenom
                db.commit()
                click.echo(f"SUPER_ADMIN existant mis à jour : {email}")
                return
            click.echo(
                f"Erreur : un utilisateur existe déjà avec cet email (rôle={existing.role}).",
                err=True,
            )
            raise SystemExit(1)

        user = Utilisateur(
            id=uuid_mod.uuid4(),
            nom=nom,
            prenom=prenom,
            email=email,
            role=PLATFORM_ROLE_SUPER_ADMIN,
            mot_de_passe_hash=hash_password(password),
            actif=True,
            doit_changer_mdp=True,
            school_id=None,
        )
        db.add(user)
        db.commit()
        log_audit(
            "SUPER_ADMIN_BOOTSTRAP",
            user.id,
            "utilisateur",
            user.id,
            details={"email": email},
            allow_null_school=True,
        )
        click.echo(f"SUPER_ADMIN créé : {email}")

    @application.cli.command("relancer-arrieres")
    def relancer_arrieres_command():
        """Relance les parents pour les arriérés de l'année active."""
        from app.extensions import get_db
        from app.models import AnneeScolaire
        from app.services.relance_arrieres import relancer_arrieres

        db = get_db()
        annees = db.query(AnneeScolaire).filter(AnneeScolaire.est_active.is_(True)).all()
        if not annees:
            print("Aucune année active.")
            return
        for annee in annees:
            result = relancer_arrieres(db, annee.id, auto_envoyer=True, school_id=annee.school_id)
            print(f"school={annee.school_id} {result}")

    @application.cli.command("digest-absences-hebdo")
    def digest_absences_hebdo_command():
        """Génère le digest hebdomadaire des absences (idempotent) pour chaque école active."""
        from app.extensions import get_db
        from app.models import School
        from app.services.digest_absences import digest_absences_hebdo

        db = get_db()
        schools = db.query(School).filter(School.is_active.is_(True)).all()
        if not schools:
            print("Aucune école active.")
            return
        for school in schools:
            result = digest_absences_hebdo(db, school.id, canal="email", auto_envoyer=True)
            print(f"school={school.code} {result}")

    @application.cli.command("traiter-notifications")
    def traiter_notifications_command():
        """Traite la file d'attente des notifications (toutes écoles)."""
        from app.extensions import get_db
        from app.models import School
        from app.services.envoi_notification import traiter_file_notifications

        db = get_db()
        schools = db.query(School).filter(School.is_active.is_(True)).all()
        total = 0
        if not schools:
            total = traiter_file_notifications()
        else:
            for school in schools:
                total += traiter_file_notifications(school_id=school.id)
        print(f"{total} notification(s) envoyée(s).")

    @application.route("/api/health")
    def health():
        payload = {"status": "ok"}
        storage_uri = application.config.get("RATELIMIT_STORAGE_URI", "")
        if storage_uri.startswith("redis://"):
            try:
                from urllib.parse import urlparse

                import redis

                parsed = urlparse(storage_uri)
                db_num = int((parsed.path or "/0").lstrip("/") or 0)
                client = redis.Redis(
                    host=parsed.hostname or "redis",
                    port=parsed.port or 6379,
                    db=db_num,
                    socket_connect_timeout=2,
                )
                client.ping()
                payload["redis"] = "ok"
            except Exception:
                return {"status": "degraded", "redis": "unavailable"}, 503
        return payload

    return application
