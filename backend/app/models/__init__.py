"""Export centralisé de tous les modèles SQLAlchemy."""
from app.models.absence_discipline import Absence, IncidentDisciplinaire
from app.models.audit import JournalAudit
from app.models.document import DocumentAdministratif
from app.models.eleve import Eleve, EleveParent, Inscription, ParentTuteur
from app.models.emploi_temps import (
    AffectationEnseignant,
    CreneauEmploiTemps,
    Enseignant,
    Salle,
)
from app.models.etablissement import (
    PROGRAM_CODE_GENERAL,
    PROGRAM_NAME_GENERAL,
    AcademicPeriod,
    AnneeScolaire,
    Classe,
    Etablissement,
    EvenementCalendrier,
    NiveauEtude,
    Program,
    Trimestre,
)
from app.models.finance import (
    EcheancePaiement,
    FraisScolaire,
    Paiement,
    seq_numero_recu,
)
from app.models.notification import Notification
from app.models.pedagogie import (
    Bulletin,
    CoefficientMatiere,
    Evaluation,
    Matiere,
    Note,
    ProgrammeDevoir,
    SeanceCours,
)
from app.models.school import School
from app.models.utilisateur import (
    PLATFORM_ROLE_SUPER_ADMIN,
    PLATFORM_ROLES,
    ROLES,
    SCHOOL_ROLES,
    RefreshToken,
    ReinitialisationMdp,
    Utilisateur,
)

__all__ = [
    "PLATFORM_ROLES",
    "PLATFORM_ROLE_SUPER_ADMIN",
    "PROGRAM_CODE_GENERAL",
    "PROGRAM_NAME_GENERAL",
    "ROLES",
    "SCHOOL_ROLES",
    "Absence",
    "AcademicPeriod",
    "AffectationEnseignant",
    "AnneeScolaire",
    "Bulletin",
    "Classe",
    "CoefficientMatiere",
    "CreneauEmploiTemps",
    "DocumentAdministratif",
    "EcheancePaiement",
    "Eleve",
    "EleveParent",
    "Enseignant",
    "Etablissement",
    "Evaluation",
    "EvenementCalendrier",
    "FraisScolaire",
    "IncidentDisciplinaire",
    "Inscription",
    "JournalAudit",
    "Matiere",
    "NiveauEtude",
    "Note",
    "Notification",
    "Paiement",
    "ParentTuteur",
    "Program",
    "ProgrammeDevoir",
    "RefreshToken",
    "ReinitialisationMdp",
    "Salle",
    "School",
    "SeanceCours",
    "Trimestre",
    "Utilisateur",
    "seq_numero_recu",
]
