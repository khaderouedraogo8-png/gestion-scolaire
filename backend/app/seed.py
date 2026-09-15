"""Script de seed — données de démonstration complètes."""
import uuid
from datetime import date, time
from decimal import Decimal

from app.auth.jwt_handler import hash_password
from app.extensions import get_db
from app.models import (
    Absence,
    AffectationEnseignant,
    AnneeScolaire,
    Classe,
    CoefficientMatiere,
    CreneauEmploiTemps,
    EcheancePaiement,
    Eleve,
    EleveParent,
    Enseignant,
    Etablissement,
    Evaluation,
    FraisScolaire,
    Inscription,
    Matiere,
    NiveauEtude,
    Note,
    Paiement,
    ParentTuteur,
    Salle,
    School,
    Trimestre,
    Utilisateur,
)

DEFAULT_SCHOOL_CODE = "ECOLE-EXISTANTE"


def _ensure_default_school(db):
    """École tenant par défaut (équivalent migration Phase 1)."""
    school = db.query(School).filter(School.code == DEFAULT_SCHOOL_CODE).first()
    if school:
        return school
    etab = db.query(Etablissement).first()
    school = School(
        id=uuid.uuid4(),
        name=(etab.nom if etab else "École existante"),
        code=DEFAULT_SCHOOL_CODE,
        email=etab.email if etab else None,
        phone=etab.telephone if etab else None,
        address=etab.adresse if etab else None,
        city=etab.ville if etab else None,
        country=etab.pays if etab else None,
        logo=etab.logo_url if etab else None,
        is_active=True,
    )
    db.add(school)
    db.flush()
    return school


def run_seed():
    db = get_db()
    school = _ensure_default_school(db)
    school_id = school.id

    # Admin par défaut
    if not db.query(Utilisateur).filter(Utilisateur.email == "admin@ecole.local").first():
        admin = Utilisateur(
            id=uuid.uuid4(),
            nom="Administrateur",
            prenom="Système",
            email="admin@ecole.local",
            mot_de_passe_hash=hash_password("Admin123!"),
            role="administrateur",
            actif=True,
            doit_changer_mdp=False,
            school_id=school_id,
        )
        db.add(admin)

    # Établissement
    if not db.query(Etablissement).filter(Etablissement.school_id == school_id).first():
        etab = Etablissement(
            id=uuid.uuid4(),
            school_id=school_id,
            nom="École Exemplaire",
            sigle="EE",
            adresse="123 Avenue de l'Éducation",
            telephone="+226 70 00 00 00",
            email="contact@ecole.local",
            type_etablissement="Complexe",
            pays="Burkina Faso",
            ville="Ouagadougou",
            format_matricule="{ANNEE}M-{SEQ}",
            devise="XOF",
        )
        db.add(etab)

    db.flush()

    # Année scolaire active
    annee = db.query(AnneeScolaire).filter(
        AnneeScolaire.libelle == "2025-2026",
        AnneeScolaire.school_id == school_id,
    ).first()
    if not annee:
        annee = AnneeScolaire(
            id=uuid.uuid4(),
            school_id=school_id,
            libelle="2025-2026",
            date_debut=date(2025, 9, 1),
            date_fin=date(2026, 6, 30),
            est_active=True,
        )
        db.add(annee)
        db.flush()

        for num, (deb, fin) in enumerate(
            [(date(2025, 9, 1), date(2025, 12, 20)),
             (date(2026, 1, 5), date(2026, 3, 31)),
             (date(2026, 4, 1), date(2026, 6, 30))],
            start=1,
        ):
            trim = Trimestre(
                id=uuid.uuid4(),
                id_annee=annee.id,
                numero=num,
                date_debut=deb,
                date_fin=fin,
            )
            db.add(trim)

    # Niveaux
    niveaux_data = [
        ("6ème", 1, "premier"),
        ("5ème", 2, "premier"),
        ("4ème", 3, "premier"),
        ("3ème", 4, "premier"),
        ("Seconde", 5, "second"),
        ("Première", 6, "second"),
        ("Terminale", 7, "second"),
    ]
    niveaux = {}
    for libelle, ordre, cycle in niveaux_data:
        n = db.query(NiveauEtude).filter(
            NiveauEtude.libelle == libelle,
            NiveauEtude.school_id == school_id,
        ).first()
        if not n:
            n = NiveauEtude(
                id=uuid.uuid4(),
                school_id=school_id,
                libelle=libelle,
                ordre=ordre,
                cycle=cycle,
            )
            db.add(n)
            db.flush()
        else:
            n.cycle = cycle
        niveaux[libelle] = n

    # Classes pour 6ème et Terminale
    for libelle_niveau, suffixes in [("6ème", ["A", "B"]), ("Terminale", ["A", "C"])]:
        niveau = niveaux[libelle_niveau]
        for s in suffixes:
            cls_libelle = f"{libelle_niveau} {s}"
            if not db.query(Classe).filter(
                Classe.libelle == cls_libelle,
                Classe.id_annee == annee.id,
                Classe.school_id == school_id,
            ).first():
                classe = Classe(
                    id=uuid.uuid4(),
                    school_id=school_id,
                    id_niveau=niveau.id,
                    id_annee=annee.id,
                    libelle=cls_libelle,
                    capacite_max=45,
                )
                db.add(classe)

    # Matières de base
    matieres_data = [
        ("Mathématiques", "MATH", 4),
        ("Français", "FR", 4),
        ("Anglais", "ANG", 2),
        ("Sciences Physiques", "PC", 3),
        ("SVT", "SVT", 2),
        ("Histoire-Géographie", "HG", 2),
    ]
    matieres = {}
    for libelle, code, coef in matieres_data:
        m = db.query(Matiere).filter(
            Matiere.code == code,
            Matiere.school_id == school_id,
        ).first()
        if not m:
            m = Matiere(id=uuid.uuid4(), school_id=school_id, libelle=libelle, code=code)
            db.add(m)
            db.flush()
        matieres[code] = m
        # Coefficients pour le niveau 6ème
        niveau_6 = niveaux.get("6ème")
        if niveau_6 and not db.query(CoefficientMatiere).filter(
            CoefficientMatiere.id_matiere == m.id,
            CoefficientMatiere.id_niveau == niveau_6.id,
        ).first():
            db.add(
                CoefficientMatiere(
                    id=uuid.uuid4(),
                    id_matiere=m.id,
                    id_niveau=niveau_6.id,
                    coefficient=coef,
                )
            )

    # Enseignant par défaut
    enseignant = db.query(Enseignant).filter(Enseignant.school_id == school_id).first()
    if not enseignant:
        enseignant = Enseignant(
            id=uuid.uuid4(),
            school_id=school_id,
            nom="Koné",
            prenom="Amadou",
            email="enseignant@ecole.local",
            specialite="Mathématiques",
            type_contrat="permanent",
        )
        db.add(enseignant)
        db.flush()

    # Comptable démo
    if not db.query(Utilisateur).filter(Utilisateur.email == "compta@ecole.local").first():
        db.add(
            Utilisateur(
                id=uuid.uuid4(),
                nom="Traoré",
                prenom="Aïcha",
                email="compta@ecole.local",
                mot_de_passe_hash=hash_password("Compta123!"),
                role="agent_comptable",
                actif=True,
                doit_changer_mdp=False,
                school_id=school_id,
            )
        )

    classe_6a = db.query(Classe).filter(
        Classe.libelle == "6ème A",
        Classe.id_annee == annee.id,
        Classe.school_id == school_id,
    ).first()
    trimestre_1 = db.query(Trimestre).filter(
        Trimestre.id_annee == annee.id, Trimestre.numero == 1
    ).first()

    # Élèves de démonstration
    eleves_demo = [
        ("Diallo", "Amadou", "M"),
        ("Sow", "Fatou", "F"),
        ("Ouédraogo", "Ibrahim", "M"),
        ("Kaboré", "Aminata", "F"),
        ("Zongo", "Moussa", "M"),
    ]
    eleves_crees = []
    if classe_6a and not db.query(Eleve).filter(
        Eleve.matricule == "2025M-001",
        Eleve.school_id == school_id,
    ).first():
        for i, (nom, prenom, sexe) in enumerate(eleves_demo, start=1):
            eleve = Eleve(
                id=uuid.uuid4(),
                school_id=school_id,
                matricule=f"2025M-{i:03d}",
                nom=nom,
                prenom=prenom,
                sexe=sexe,
                date_naissance=date(2013, 3, 15),
            )
            db.add(eleve)
            db.flush()
            db.add(
                Inscription(
                    id=uuid.uuid4(),
                    school_id=school_id,
                    id_eleve=eleve.id,
                    id_classe=classe_6a.id,
                    id_annee=annee.id,
                    statut="inscrit",
                )
            )
            parent = ParentTuteur(
                id=uuid.uuid4(),
                school_id=school_id,
                nom=nom,
                prenom=f"Parent {prenom}",
                lien_parente="père" if sexe == "M" else "mère",
                telephone=f"+226700000{i:02d}",
                email=f"parent.{prenom.lower()}@demo.local",
            )
            db.add(parent)
            db.flush()
            db.add(EleveParent(id_eleve=eleve.id, id_parent=parent.id, tuteur_legal=True))
            eleves_crees.append(eleve)

    # Salles et emploi du temps
    salle_a = db.query(Salle).filter(
        Salle.libelle == "Salle 101",
        Salle.school_id == school_id,
    ).first()
    if not salle_a:
        salle_a = Salle(id=uuid.uuid4(), school_id=school_id, libelle="Salle 101", capacite=45)
        db.add(salle_a)
        db.add(Salle(id=uuid.uuid4(), school_id=school_id, libelle="Salle 102", capacite=40))
        db.flush()

    if classe_6a and enseignant and matieres.get("MATH"):
        aff = db.query(AffectationEnseignant).filter(
            AffectationEnseignant.id_classe == classe_6a.id,
            AffectationEnseignant.id_matiere == matieres["MATH"].id,
        ).first()
        if not aff:
            aff = AffectationEnseignant(
                id=uuid.uuid4(),
                school_id=school_id,
                id_enseignant=enseignant.id,
                id_classe=classe_6a.id,
                id_matiere=matieres["MATH"].id,
                id_annee=annee.id,
                volume_horaire_hebdo=4,
            )
            db.add(aff)
            db.flush()
        if aff and not db.query(CreneauEmploiTemps).filter(
            CreneauEmploiTemps.id_affectation == aff.id
        ).first():
            conflit = db.query(CreneauEmploiTemps).filter(
                CreneauEmploiTemps.id_salle == salle_a.id,
                CreneauEmploiTemps.jour_semaine == 1,
                CreneauEmploiTemps.heure_debut == time(8, 0),
            ).first()
            if not conflit:
                db.add(
                    CreneauEmploiTemps(
                        id=uuid.uuid4(),
                        id_affectation=aff.id,
                        id_salle=salle_a.id,
                        jour_semaine=1,
                        heure_debut=time(8, 0),
                        heure_fin=time(10, 0),
                    )
                )

    # Évaluation et notes démo
    if classe_6a and trimestre_1 and enseignant and matieres.get("MATH"):
        eval_demo = db.query(Evaluation).filter(
            Evaluation.libelle == "Devoir 1 — Math",
            Evaluation.school_id == school_id,
        ).first()
        if not eval_demo:
            eval_demo = Evaluation(
                id=uuid.uuid4(),
                school_id=school_id,
                id_classe=classe_6a.id,
                id_matiere=matieres["MATH"].id,
                id_trimestre=trimestre_1.id,
                id_enseignant=enseignant.id,
                type_evaluation="devoir",
                coefficient=2,
                date_evaluation=date(2025, 10, 15),
                libelle="Devoir 1 — Math",
            )
            db.add(eval_demo)
            db.flush()
            notes_vals = [14, 12, 16, 11, 15]
            eleves_notes = eleves_crees or db.query(Eleve).filter(
                Eleve.school_id == school_id
            ).limit(5).all()
            for eleve, val in zip(eleves_notes, notes_vals):
                if not db.query(Note).filter(
                    Note.id_evaluation == eval_demo.id, Note.id_eleve == eleve.id
                ).first():
                    db.add(
                        Note(
                            id=uuid.uuid4(),
                            school_id=school_id,
                            id_evaluation=eval_demo.id,
                            id_eleve=eleve.id,
                            valeur_note=Decimal(str(val)),
                            absent=False,
                        )
                    )

    # Paiement démo
    first_eleve = db.query(Eleve).filter(
        Eleve.matricule == "2025M-001",
        Eleve.school_id == school_id,
    ).first()
    admin = db.query(Utilisateur).filter(Utilisateur.email == "admin@ecole.local").first()
    if first_eleve and annee and not db.query(Paiement).filter(
        Paiement.id_eleve == first_eleve.id
    ).first():
        db.add(
            Paiement(
                id=uuid.uuid4(),
                school_id=school_id,
                id_eleve=first_eleve.id,
                id_annee=annee.id,
                motif="Scolarité",
                montant_verse=Decimal(50000),
                mode_paiement="Espèces",
                numero_recu="REC-SEED-001",
                encaisse_par=admin.id if admin else None,
            )
        )

    # Absence démo
    if first_eleve and not db.query(Absence).filter(Absence.id_eleve == first_eleve.id).first():
        db.add(
            Absence(
                id=uuid.uuid4(),
                school_id=school_id,
                id_eleve=first_eleve.id,
                date_absence=date(2025, 10, 20),
                type_absence="absence",
                justifiee=False,
                signale_par=admin.id if admin else None,
            )
        )

    # Frais scolaires et échéances (6ème — année active)
    niveau_6 = niveaux.get("6ème")
    if niveau_6 and annee:
        frais = db.query(FraisScolaire).filter(
            FraisScolaire.id_niveau == niveau_6.id,
            FraisScolaire.id_annee == annee.id,
            FraisScolaire.motif == "Scolarité",
            FraisScolaire.school_id == school_id,
        ).first()
        if not frais:
            frais = FraisScolaire(
                id=uuid.uuid4(),
                school_id=school_id,
                id_niveau=niveau_6.id,
                id_annee=annee.id,
                motif="Scolarité",
                montant_total=150000,
            )
            db.add(frais)
            db.flush()
            echeances_data = [
                ("1ère tranche — inscription", 50000, date(2025, 9, 15)),
                ("2ème tranche — T1", 50000, date(2025, 12, 15)),
                ("3ème tranche — T2", 50000, date(2026, 3, 15)),
            ]
            for libelle, montant, echeance in echeances_data:
                db.add(
                    EcheancePaiement(
                        id=uuid.uuid4(),
                        id_frais=frais.id,
                        libelle=libelle,
                        montant=montant,
                        date_echeance=echeance,
                    )
                )

    admin = db.query(Utilisateur).filter(Utilisateur.email == "admin@ecole.local").first()
    if admin:
        admin.doit_changer_mdp = False

    # Compte parent démo (lié au 1er parent créé)
    if not db.query(Utilisateur).filter(Utilisateur.email == "parent@demo.local").first():
        parent_user = Utilisateur(
            id=uuid.uuid4(),
            nom="Diallo",
            prenom="Parent Amadou",
            email="parent@demo.local",
            mot_de_passe_hash=hash_password("Parent123!"),
            role="parent",
            actif=True,
            doit_changer_mdp=False,
            school_id=school_id,
        )
        db.add(parent_user)
        db.flush()
        first_parent = db.query(ParentTuteur).filter(
            ParentTuteur.email == "parent.amadou@demo.local",
            ParentTuteur.school_id == school_id,
        ).first()
        if first_parent:
            first_parent.id_utilisateur = parent_user.id

    db.commit()

    from app.seed_extended import run_extended_seed

    run_extended_seed(db, school)
