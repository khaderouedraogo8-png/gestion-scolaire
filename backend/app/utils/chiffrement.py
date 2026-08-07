"""Chiffrement des notes médicales via pgcrypto (pgp_sym_encrypt)."""
from flask import current_app
from sqlalchemy import text

from app.extensions import get_db


def chiffrer_notes_medicales(texte: str) -> bytes:
    """Chiffre les notes médicales avant stockage en base (pgcrypto)."""
    if not texte:
        return b""
    db = get_db()
    key = current_app.config["ENCRYPTION_KEY"]
    result = db.execute(
        text("SELECT pgp_sym_encrypt(:data, :key)"),
        {"data": texte, "key": key},
    ).scalar()
    return bytes(result) if result else b""


def dechiffrer_notes_medicales(donnees_chiffrees: bytes) -> str | None:
    """Déchiffre les notes médicales pour affichage autorisé uniquement."""
    if not donnees_chiffrees:
        return None
    db = get_db()
    key = current_app.config["ENCRYPTION_KEY"]
    try:
        result = db.execute(
            text("SELECT pgp_sym_decrypt(:data, :key)"),
            {"data": donnees_chiffrees, "key": key},
        ).scalar()
        if result is None:
            return None
        return result.decode("utf-8") if isinstance(result, (bytes, memoryview)) else str(result)
    except Exception:
        return None
