"""Génération de reçus de paiement PDF."""
import os
import uuid
from datetime import UTC, datetime

from flask import current_app, render_template

from app.extensions import get_db
from app.models import Eleve, Etablissement, Paiement
from app.services.pdf_render import html_to_pdf
from app.services.tenant import get_or_404_tenant, tenant_query


def generer_recu_pdf(paiement_id: uuid.UUID) -> str:
    """Génère le PDF du reçu de paiement."""
    db = get_db()
    paiement = get_or_404_tenant(Paiement, paiement_id)
    if paiement.annule:
        raise ValueError("Paiement annulé — reçu non valide")

    eleve = tenant_query(Eleve).filter(Eleve.id == paiement.id_eleve).first()
    etablissement = tenant_query(Etablissement).first()

    html = render_template(
        "recu.html",
        etablissement=etablissement,
        eleve=eleve,
        paiement=paiement,
        date_generation=datetime.now(UTC),
    )

    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "recus")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"recu_{paiement.numero_recu}.pdf"
    filepath = os.path.join(upload_dir, filename)
    html_to_pdf(html, filepath)
    return filepath
