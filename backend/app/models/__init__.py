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
    AnneeScolaire,
    Classe,
    Etablissement,
    NiveauEtude,
    Trimestre,
)
from app.models.finance import EcheancePaiement, FraisScolaire, Paiement, seq_numero_recu
from app.models.notification import Notification
from app.models.pedagogie import (
    Bulletin,
    CoefficientMatiere,
    Evaluation,
    Matiere,
    Note,
)
from app.models.utilisateur import (
    ROLES,
    ReinitialisationMdp,
    RefreshToken,
    Utilisateur,
)

__all__ = [
    "ROLES",
    "Absence",
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
    "ReinitialisationMdp",
    "RefreshToken",
    "Salle",
    "Trimestre",
    "Utilisateur",
    "seq_numero_recu",
]
