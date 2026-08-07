"""Génération de documents administratifs (attestation, certificat)."""
import os
import uuid
from datetime import date

from flask import current_app, render_template

from app.extensions import get_db
from app.services.pdf_render import html_to_pdf
from app.models import AnneeScolaire, Classe, DocumentAdministratif, Eleve, Etablissement, Inscription, NiveauEtude


def _generer_pdf_document(
    id_eleve: uuid.UUID,
    id_annee: uuid.UUID,
    id_utilisateur: uuid.UUID,
    type_document: str,
    template_name: str,
    titre: str,
) -> DocumentAdministratif:
    db = get_db()
    eleve = db.query(Eleve).filter(Eleve.id == id_eleve).first()
    if not eleve:
        raise ValueError("Élève introuvable")

    annee = db.query(AnneeScolaire).filter(AnneeScolaire.id == id_annee).first()
    if not annee:
        raise ValueError("Année scolaire introuvable")

    inscription = (
        db.query(Inscription)
        .filter(Inscription.id_eleve == id_eleve, Inscription.id_annee == id_annee)
        .first()
    )
    if not inscription:
        raise ValueError("Élève non inscrit pour cette année")

    classe = db.query(Classe).filter(Classe.id == inscription.id_classe).first()
    etablissement = db.query(Etablissement).first()

    html = render_template(
        template_name,
        etablissement=etablissement,
        eleve=eleve,
        classe=classe,
        annee=annee,
        titre=titre,
        date_emission=date.today(),
    )

    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "documents")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{type_document}_{eleve.matricule}.pdf"
    filepath = os.path.join(upload_dir, filename)
    html_to_pdf(html, filepath)

    doc = DocumentAdministratif(
        id=uuid.uuid4(),
        id_eleve=id_eleve,
        type_document=type_document,
        date_emission=date.today(),
        pdf_url=filepath,
        genere_par=id_utilisateur,
    )
    db.add(doc)
    db.commit()
    return doc


def generer_attestation_scolarite(
    id_eleve: uuid.UUID, id_annee: uuid.UUID, id_utilisateur: uuid.UUID
) -> DocumentAdministratif:
    return _generer_pdf_document(
        id_eleve,
        id_annee,
        id_utilisateur,
        "attestation_scolarite",
        "attestation.html",
        "Attestation de scolarité",
    )


def generer_certificat_scolarite(
    id_eleve: uuid.UUID, id_annee: uuid.UUID, id_utilisateur: uuid.UUID
) -> DocumentAdministratif:
    return _generer_pdf_document(
        id_eleve,
        id_annee,
        id_utilisateur,
        "certificat",
        "attestation.html",
        "Certificat de scolarité",
    )


def generer_diplome(
    id_eleve: uuid.UUID,
    id_annee: uuid.UUID,
    id_utilisateur: uuid.UUID,
    mention: str | None = None,
) -> DocumentAdministratif:
    """Génère un diplôme de fin d'études."""
    db = get_db()
    eleve = db.query(Eleve).filter(Eleve.id == id_eleve).first()
    if not eleve:
        raise ValueError("Élève introuvable")

    annee = db.query(AnneeScolaire).filter(AnneeScolaire.id == id_annee).first()
    if not annee:
        raise ValueError("Année scolaire introuvable")

    inscription = (
        db.query(Inscription)
        .filter(Inscription.id_eleve == id_eleve, Inscription.id_annee == id_annee)
        .first()
    )
    if not inscription:
        raise ValueError("Élève non inscrit pour cette année")

    classe = db.query(Classe).filter(Classe.id == inscription.id_classe).first()
    niveau = (
        db.query(NiveauEtude).filter(NiveauEtude.id == classe.id_niveau).first()
        if classe
        else None
    )
    etablissement = db.query(Etablissement).first()

    from flask import render_template

    html = render_template(
        "diplome.html",
        etablissement=etablissement,
        eleve=eleve,
        classe=classe,
        niveau=niveau,
        annee=annee,
        mention=mention,
        date_emission=date.today(),
    )

    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "documents")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"diplome_{eleve.matricule}.pdf"
    filepath = os.path.join(upload_dir, filename)
    html_to_pdf(html, filepath)

    doc = DocumentAdministratif(
        id=uuid.uuid4(),
        id_eleve=id_eleve,
        type_document="diplome",
        date_emission=date.today(),
        pdf_url=filepath,
        genere_par=id_utilisateur,
    )
    db.add(doc)
    db.commit()
    return doc
