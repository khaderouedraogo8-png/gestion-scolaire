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
    from app.routes.audit import blp as audit_blp
    from app.routes.auth import blp as auth_blp
    from app.routes.dashboard import blp as dashboard_blp
    from app.routes.documents import blp as documents_blp
    from app.routes.eleves import blp as eleves_blp
    from app.routes.emploi_temps import blp as emploi_temps_blp
    from app.routes.etablissement import blp as etablissement_blp
    from app.routes.finance import blp as finance_blp
    from app.routes.notes import blp as notes_blp
    from app.routes.notifications import blp as notifications_blp
    from app.routes.pedagogie import blp as pedagogie_blp
    from app.routes.users import blp as users_blp

    # Auth : routes plates (/api/login, /api/me, …)
    api.register_blueprint(auth_blp, url_prefix="/api")
    api.register_blueprint(users_blp, url_prefix="/api")
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

    @application.cli.command("seed")
    def seed_command():
        """Commande CLI : flask seed"""
        from app.seed import run_seed

        run_seed()
        print("Seed terminé.")

    @application.cli.command("relancer-arrieres")
    def relancer_arrieres_command():
        """Relance les parents pour les arriérés de l'année active."""
        from app.extensions import get_db
        from app.models import AnneeScolaire
        from app.services.relance_arrieres import relancer_arrieres

        db = get_db()
        annee = db.query(AnneeScolaire).filter(AnneeScolaire.est_active.is_(True)).first()
        if not annee:
            print("Aucune année active.")
            return
        result = relancer_arrieres(db, annee.id, auto_envoyer=True)
        print(result)

    @application.cli.command("traiter-notifications")
    def traiter_notifications_command():
        """Traite la file d'attente des notifications."""
        from app.services.envoi_notification import traiter_file_notifications

        sent = traiter_file_notifications()
        print(f"{sent} notification(s) envoyée(s).")

    @application.route("/api/health")
    def health():
        payload = {"status": "ok"}
        storage_uri = application.config.get("RATELIMIT_STORAGE_URI", "")
        if storage_uri.startswith("redis://"):
            try:
                import redis
                from urllib.parse import urlparse

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
