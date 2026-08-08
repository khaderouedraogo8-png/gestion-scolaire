"""Export centralisé des schémas Marshmallow."""
from app.schemas.absences import AbsenceSchema, IncidentDisciplinaireSchema
from app.schemas.auth import (
    ChangePasswordSchema,
    LoginSchema,
    TokenResponseSchema,
    UserSchema,
)
from app.schemas.documents import (
    DocumentAdministratifSchema,
    NotificationCreateSchema,
    NotificationSchema,
)
from app.schemas.eleve import (
    EleveCreateSchema,
    EleveDetailSchema,
    EleveSchema,
    InscriptionSchema,
    ParentTuteurSchema,
)
from app.schemas.emploi_temps import (
    AffectationEnseignantSchema,
    CreneauEmploiTempsSchema,
    EnseignantSchema,
    SalleSchema,
)
from app.schemas.etablissement import (
    AnneeScolaireSchema,
    ClasseSchema,
    EtablissementSchema,
    NiveauEtudeSchema,
    TrimestreSchema,
)
from app.schemas.finance import (
    AnnulationPaiementSchema,
    EcheancePaiementSchema,
    FraisScolaireSchema,
    PaiementCreateSchema,
    PaiementSchema,
)
from app.schemas.notes import (
    BulletinSchema,
    CoefficientMatiereSchema,
    EvaluationSchema,
    MatiereSchema,
    NoteBatchSchema,
    NoteSchema,
)

__all__ = [
    "AbsenceSchema",
    "AffectationEnseignantSchema",
    "AnneeScolaireSchema",
    "AnnulationPaiementSchema",
    "BulletinSchema",
    "ChangePasswordSchema",
    "ClasseSchema",
    "CoefficientMatiereSchema",
    "CreneauEmploiTempsSchema",
    "DocumentAdministratifSchema",
    "EcheancePaiementSchema",
    "EleveCreateSchema",
    "EleveDetailSchema",
    "EleveSchema",
    "EnseignantSchema",
    "EtablissementSchema",
    "EvaluationSchema",
    "FraisScolaireSchema",
    "IncidentDisciplinaireSchema",
    "InscriptionSchema",
    "LoginSchema",
    "MatiereSchema",
    "NiveauEtudeSchema",
    "NoteBatchSchema",
    "NoteSchema",
    "NotificationCreateSchema",
    "NotificationSchema",
    "PaiementCreateSchema",
    "PaiementSchema",
    "ParentTuteurSchema",
    "SalleSchema",
    "TokenResponseSchema",
    "TrimestreSchema",
    "UserSchema",
]
