import { Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import { useAuthStore } from './store/authStore';

import Login from './pages/auth/Login';
import OtpLogin from './pages/auth/OtpLogin';
import ChangePassword from './pages/auth/ChangePassword';
import ForgotPassword from './pages/auth/ForgotPassword';
import PublicHome from './pages/landing/PublicHome';
import Dashboard from './pages/dashboard/Dashboard';

import ClassesHome from './pages/classes/ClassesHome';
import CycleClasses from './pages/classes/CycleClasses';
import ClassDetail from './pages/classes/ClassDetail';

import EleveList from './pages/eleves/EleveList';
import EleveDetail from './pages/eleves/EleveDetail';
import EleveForm from './pages/eleves/EleveForm';
import EleveImport from './pages/eleves/EleveImport';
import InscriptionForm from './pages/eleves/InscriptionForm';
import Fratries from './pages/eleves/Fratries';

import AdmissionList from './pages/admission/AdmissionList';
import AdmissionForm from './pages/admission/AdmissionForm';

import EvaluationList from './pages/notes/EvaluationList';
import SaisieNotes from './pages/notes/SaisieNotes';
import BulletinList from './pages/notes/BulletinList';
import ResultatsAcademiques from './pages/notes/ResultatsAcademiques';
import ConseilClasse from './pages/notes/ConseilClasse';

import FraisList from './pages/finance/FraisList';
import Encaissement from './pages/finance/Encaissement';
import Arrieres from './pages/finance/Arrieres';
import Recus from './pages/finance/Recus';
import ComptabiliteSyscohada from './pages/finance/ComptabiliteSyscohada';
import ComptabiliteEcritures from './pages/finance/ComptabiliteEcritures';
import Paie from './pages/finance/Paie';
import Recouvrement from './pages/finance/Recouvrement';
import MobileMoney from './pages/finance/MobileMoney';
import PaiementsParent from './pages/finance/PaiementsParent';

import GettingStarted from './pages/setup/GettingStarted';

import Enseignants from './pages/emploi/Enseignants';
import EnseignantDetail from './pages/emploi/EnseignantDetail';
import EmploiTemps from './pages/emploi/EmploiTemps';
import Affectations from './pages/emploi/Affectations';
import Salles from './pages/emploi/Salles';

import Absences from './pages/absences/Absences';
import Discipline from './pages/absences/Discipline';

import Documents from './pages/documents/Documents';
import VerifierQR from './pages/documents/VerifierQR';
import Notifications from './pages/notifications/Notifications';

import Etablissement from './pages/config/Etablissement';
import Annees from './pages/config/Annees';
import Classes from './pages/etablissement/Classes';
import Niveaux from './pages/etablissement/Niveaux';
import Matieres from './pages/config/Matieres';
import Coefficients from './pages/config/Coefficients';
import GradingRulesets from './pages/config/GradingRulesets';
import GradingRulesetDetail from './pages/config/GradingRulesetDetail';
import EvaluationTypes from './pages/config/EvaluationTypes';
import CalendrierScolaire from './pages/config/CalendrierScolaire';
import Trimestres from './pages/config/Trimestres';
import AuditJournal from './pages/config/AuditJournal';
import Utilisateurs from './pages/config/Utilisateurs';
import Programmes from './pages/etablissement/Programmes';
import ProgrammeDetail from './pages/etablissement/ProgrammeDetail';
import Periodes from './pages/etablissement/Periodes';

import ParentHome from './pages/parent/ParentHome';
import ParentPedagogie from './pages/parent/ParentPedagogie';
import ParentNotifications from './pages/parent/ParentNotifications';
import ParentEvolution from './pages/parent/ParentEvolution';
import ParentNotes from './pages/parent/ParentNotes';

import PlatformSchools from './pages/platform/PlatformSchools';
import PlatformOnboarding from './pages/platform/PlatformOnboarding';

import Cantine from './pages/vie-scolaire/Cantine';
import Transport from './pages/vie-scolaire/Transport';
import Internat from './pages/vie-scolaire/Internat';
import Infirmerie from './pages/vie-scolaire/Infirmerie';
import Bibliotheque from './pages/vie-scolaire/Bibliotheque';

import Contrats from './pages/rh/Contrats';
import Conges from './pages/rh/Conges';

import Visiteurs from './pages/front-office/Visiteurs';
import Sorties from './pages/front-office/Sorties';

import Inventaire from './pages/inventaire/Inventaire';

import Devoirs from './pages/elearning/Devoirs';
import Quiz from './pages/elearning/Quiz';

import EleveHome from './pages/eleve-portal/EleveHome';

import { homePathForRole } from './utils/homePath';

const ADMIN = ['administrateur', 'directeur'];
const SUPER_ADMIN = ['super_admin'];
const ALL_AUTHENTICATED = [
  ...ADMIN,
  'enseignant',
  'agent_comptable',
  'secretariat',
  'surveillant',
  'parent',
  'eleve',
  ...SUPER_ADMIN,
];
const DASHBOARD = [...ADMIN, 'agent_comptable', 'secretariat', 'enseignant', 'surveillant', ...SUPER_ADMIN];
const ELEVE_READ = [...ADMIN, 'agent_comptable', 'secretariat', 'enseignant', 'parent', ...SUPER_ADMIN];
const ELEVE_WRITE = [...ADMIN, 'secretariat', ...SUPER_ADMIN];
const NOTES = [...ADMIN, 'enseignant', 'secretariat', ...SUPER_ADMIN];
const NOTES_WRITE = [...ADMIN, 'enseignant', ...SUPER_ADMIN];
const NOTES_BULLETINS = [...ADMIN, 'enseignant', 'secretariat', 'parent', ...SUPER_ADMIN];
const NOTES_PARENT = [...ADMIN, 'enseignant', 'secretariat', 'parent', 'eleve', ...SUPER_ADMIN];
const FINANCE = [...ADMIN, 'agent_comptable', ...SUPER_ADMIN];
const FINANCE_WRITE = [...ADMIN, 'agent_comptable', ...SUPER_ADMIN];
const FINANCE_RECOUV = [...ADMIN, 'agent_comptable', 'secretariat', ...SUPER_ADMIN];
const EMPLOI = [...ADMIN, 'enseignant', ...SUPER_ADMIN];
const ABSENCES = [...ADMIN, 'enseignant', 'secretariat', 'surveillant', 'parent', 'eleve', ...SUPER_ADMIN];
const DISCIPLINE = [...ADMIN, 'enseignant', 'secretariat', 'surveillant', ...SUPER_ADMIN];
const DOCS = [...ADMIN, 'secretariat', ...SUPER_ADMIN];
const NOTIF = [...ADMIN, 'secretariat', ...SUPER_ADMIN];
const CLASS_NAV = [...ADMIN, 'agent_comptable', 'secretariat', 'enseignant', ...SUPER_ADMIN];
const ADMISSION = [...ADMIN, 'secretariat', ...SUPER_ADMIN];
const FRATRIES = [...ADMIN, 'secretariat', 'agent_comptable', ...SUPER_ADMIN];
const CONSEIL = [...ADMIN, 'enseignant', 'secretariat', ...SUPER_ADMIN];
const VIE_SCO = [...ADMIN, 'secretariat', ...SUPER_ADMIN];
const RH = [...ADMIN, ...SUPER_ADMIN];
const FRONT = [...ADMIN, 'secretariat', 'surveillant', ...SUPER_ADMIN];
const INVENTAIRE = [...ADMIN, 'secretariat', ...SUPER_ADMIN];
const ELEARNING = [...ADMIN, 'enseignant', 'secretariat', 'parent', 'eleve', ...SUPER_ADMIN];
const ELEARNING_WRITE = [...ADMIN, 'enseignant', ...SUPER_ADMIN];
const MOBILE_MONEY = [...ADMIN, 'agent_comptable', 'parent', ...SUPER_ADMIN];

const CONFIG = [...ADMIN, ...SUPER_ADMIN];
const SETUP = [...ADMIN, 'secretariat'];

function HomeRedirect() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const role = useAuthStore((s) => s.user?.role);
  if (!isAuthenticated) return <Navigate to="/" replace />;
  return <Navigate to={homePathForRole(role)} replace />;
}

function guard(roles, element) {
  return <ProtectedRoute roles={roles}>{element}</ProtectedRoute>;
}

export const routes = [
  {
    path: '/',
    element: <PublicHome />,
  },
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/login/otp',
    element: <OtpLogin />,
  },
  {
    path: '/forgot-password',
    element: <ForgotPassword />,
  },
  {
    path: '/change-password',
    element: (
      <ProtectedRoute>
        <ChangePassword />
      </ProtectedRoute>
    ),
  },
  {
    element: (
      <ProtectedRoute roles={ALL_AUTHENTICATED}>
        <Layout />
      </ProtectedRoute>
    ),
    children: [
      {
        path: 'platform/schools',
        element: guard(SUPER_ADMIN, <PlatformSchools />),
      },
      {
        path: 'platform/onboarding',
        element: guard(SUPER_ADMIN, <PlatformOnboarding />),
      },
      {
        path: 'parent',
        element: guard(['parent'], <ParentHome />),
      },
      {
        path: 'parent/pedagogie',
        element: guard(['parent'], <ParentPedagogie />),
      },
      {
        path: 'parent/notifications',
        element: guard(['parent'], <ParentNotifications />),
      },
      {
        path: 'parent/evolution',
        element: guard(['parent'], <ParentEvolution />),
      },
      {
        path: 'parent/notes',
        element: guard(['parent'], <ParentNotes />),
      },
      {
        path: 'eleve',
        element: guard(['eleve', ...ADMIN], <EleveHome />),
      },
      {
        path: 'dashboard',
        element: guard(DASHBOARD, <Dashboard />),
      },
      {
        path: 'setup',
        element: guard(SETUP, <GettingStarted />),
      },
      {
        path: 'classes',
        element: guard(CLASS_NAV, <ClassesHome />),
      },
      {
        path: 'classes/:cycle',
        element: guard(CLASS_NAV, <CycleClasses />),
      },
      {
        path: 'classes/:cycle/:classeSlug',
        element: guard(CLASS_NAV, <ClassDetail />),
      },
      {
        path: 'eleves/recherche',
        element: guard([...ELEVE_READ.filter((r) => r !== 'parent')], <EleveList />),
      },
      {
        path: 'eleves',
        element: guard(ELEVE_READ, <EleveList />),
      },
      {
        path: 'eleves/nouveau',
        element: guard(ELEVE_WRITE, <EleveForm />),
      },
      {
        path: 'eleves/import',
        element: guard(ELEVE_WRITE, <EleveImport />),
      },
      {
        path: 'eleves/fratries',
        element: guard(FRATRIES, <Fratries />),
      },
      {
        path: 'eleves/:id',
        element: guard(ELEVE_READ, <EleveDetail />),
      },
      {
        path: 'eleves/:id/modifier',
        element: guard(ELEVE_WRITE, <EleveForm />),
      },
      {
        path: 'eleves/:id/inscription',
        element: guard(ELEVE_WRITE, <InscriptionForm />),
      },
      {
        path: 'admission',
        element: guard(ADMISSION, <AdmissionList />),
      },
      {
        path: 'admission/nouveau',
        element: guard(ADMISSION, <AdmissionForm />),
      },
      {
        path: 'admission/:id',
        element: guard(ADMISSION, <AdmissionForm />),
      },
      {
        path: 'notes/evaluations',
        element: guard(NOTES, <EvaluationList />),
      },
      {
        path: 'notes/saisie/:evaluationId?',
        element: guard(NOTES_WRITE, <SaisieNotes />),
      },
      {
        path: 'notes/resultats',
        element: guard(NOTES_PARENT, <ResultatsAcademiques />),
      },
      {
        path: 'notes/bulletins',
        element: guard(NOTES_BULLETINS, <BulletinList />),
      },
      {
        path: 'notes/conseil-classe',
        element: guard(CONSEIL, <ConseilClasse />),
      },
      {
        path: 'finance/frais',
        element: guard(FINANCE, <FraisList />),
      },
      {
        path: 'finance/encaissement',
        element: guard(FINANCE_WRITE, <Encaissement />),
      },
      {
        path: 'finance/arrieres',
        element: guard(FINANCE, <Arrieres />),
      },
      {
        path: 'finance/recouvrement',
        element: guard(FINANCE_RECOUV, <Recouvrement />),
      },
      {
        path: 'finance/mobile-money',
        element: guard(MOBILE_MONEY, <MobileMoney />),
      },
      {
        path: 'finance/recus',
        element: guard(FINANCE, <Recus />),
      },
      {
        path: 'finance/syscohada',
        element: guard(FINANCE, <ComptabiliteSyscohada />),
      },
      {
        path: 'finance/ecritures',
        element: guard(FINANCE, <ComptabiliteEcritures />),
      },
      {
        path: 'finance/paie',
        element: guard(FINANCE, <Paie />),
      },
      {
        path: 'finance/paiements',
        element: guard(['parent'], <PaiementsParent />),
      },
      {
        path: 'emploi/enseignants',
        element: guard(EMPLOI, <Enseignants />),
      },
      {
        path: 'emploi/enseignants/:id',
        element: guard(EMPLOI, <EnseignantDetail />),
      },
      {
        path: 'emploi/temps',
        element: guard(EMPLOI, <EmploiTemps />),
      },
      {
        path: 'emploi/affectations',
        element: guard(ADMIN, <Affectations />),
      },
      {
        path: 'emploi/salles',
        element: guard(EMPLOI, <Salles />),
      },
      {
        path: 'absences',
        element: guard(ABSENCES, <Absences />),
      },
      {
        path: 'absences/discipline',
        element: guard(DISCIPLINE, <Discipline />),
      },
      {
        path: 'vie-scolaire/cantine',
        element: guard(VIE_SCO, <Cantine />),
      },
      {
        path: 'vie-scolaire/transport',
        element: guard(VIE_SCO, <Transport />),
      },
      {
        path: 'vie-scolaire/internat',
        element: guard(VIE_SCO, <Internat />),
      },
      {
        path: 'vie-scolaire/infirmerie',
        element: guard(VIE_SCO, <Infirmerie />),
      },
      {
        path: 'vie-scolaire/bibliotheque',
        element: guard([...VIE_SCO, 'enseignant'], <Bibliotheque />),
      },
      {
        path: 'rh/contrats',
        element: guard(RH, <Contrats />),
      },
      {
        path: 'rh/conges',
        element: guard(RH, <Conges />),
      },
      {
        path: 'front-office/visiteurs',
        element: guard(FRONT, <Visiteurs />),
      },
      {
        path: 'front-office/sorties',
        element: guard(FRONT, <Sorties />),
      },
      {
        path: 'inventaire',
        element: guard(INVENTAIRE, <Inventaire />),
      },
      {
        path: 'elearning/devoirs',
        element: guard(ELEARNING, <Devoirs />),
      },
      {
        path: 'elearning/quiz',
        element: guard(ELEARNING_WRITE, <Quiz />),
      },
      {
        path: 'documents',
        element: guard(DOCS, <Documents />),
      },
      {
        path: 'documents/verifier-qr',
        element: guard(DOCS, <VerifierQR />),
      },
      {
        path: 'notifications',
        element: guard(NOTIF, <Notifications />),
      },
      {
        path: 'config/etablissement',
        element: guard(CONFIG, <Etablissement />),
      },
      {
        path: 'config/annees',
        element: guard(CONFIG, <Annees />),
      },
      {
        path: 'etablissement/programmes',
        element: guard(CONFIG, <Programmes />),
      },
      {
        path: 'etablissement/programmes/:id',
        element: guard(CONFIG, <ProgrammeDetail />),
      },
      {
        path: 'etablissement/periodes',
        element: guard(CONFIG, <Periodes />),
      },
      {
        path: 'etablissement/niveaux',
        element: guard(CONFIG, <Niveaux />),
      },
      {
        path: 'etablissement/classes',
        element: guard(CONFIG, <Classes />),
      },
      {
        path: 'config/classes',
        element: guard(CONFIG, <Classes />),
      },
      {
        path: 'config/niveaux',
        element: guard(CONFIG, <Niveaux />),
      },
      {
        path: 'config/matieres',
        element: guard(CONFIG, <Matieres />),
      },
      {
        path: 'config/coefficients',
        element: guard(CONFIG, <Coefficients />),
      },
      {
        path: 'config/regles-notation',
        element: guard(CONFIG, <GradingRulesets />),
      },
      {
        path: 'config/regles-notation/:id',
        element: guard(CONFIG, <GradingRulesetDetail />),
      },
      {
        path: 'config/types-evaluation',
        element: guard(CONFIG, <EvaluationTypes />),
      },
      {
        path: 'config/trimestres',
        element: guard(CONFIG, <Trimestres />),
      },
      {
        path: 'config/calendrier',
        element: guard(CONFIG, <CalendrierScolaire />),
      },
      {
        path: 'config/audit',
        element: guard(CONFIG, <AuditJournal />),
      },
      {
        path: 'config/utilisateurs',
        element: guard(CONFIG, <Utilisateurs />),
      },
    ],
  },
  {
    path: '*',
    element: <HomeRedirect />,
  },
];
