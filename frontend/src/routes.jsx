import { Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import { useAuthStore } from './store/authStore';

import Login from './pages/auth/Login';
import ChangePassword from './pages/auth/ChangePassword';
import Dashboard from './pages/dashboard/Dashboard';

import ClassesHome from './pages/classes/ClassesHome';
import CycleClasses from './pages/classes/CycleClasses';
import ClassDetail from './pages/classes/ClassDetail';

import EleveList from './pages/eleves/EleveList';
import EleveDetail from './pages/eleves/EleveDetail';
import EleveForm from './pages/eleves/EleveForm';
import InscriptionForm from './pages/eleves/InscriptionForm';

import EvaluationList from './pages/notes/EvaluationList';
import SaisieNotes from './pages/notes/SaisieNotes';
import BulletinList from './pages/notes/BulletinList';

import FraisList from './pages/finance/FraisList';
import Encaissement from './pages/finance/Encaissement';
import Arrieres from './pages/finance/Arrieres';
import Recus from './pages/finance/Recus';

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
import Classes from './pages/config/Classes';
import Niveaux from './pages/config/Niveaux';
import Matieres from './pages/config/Matieres';
import Coefficients from './pages/config/Coefficients';
import CalendrierScolaire from './pages/config/CalendrierScolaire';
import Trimestres from './pages/config/Trimestres';
import AuditJournal from './pages/config/AuditJournal';
import Utilisateurs from './pages/config/Utilisateurs';

import ForgotPassword from './pages/auth/ForgotPassword';
import ParentHome from './pages/parent/ParentHome';
import PaiementsParent from './pages/finance/PaiementsParent';

const ADMIN = ['administrateur', 'directeur'];
const ALL_AUTHENTICATED = [...ADMIN, 'enseignant', 'agent_comptable', 'secretariat', 'parent'];
const DASHBOARD = [...ADMIN, 'agent_comptable', 'secretariat'];
const ELEVE_READ = [...ADMIN, 'agent_comptable', 'secretariat', 'parent'];
const ELEVE_WRITE = [...ADMIN, 'secretariat'];
const NOTES = [...ADMIN, 'enseignant', 'secretariat', 'parent'];
const NOTES_WRITE = [...ADMIN, 'enseignant'];
const FINANCE = [...ADMIN, 'agent_comptable', 'secretariat'];
const FINANCE_WRITE = [...ADMIN, 'agent_comptable'];
const EMPLOI = [...ADMIN, 'enseignant'];
const ABSENCES = [...ADMIN, 'enseignant', 'secretariat', 'parent'];
const DOCS = [...ADMIN, 'secretariat'];
const NOTIF = [...ADMIN, 'secretariat'];
const CLASS_NAV = [...ADMIN, 'agent_comptable', 'secretariat', 'enseignant'];

const CONFIG = ADMIN;

function HomeRedirect() {
  const role = useAuthStore((s) => s.user?.role);
  if (role === 'parent') return <Navigate to="/parent" replace />;
  if (role && DASHBOARD.includes(role)) return <Navigate to="/dashboard" replace />;
  if (role === 'enseignant') return <Navigate to="/classes" replace />;
  return <Navigate to="/classes" replace />;
}

export const routes = [
  {
    path: '/login',
    element: <Login />,
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
    path: '/',
    element: (
      <ProtectedRoute roles={ALL_AUTHENTICATED}>
        <Layout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <HomeRedirect /> },
      {
        path: 'parent',
        element: (
          <ProtectedRoute roles={['parent']}>
            <ParentHome />
          </ProtectedRoute>
        ),
      },
      {
        path: 'dashboard',
        element: (
          <ProtectedRoute roles={DASHBOARD}>
            <Dashboard />
          </ProtectedRoute>
        ),
      },
      {
        path: 'classes',
        element: (
          <ProtectedRoute roles={CLASS_NAV}>
            <ClassesHome />
          </ProtectedRoute>
        ),
      },
      {
        path: 'classes/:cycle',
        element: (
          <ProtectedRoute roles={CLASS_NAV}>
            <CycleClasses />
          </ProtectedRoute>
        ),
      },
      {
        path: 'classes/:cycle/:classeSlug',
        element: (
          <ProtectedRoute roles={CLASS_NAV}>
            <ClassDetail />
          </ProtectedRoute>
        ),
      },
      {
        path: 'eleves/recherche',
        element: (
          <ProtectedRoute roles={[...ELEVE_READ.filter((r) => r !== 'parent')]}>
            <EleveList />
          </ProtectedRoute>
        ),
      },
      {
        path: 'eleves',
        element: (
          <ProtectedRoute roles={ELEVE_READ}>
            <EleveList />
          </ProtectedRoute>
        ),
      },
      {
        path: 'eleves/nouveau',
        element: (
          <ProtectedRoute roles={ELEVE_WRITE}>
            <EleveForm />
          </ProtectedRoute>
        ),
      },
      {
        path: 'eleves/:id',
        element: (
          <ProtectedRoute roles={ELEVE_READ}>
            <EleveDetail />
          </ProtectedRoute>
        ),
      },
      {
        path: 'eleves/:id/modifier',
        element: (
          <ProtectedRoute roles={ELEVE_WRITE}>
            <EleveForm />
          </ProtectedRoute>
        ),
      },
      {
        path: 'eleves/:id/inscription',
        element: (
          <ProtectedRoute roles={ELEVE_WRITE}>
            <InscriptionForm />
          </ProtectedRoute>
        ),
      },
      {
        path: 'notes/evaluations',
        element: (
          <ProtectedRoute roles={NOTES}>
            <EvaluationList />
          </ProtectedRoute>
        ),
      },
      {
        path: 'notes/saisie/:evaluationId?',
        element: (
          <ProtectedRoute roles={NOTES_WRITE}>
            <SaisieNotes />
          </ProtectedRoute>
        ),
      },
      {
        path: 'notes/bulletins',
        element: (
          <ProtectedRoute roles={NOTES}>
            <BulletinList />
          </ProtectedRoute>
        ),
      },
      {
        path: 'finance/frais',
        element: (
          <ProtectedRoute roles={FINANCE}>
            <FraisList />
          </ProtectedRoute>
        ),
      },
      {
        path: 'finance/encaissement',
        element: (
          <ProtectedRoute roles={FINANCE_WRITE}>
            <Encaissement />
          </ProtectedRoute>
        ),
      },
      {
        path: 'finance/arrieres',
        element: (
          <ProtectedRoute roles={FINANCE}>
            <Arrieres />
          </ProtectedRoute>
        ),
      },
      {
        path: 'finance/recus',
        element: (
          <ProtectedRoute roles={FINANCE}>
            <Recus />
          </ProtectedRoute>
        ),
      },
      {
        path: 'finance/paiements',
        element: (
          <ProtectedRoute roles={['parent']}>
            <PaiementsParent />
          </ProtectedRoute>
        ),
      },
      {
        path: 'emploi/enseignants',
        element: (
          <ProtectedRoute roles={EMPLOI}>
            <Enseignants />
          </ProtectedRoute>
        ),
      },
      {
        path: 'emploi/enseignants/:id',
        element: (
          <ProtectedRoute roles={EMPLOI}>
            <EnseignantDetail />
          </ProtectedRoute>
        ),
      },
      {
        path: 'emploi/temps',
        element: (
          <ProtectedRoute roles={EMPLOI}>
            <EmploiTemps />
          </ProtectedRoute>
        ),
      },
      {
        path: 'emploi/affectations',
        element: (
          <ProtectedRoute roles={ADMIN}>
            <Affectations />
          </ProtectedRoute>
        ),
      },
      {
        path: 'emploi/salles',
        element: (
          <ProtectedRoute roles={EMPLOI}>
            <Salles />
          </ProtectedRoute>
        ),
      },
      {
        path: 'absences',
        element: (
          <ProtectedRoute roles={ABSENCES}>
            <Absences />
          </ProtectedRoute>
        ),
      },
      {
        path: 'absences/discipline',
        element: (
          <ProtectedRoute roles={ABSENCES}>
            <Discipline />
          </ProtectedRoute>
        ),
      },
      {
        path: 'documents',
        element: (
          <ProtectedRoute roles={DOCS}>
            <Documents />
          </ProtectedRoute>
        ),
      },
      {
        path: 'documents/verifier-qr',
        element: (
          <ProtectedRoute roles={DOCS}>
            <VerifierQR />
          </ProtectedRoute>
        ),
      },
      {
        path: 'notifications',
        element: (
          <ProtectedRoute roles={NOTIF}>
            <Notifications />
          </ProtectedRoute>
        ),
      },
      {
        path: 'config/etablissement',
        element: (
          <ProtectedRoute roles={CONFIG}>
            <Etablissement />
          </ProtectedRoute>
        ),
      },
      {
        path: 'config/annees',
        element: (
          <ProtectedRoute roles={CONFIG}>
            <Annees />
          </ProtectedRoute>
        ),
      },
      {
        path: 'config/classes',
        element: (
          <ProtectedRoute roles={CONFIG}>
            <Classes />
          </ProtectedRoute>
        ),
      },
      {
        path: 'config/niveaux',
        element: (
          <ProtectedRoute roles={CONFIG}>
            <Niveaux />
          </ProtectedRoute>
        ),
      },
      {
        path: 'config/matieres',
        element: (
          <ProtectedRoute roles={CONFIG}>
            <Matieres />
          </ProtectedRoute>
        ),
      },
      {
        path: 'config/coefficients',
        element: (
          <ProtectedRoute roles={CONFIG}>
            <Coefficients />
          </ProtectedRoute>
        ),
      },
      {
        path: 'config/trimestres',
        element: (
          <ProtectedRoute roles={CONFIG}>
            <Trimestres />
          </ProtectedRoute>
        ),
      },
      {
        path: 'config/calendrier',
        element: (
          <ProtectedRoute roles={CONFIG}>
            <CalendrierScolaire />
          </ProtectedRoute>
        ),
      },
      {
        path: 'config/audit',
        element: (
          <ProtectedRoute roles={CONFIG}>
            <AuditJournal />
          </ProtectedRoute>
        ),
      },
      {
        path: 'config/utilisateurs',
        element: (
          <ProtectedRoute roles={CONFIG}>
            <Utilisateurs />
          </ProtectedRoute>
        ),
      },
    ],
  },
  {
    path: '*',
    element: <HomeRedirect />,
  },
];
