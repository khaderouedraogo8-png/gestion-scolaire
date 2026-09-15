"""Tests normalisation DATABASE_URL (Railway / Heroku)."""
from app.config import normalize_database_url


def test_normalize_postgres_scheme():
    assert (
        normalize_database_url("postgres://u:p@host:5432/db")
        == "postgresql+psycopg2://u:p@host:5432/db"
    )


def test_normalize_postgresql_scheme():
    assert (
        normalize_database_url("postgresql://u:p@host:5432/db")
        == "postgresql+psycopg2://u:p@host:5432/db"
    )


def test_normalize_already_psycopg2():
    url = "postgresql+psycopg2://u:p@host:5432/db"
    assert normalize_database_url(url) == url


def test_normalize_empty():
    assert normalize_database_url("") == ""
