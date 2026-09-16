import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  GraduationCap,
  FileText,
  Wallet,
  Calendar,
  ClipboardList,
  FolderOpen,
  Bell,
  Settings,
  Home,
  Receipt,
  BookOpen,
  X,
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import SealMedallion from './SealMedallion';

const ADMIN_ROLES = ['administrateur', 'directeur'];
const PLATFORM_ROLES = ['super_admin'];

const ICONS = {
  home: Home,
  dashboard: LayoutDashboard,
  eleves: GraduationCap,
  notes: FileText,
  finance: Wallet,
  paiements: Receipt,
  emploi: Calendar,
  absences: ClipboardList,
  documents: FolderOpen,
  notifications: Bell,
  config: Settings,
  pedagogie: BookOpen,
};

const menuItems = [
  {
    label: 'Écoles plateforme',
    path: '/platform/schools',
    icon: 'dashboard',
    roles: PLATFORM_ROLES,
  },
  {
    label: 'Onboarding',
    path: '/platform/onboarding',
    icon: 'config',
    roles: PLATFORM_ROLES,
  },
  { label: 'Accueil', path: '/parent', icon: 'home', roles: ['parent'] },
  {
    label: 'Programme pédagogique',
    path: '/parent/pedagogie',
    icon: 'pedagogie',
    roles: ['parent'],
  },
  { label: 'Bulletins', path: '/notes/bulletins', icon: 'notes', roles: ['parent'] },
  { label: 'Absences', path: '/absences', icon: 'absences', roles: ['parent'] },
  {
    label: 'Tableau de bord',
    path: '/dashboard',
    icon: 'dashboard',
    roles: [...ADMIN_ROLES, 'agent_comptable', 'secretariat'],
  },
  {
    label: 'Élèves',
    path: '/classes',
    icon: 'eleves',
    roles: [...ADMIN_ROLES, 'agent_comptable', 'secretariat', 'enseignant'],
  },
  {
    label: 'Élèves',
    path: '/eleves',
    icon: 'eleves',
    roles: ['parent'],
  },
  {
    label: 'Notes & Bulletins',
    path: '/notes/evaluations',
    icon: 'notes',
    roles: [...ADMIN_ROLES, 'enseignant', 'secretariat'],
    children: [
      { label: 'Évaluations', path: '/notes/evaluations', roles: [...ADMIN_ROLES, 'enseignant', 'secretariat'] },
      { label: 'Saisie des notes', path: '/notes/saisie', roles: [...ADMIN_ROLES, 'enseignant'] },
      { label: 'Résultats', path: '/notes/resultats', roles: [...ADMIN_ROLES, 'enseignant', 'secretariat'] },
      { label: 'Bulletins', path: '/notes/bulletins', roles: [...ADMIN_ROLES, 'enseignant', 'secretariat'] },
    ],
  },
  {
    label: 'Finance',
    path: '/finance/frais',
    icon: 'finance',
    roles: [...ADMIN_ROLES, 'agent_comptable', 'secretariat'],
    children: [
      { label: 'Frais scolaires', path: '/finance/frais', roles: [...ADMIN_ROLES, 'agent_comptable', 'secretariat'] },
      { label: 'Encaissement', path: '/finance/encaissement', roles: [...ADMIN_ROLES, 'agent_comptable'] },
      { label: 'Arriérés', path: '/finance/arrieres', roles: [...ADMIN_ROLES, 'agent_comptable', 'secretariat'] },
      { label: 'Reçus', path: '/finance/recus', roles: [...ADMIN_ROLES, 'agent_comptable', 'secretariat'] },
    ],
  },
  { label: 'Paiements', path: '/finance/paiements', icon: 'paiements', roles: ['parent'] },
  {
    label: 'Emploi du temps',
    path: '/emploi/temps',
    icon: 'emploi',
    roles: [...ADMIN_ROLES, 'enseignant'],
    children: [
      { label: 'Enseignants', path: '/emploi/enseignants', roles: [...ADMIN_ROLES, 'enseignant'] },
      { label: 'Emploi du temps', path: '/emploi/temps', roles: [...ADMIN_ROLES, 'enseignant'] },
      { label: 'Affectations', path: '/emploi/affectations', roles: ADMIN_ROLES },
      { label: 'Salles', path: '/emploi/salles', roles: [...ADMIN_ROLES, 'enseignant'] },
    ],
  },
  {
    label: 'Absences & Discipline',
    path: '/absences',
    icon: 'absences',
    roles: [...ADMIN_ROLES, 'enseignant', 'secretariat'],
    children: [
      { label: 'Absences', path: '/absences', roles: [...ADMIN_ROLES, 'enseignant', 'secretariat'] },
      { label: 'Discipline', path: '/absences/discipline', roles: [...ADMIN_ROLES, 'enseignant', 'secretariat'] },
    ],
  },
  {
    label: 'Documents',
    path: '/documents',
    icon: 'documents',
    roles: [...ADMIN_ROLES, 'secretariat'],
    children: [
      { label: 'Génération', path: '/documents', roles: [...ADMIN_ROLES, 'secretariat'] },
      { label: 'Vérifier QR', path: '/documents/verifier-qr', roles: [...ADMIN_ROLES, 'secretariat'] },
    ],
  },
  {
    label: 'Notifications',
    path: '/notifications',
    icon: 'notifications',
    roles: [...ADMIN_ROLES, 'secretariat'],
  },
  {
    label: 'Configuration',
    path: '/config/etablissement',
    icon: 'config',
    roles: ADMIN_ROLES,
    children: [
      { label: 'Établissement', path: '/config/etablissement', roles: ADMIN_ROLES },
      { label: 'Années scolaires', path: '/config/annees', roles: ADMIN_ROLES },
      { label: 'Programmes', path: '/etablissement/programmes', roles: ADMIN_ROLES },
      { label: 'Périodes', path: '/etablissement/periodes', roles: ADMIN_ROLES },
      { label: 'Niveaux', path: '/etablissement/niveaux', roles: ADMIN_ROLES },
      { label: 'Classes', path: '/etablissement/classes', roles: ADMIN_ROLES },
      { label: 'Trimestres (legacy)', path: '/config/trimestres', roles: ADMIN_ROLES },
      { label: 'Calendrier scolaire', path: '/config/calendrier', roles: ADMIN_ROLES },
      { label: 'Matières', path: '/config/matieres', roles: ADMIN_ROLES },
      { label: 'Coefficients', path: '/config/coefficients', roles: ADMIN_ROLES },
      { label: 'Règles de notation', path: '/config/regles-notation', roles: ADMIN_ROLES },
      { label: 'Utilisateurs', path: '/config/utilisateurs', roles: ADMIN_ROLES },
      { label: 'Journal audit', path: '/config/audit', roles: ADMIN_ROLES },
    ],
  },
];

function NavIcon({ name }) {
  const Icon = ICONS[name] || FileText;
  return <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={1.75} aria-hidden="true" />;
}

function NavItem({ item, collapsed, onNavigate, role }) {
  const location = useLocation();
  const isActive =
    location.pathname === item.path ||
    item.children?.some((c) => location.pathname.startsWith(c.path));

  const linkClass = isActive
    ? 'border-l-2 border-or-cachet bg-or-cachet-clair text-craie rounded-r-lg'
    : 'text-craie/70 hover:bg-or-cachet-clair/40 hover:text-craie rounded-lg';

  const childVisible = (child) => {
    if (!child.roles) return true;
    if (!role) return false;
    if (child.roles.includes(role)) return true;
    if (role === 'super_admin') {
      return child.roles.some((r) => ADMIN_ROLES.includes(r));
    }
    return false;
  };

  if (item.children) {
    return (
      <div className="space-y-1">
        <Link
          to={item.path}
          onClick={onNavigate}
          className={`flex items-center gap-3 px-3 py-2.5 text-sm font-medium transition-all duration-200 ${linkClass} ${isActive ? '[&_svg]:text-or-cachet' : ''}`}
        >
          <NavIcon name={item.icon} />
          {!collapsed && <span>{item.label}</span>}
        </Link>
        {!collapsed && isActive && (
          <div className="ml-9 space-y-1 border-l border-craie/20 pl-3">
            {item.children.filter(childVisible).map((child) => (
              <Link
                key={child.path}
                to={child.path}
                onClick={onNavigate}
                className={`block rounded-md px-2 py-1.5 text-xs transition-colors ${
                  location.pathname === child.path || location.pathname.startsWith(child.path + '/')
                    ? 'font-medium text-or-cachet'
                    : 'text-craie/60 hover:text-craie'
                }`}
              >
                {child.label}
              </Link>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <Link
      to={item.path}
      onClick={onNavigate}
      className={`flex items-center gap-3 px-3 py-2.5 text-sm font-medium transition-all duration-200 ${linkClass} ${isActive ? '[&_svg]:text-or-cachet' : ''}`}
    >
      <NavIcon name={item.icon} />
      {!collapsed && <span>{item.label}</span>}
    </Link>
  );
}

export default function Sidebar({ collapsed, mobileOpen, onCloseMobile }) {
  const user = useAuthStore((s) => s.user);
  const actingSchoolId = useAuthStore((s) => s.actingSchoolId);
  const role = user?.role;
  const visibleItems = menuItems.filter((item) => {
    if (!role) return false;
    if (item.roles.includes(role)) return true;
    // SUPER_ADMIN en contexte école : accès navigation admin école
    if (role === 'super_admin' && actingSchoolId) {
      return item.roles.some((r) => ADMIN_ROLES.includes(r));
    }
    return false;
  });

  return (
    <aside
      className={`sidebar-premium fixed inset-y-0 left-0 z-50 w-64 transform shadow-[4px_0_24px_rgba(13,22,40,0.15)] transition-transform duration-300 lg:static lg:translate-x-0 ${
        mobileOpen ? 'translate-x-0' : '-translate-x-full'
      } ${collapsed ? 'lg:w-20' : 'lg:w-64'}`}
    >
      <div className="flex h-full flex-col">
        <div
          className={`flex items-center border-b border-white/[0.08] px-4 py-5 ${collapsed ? 'justify-center' : 'gap-3'}`}
        >
          <SealMedallion size="md" />
          {!collapsed && (
            <div className="min-w-0 flex-1">
              <h1 className="font-display text-sm font-medium tracking-tight text-craie">
                Gestion Scolaire
              </h1>
              <p className="text-[11px] capitalize tracking-wide text-craie/50">
                {role?.replace('_', ' ')}
              </p>
            </div>
          )}
          {mobileOpen && (
            <button
              type="button"
              onClick={onCloseMobile}
              className="rounded-input p-2 text-craie/70 hover:bg-encre-clair hover:text-craie lg:hidden"
              aria-label="Fermer le menu"
            >
              <X className="h-5 w-5" strokeWidth={1.75} />
            </button>
          )}
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-4">
          {visibleItems.map((item) => (
            <NavItem
              key={item.path}
              item={item}
              collapsed={collapsed}
              onNavigate={onCloseMobile}
              role={role}
            />
          ))}
        </nav>
      </div>
    </aside>
  );
}
