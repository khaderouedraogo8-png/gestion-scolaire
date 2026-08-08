"""Données de démonstration étendues — tous rôles, classes remplies, notifications."""
import uuid
from datetime import date, time
from decimal import Decimal

from app.auth.jwt_handler import hash_password
from app.models import (
    AffectationEnseignant,
    AnneeScolaire,
    Classe,
    CreneauEmploiTemps,
    Eleve,
    EleveParent,
    Enseignant,
    Evaluation,
    Inscription,
    Matiere,
    Note,
    Notification,
    ParentTuteur,
    Salle,
    Trimestre,
    Utilisateur,
)


def _ensure_user(db, email, nom, prenom, role, password):
    user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
    if user:
        return user
    user = Utilisateur(
        id=uuid.uuid4(),
        nom=nom,
        prenom=prenom,
        email=email,
        mot_de_passe_hash=hash_password(password),
        role=role,
        actif=True,
        doit_changer_mdp=False,
    )
    db.add(user)
    db.flush()
    return user


def run_extended_seed(db):
    """Complète le seed de base (idempotent)."""
    annee = db.query(AnneeScolaire).filter(AnneeScolaire.est_active.is_(True)).first()
    if not annee:
        return

    trimestre_1 = db.query(Trimestre).filter(
        Trimestre.id_annee == annee.id, Trimestre.numero == 1
    ).first()

    # --- Comptes tous rôles ---
    _ensure_user(db, "directeur@ecole.local", "Ouédraogo", "Jean", "directeur", "Directeur123!")
    _ensure_user(db, "secretariat@ecole.local", "Sawadogo", "Marie", "secretariat", "Secret123!")
    enseignant_user = _ensure_user(
        db, "enseignant@ecole.local", "Koné", "Amadou", "enseignant", "Enseignant123!"
    )

    enseignant = db.query(Enseignant).filter(Enseignant.email == "enseignant@ecole.local").first()
    if not enseignant:
        enseignant = db.query(Enseignant).first()
    if enseignant:
        enseignant.email = "enseignant@ecole.local"
        enseignant.id_utilisateur = enseignant_user.id

    enseignant_fr = db.query(Enseignant).filter(Enseignant.email == "francais@ecole.local").first()
    if not enseignant_fr:
        enseignant_fr = Enseignant(
            id=uuid.uuid4(),
            nom="Diabaté",
            prenom="Awa",
            email="francais@ecole.local",
            specialite="Français",
            type_contrat="permanent",
        )
        db.add(enseignant_fr)
        db.flush()

    # --- Élèves supplémentaires (6ème B + Terminale A) ---
    classes_cibles = [
        ("6ème B", "2025M-1"),
        ("Terminale A", "2025M-T"),
    ]
    prenoms_extra = [
        ("Coulibaly", "Rasmata", "F"),
        ("Bamba", "Seydou", "M"),
        ("Nikiema", "Salimata", "F"),
        ("Compaoré", "Issa", "M"),
        ("Tapsoba", "Kadiatou", "F"),
        ("Sanou", "Boubacar", "M"),
        ("Yameogo", "Clarisse", "F"),
        ("Ilboudo", "Théo", "M"),
    ]

    seq = 10
    for cls_libelle, prefix in classes_cibles:
        classe = db.query(Classe).filter(
            Classe.libelle == cls_libelle, Classe.id_annee == annee.id
        ).first()
        if not classe:
            continue
        for nom, prenom, sexe in prenoms_extra[:4] if "6ème" in cls_libelle else prenoms_extra[4:8]:
            matricule = f"{prefix}{seq:02d}"
            seq += 1
            if db.query(Eleve).filter(Eleve.matricule == matricule).first():
                continue
            eleve = Eleve(
                id=uuid.uuid4(),
                matricule=matricule,
                nom=nom,
                prenom=prenom,
                sexe=sexe,
                date_naissance=date(2008 if "Terminale" in cls_libelle else 2013, 6, 10),
            )
            db.add(eleve)
            db.flush()
            db.add(
                Inscription(
                    id=uuid.uuid4(),
                    id_eleve=eleve.id,
                    id_classe=classe.id,
                    id_annee=annee.id,
                    statut="inscrit",
                )
            )
            parent = ParentTuteur(
                id=uuid.uuid4(),
                nom=nom,
                prenom=f"Tuteur {prenom}",
                lien_parente="tuteur",
                telephone=f"+2267011{seq:04d}",
                email=f"tuteur.{prenom.lower()}.{nom.lower()}@demo.local",
            )
            db.add(parent)
            db.flush()
            db.add(EleveParent(id_eleve=eleve.id, id_parent=parent.id, tuteur_legal=True))

    # --- Affectations + créneaux supplémentaires ---
    matiere_math = db.query(Matiere).filter(Matiere.code == "MATH").first()
    matiere_fr = db.query(Matiere).filter(Matiere.code == "FR").first()
    classe_6b = db.query(Classe).filter(Classe.libelle == "6ème B", Classe.id_annee == annee.id).first()
    salle = db.query(Salle).filter(Salle.libelle == "Salle 102").first()

    if classe_6b and enseignant and matiere_math and salle:
        aff = db.query(AffectationEnseignant).filter(
            AffectationEnseignant.id_classe == classe_6b.id,
            AffectationEnseignant.id_matiere == matiere_math.id,
        ).first()
        if not aff:
            aff = AffectationEnseignant(
                id=uuid.uuid4(),
                id_enseignant=enseignant.id,
                id_classe=classe_6b.id,
                id_matiere=matiere_math.id,
                id_annee=annee.id,
                volume_horaire_hebdo=4,
            )
            db.add(aff)
            db.flush()
            if not db.query(CreneauEmploiTemps).filter(CreneauEmploiTemps.id_affectation == aff.id).first():
                db.add(
                    CreneauEmploiTemps(
                        id=uuid.uuid4(),
                        id_affectation=aff.id,
                        id_salle=salle.id,
                        jour_semaine=3,
                        heure_debut=time(10, 0),
                        heure_fin=time(12, 0),
                    )
                )

    classe_6a = db.query(Classe).filter(Classe.libelle == "6ème A", Classe.id_annee == annee.id).first()
    if classe_6a and enseignant_fr and matiere_fr and salle:
        aff_fr = db.query(AffectationEnseignant).filter(
            AffectationEnseignant.id_classe == classe_6a.id,
            AffectationEnseignant.id_matiere == matiere_fr.id,
        ).first()
        if not aff_fr:
            aff_fr = AffectationEnseignant(
                id=uuid.uuid4(),
                id_enseignant=enseignant_fr.id,
                id_classe=classe_6a.id,
                id_matiere=matiere_fr.id,
                id_annee=annee.id,
                volume_horaire_hebdo=4,
            )
            db.add(aff_fr)
            db.flush()

        if trimestre_1 and not db.query(Evaluation).filter(Evaluation.libelle == "Devoir 1 — Français").first():
            eval_fr = Evaluation(
                id=uuid.uuid4(),
                id_classe=classe_6a.id,
                id_matiere=matiere_fr.id,
                id_trimestre=trimestre_1.id,
                id_enseignant=enseignant_fr.id,
                type_evaluation="devoir",
                coefficient=2,
                date_evaluation=date(2025, 10, 18),
                libelle="Devoir 1 — Français",
            )
            db.add(eval_fr)
            db.flush()
            inscrits = (
                db.query(Eleve)
                .join(Inscription, Inscription.id_eleve == Eleve.id)
                .filter(Inscription.id_classe == classe_6a.id, Inscription.id_annee == annee.id)
                .all()
            )
            for i, eleve in enumerate(inscrits):
                if not db.query(Note).filter(Note.id_evaluation == eval_fr.id, Note.id_eleve == eleve.id).first():
                    db.add(
                        Note(
                            id=uuid.uuid4(),
                            id_evaluation=eval_fr.id,
                            id_eleve=eleve.id,
                            valeur_note=Decimal(str(10 + (i % 8))),
                            absent=False,
                        )
                    )

    # --- Notification email de démo (file d'attente) ---
    first_eleve = db.query(Eleve).filter(Eleve.matricule == "2025M-001").first()
    if first_eleve and not db.query(Notification).filter(
        Notification.type_notification == "demo_bienvenue"
    ).first():
        link = db.query(EleveParent).filter(EleveParent.id_eleve == first_eleve.id).first()
        db.add(
            Notification(
                id=uuid.uuid4(),
                id_eleve=first_eleve.id,
                id_parent=link.id_parent if link else None,
                canal="email",
                type_notification="demo_bienvenue",
                contenu=(
                    "Bienvenue sur la plateforme Gestion Scolaire. "
                    "Consultez les notes et paiements de votre enfant en ligne."
                ),
                statut="en_attente",
            )
        )

    db.commit()
