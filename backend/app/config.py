"""Configuration par environnement (dev / test / prod)."""
import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://gestion:gestion_dev@localhost:5432/gestion_scolaire",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_TOKEN_LOCATION = ("headers",)
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"
    REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY", "dev-refresh-secret-change-in-production")

    # Chiffrement notes médicales
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "dev-encryption-key-32chars-min!!")
    QR_HMAC_SECRET = os.getenv("QR_HMAC_SECRET", "dev-qr-hmac-secret")

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

    # Rate limiting (Redis recommandé en prod multi-workers : redis://redis:6379/0)
    RATELIMIT_ENABLED = os.getenv("RATELIMIT_ENABLED", "true").lower() == "true"
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

    # Uploads
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))

    # Flask-Smorest / OpenAPI
    API_TITLE = "Gestion Scolaire API"
    API_VERSION = "v1"
    OPENAPI_VERSION = "3.0.3"
    OPENAPI_URL_PREFIX = "/api"
    OPENAPI_SWAGGER_UI_PATH = "/docs"
    OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    # Sécurité
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30

    # SMTP / SMS (stubs configurables)
    SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "noreply@ecole.local")
    SMS_API_URL = os.getenv("SMS_API_URL", "")
    SMS_API_KEY = os.getenv("SMS_API_KEY", "")
    SMS_SENDER = os.getenv("SMS_SENDER", "ECOLE")


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    RATELIMIT_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://gestion:gestion_test@localhost:5432/gestion_scolaire_test",
    )
    JWT_SECRET_KEY = "test-jwt-secret"
    REFRESH_SECRET_KEY = "test-refresh-secret"
    ENCRYPTION_KEY = "test-encryption-key-32chars-min!!"


class ProductionConfig(Config):
    DEBUG = False
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "redis://redis:6379/0")
    # Désactive la doc Swagger en production
    OPENAPI_URL_PREFIX = None

    _INSECURE_DEFAULTS = {
        "JWT_SECRET_KEY": "dev-jwt-secret-change-in-production",
        "REFRESH_SECRET_KEY": "dev-refresh-secret-change-in-production",
        "ENCRYPTION_KEY": "dev-encryption-key-32chars-min!!",
        "QR_HMAC_SECRET": "dev-qr-hmac-secret",
    }

    @classmethod
    def validate_secrets(cls) -> None:
        """Bloque le démarrage si des secrets prod sont absents ou encore aux valeurs dev."""
        invalid = []
        for key, default in cls._INSECURE_DEFAULTS.items():
            env_value = os.getenv(key)
            if env_value is None or not str(env_value).strip():
                invalid.append(f"{key} (absente ou vide)")
            elif env_value == default:
                invalid.append(f"{key} (valeur de dev par défaut)")
        if invalid:
            raise RuntimeError(
                "Configuration production invalide — définissez des secrets uniques pour : "
                + ", ".join(invalid)
            )


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
