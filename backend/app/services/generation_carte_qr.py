"""Génération de cartes scolaires avec QR code signé HMAC."""
import hashlib
import hmac
import json
import os
import uuid
from datetime import date, datetime, timezone

import qrcode
from flask import current_app, render_template

from app.extensions import get_db
from app.services.pdf_render import html_to_pdf
from app.models import DocumentAdministratif, Eleve, Etablissement, Inscription


def _sign_payload(payload: dict) -> str:
    """Signe le payload QR avec HMAC-SHA256."""
    secret = current_app.config["QR_HMAC_SECRET"].encode()
    message = json.dumps(payload, sort_keys=True).encode()
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
    return signature


def generer_qr_data(eleve: Eleve, annee_libelle: str) -> str:
    """Génère les données QR signées pour une carte scolaire."""
    payload = {
        "matricule": eleve.matricule,
        "nom": eleve.nom,
        "prenom": eleve.prenom,
        "annee": annee_libelle,
        "issued": date.today().isoformat(),
    }
    signature = _sign_payload(payload)
    payload["sig"] = signature
    return json.dumps(payload)


def verifier_qr_data(qr_json: str) -> tuple[bool, dict | None]:
    """Vérifie l'intégrité d'un QR code scanné."""
    try:
        data = json.loads(qr_json)
        signature = data.pop("sig", None)
        if not signature:
            return False, None
        expected = _sign_payload(data)
        if not hmac.compare_digest(signature, expected):
            return False, None
        return True, data
    except (json.JSONDecodeError, KeyError):
        return False, None


def generer_carte_scolaire(
    id_eleve: uuid.UUID,
    id_annee: uuid.UUID,
    id_utilisateur: uuid.UUID,
    date_expiration: date | None = None,
) -> DocumentAdministratif:
    """Génère une carte scolaire PDF avec QR code HMAC."""
    db = get_db()
    eleve = db.query(Eleve).filter(Eleve.id == id_eleve).first()
    if not eleve:
        raise ValueError("Élève introuvable")

    from app.models import AnneeScolaire

    annee = db.query(AnneeScolaire).filter(AnneeScolaire.id == id_annee).first()
    inscription = (
        db.query(Inscription)
        .filter(Inscription.id_eleve == id_eleve, Inscription.id_annee == id_annee)
        .first()
    )
    etablissement = db.query(Etablissement).first()

    qr_data = generer_qr_data(eleve, annee.libelle if annee else "")

    # Générer image QR
    qr = qrcode.make(qr_data)
    qr_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "qr")
    os.makedirs(qr_dir, exist_ok=True)
    qr_path = os.path.join(qr_dir, f"qr_{eleve.matricule}.png")
    qr.save(qr_path)

    from app.models import Classe

    classe = (
        db.query(Classe).filter(Classe.id == inscription.id_classe).first() if inscription else None
    )

    html = render_template(
        "carte_scolaire.html",
        etablissement=etablissement,
        eleve=eleve,
        classe=classe,
        annee=annee,
        qr_path=qr_path,
        date_emission=date.today(),
    )

    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "cartes")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"carte_{eleve.matricule}.pdf"
    filepath = os.path.join(upload_dir, filename)
    html_to_pdf(html, filepath)

    doc = DocumentAdministratif(
        id=uuid.uuid4(),
        id_eleve=id_eleve,
        type_document="carte_scolaire",
        qr_code_data=qr_data,
        date_emission=date.today(),
        date_expiration=date_expiration,
        pdf_url=filepath,
        genere_par=id_utilisateur,
    )
    db.add(doc)
    db.commit()
    return doc
