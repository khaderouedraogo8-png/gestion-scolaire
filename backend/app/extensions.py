"""Initialisation des extensions Flask."""
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_smorest import Api
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker

from flask import g


class Base(DeclarativeBase):
    metadata = MetaData()


engine = None
SessionLocal = None
db_session = None
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per minute"])
api = Api()
cors = CORS()


def init_db(app):
    """Initialise le moteur SQLAlchemy et la session scoped."""
    global engine, SessionLocal, db_session
    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"], pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db_session = scoped_session(SessionLocal)

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()


def get_db():
    """Retourne la session courante (crée une nouvelle si nécessaire)."""
    if "db" not in g:
        g.db = db_session()
    return g.db
