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
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import SealMedallion from './SealMedallion';

const ADMIN_ROLES = ['administrateur', 'directeur'];

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
};

const menuItems = [
  { label: 'Accueil', path: '/parent', icon: 'home', roles: ['parent'] },
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
      { label: 'Évaluations', path: '/notes/evaluations' },
      { label: 'Saisie des notes', path: '/notes/saisie' },
      { label: 'Bulletins', path: '/notes/bulletins' },
    ],
  },
  {
    label: 'Finance',
    path: '/finance/frais',
    icon: 'finance',
    roles: [...ADMIN_ROLES, 'agent_comptable', 'secretariat'],
    children: [
      { label: 'Frais scolaires', path: '/finance/frais' },
      { label: 'Encaissement', path: '/finance/encaissement' },
      { label: 'Arriérés', path: '/finance/arrieres' },
      { label: 'Reçus', path: '/finance/recus' },
    ],
  },
  { label: 'Paiements', path: '/finance/paiements', icon: 'paiements', roles: ['parent'] },
  {
    label: 'Emploi du temps',
    path: '/emploi/temps',
    icon: 'emploi',
    roles: [...ADMIN_ROLES, 'enseignant'],
    children: [
      { label: 'Enseignants', path: '/emploi/enseignants' },
      { label: 'Emploi du temps', path: '/emploi/temps' },
      { label: 'Affectations', path: '/emploi/affectations' },
      { label: 'Salles', path: '/emploi/salles' },
    ],
  },
  {
    label: 'Absences & Discipline',
    path: '/absences',
    icon: 'absences',
    roles: [...ADMIN_ROLES, 'enseignant', 'secretariat'],
    children: [
      { label: 'Absences', path: '/absences' },
      { label: 'Discipline', path: '/absences/discipline' },
    ],
  },
  {
    label: 'Documents',
    path: '/documents',
    icon: 'documents',
    roles: [...ADMIN_ROLES, 'secretariat'],
    children: [
      { label: 'Génération', path: '/documents' },
      { label: 'Vérifier QR', path: '/documents/verifier-qr' },
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
      { label: 'Établissement', path: '/config/etablissement' },
      { label: 'Années scolaires', path: '/config/annees' },
      { label: 'Trimestres', path: '/config/trimestres' },
      { label: 'Calendrier scolaire', path: '/config/calendrier' },
      { label: 'Niveaux', path: '/config/niveaux' },
      { label: 'Classes', path: '/config/classes' },
      { label: 'Matières', path: '/config/matieres' },
      { label: 'Coefficients', path: '/config/coefficients' },
      { label: 'Utilisateurs', path: '/config/utilisateurs' },
      { label: 'Journal audit', path: '/config/audit' },
    ],
  },
];

function NavIcon({ name }) {
  const Icon = ICONS[name] || FileText;
  return <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={1.75} aria-hidden="true" />;
}

function NavItem({ item, collapsed, onNavigate }) {
  const location = useLocation();
  const isActive =
    location.pathname === item.path ||
    item.children?.some((c) => location.pathname.startsWith(c.path));

  const linkClass = isActive
    ? 'border-l-2 border-or-cachet bg-or-cachet-clair text-craie rounded-r-lg'
    : 'text-craie/70 hover:bg-encre-clair hover:text-craie rounded-lg';

  if (item.children) {
    return (
      <div className="space-y-1">
        <Link
          to={item.path}
          onClick={onNavigate}
          className={`flex items-center gap-3 px-3 py-2 text-sm font-medium transition-colors ${linkClass}`}
        >
          <NavIcon name={item.icon} />
          {!collapsed && <span>{item.label}</span>}
        </Link>
        {!collapsed && isActive && (
          <div className="ml-9 space-y-1 border-l border-craie/20 pl-3">
            {item.children.map((child) => (
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
      className={`flex items-center gap-3 px-3 py-2 text-sm font-medium transition-colors ${linkClass}`}
    >
      <NavIcon name={item.icon} />
      {!collapsed && <span>{item.label}</span>}
    </Link>
  );
}

export default function Sidebar({ collapsed, mobileOpen, onCloseMobile }) {
  const user = useAuthStore((s) => s.user);
  const role = user?.role;
  const visibleItems = menuItems.filter((item) => role && item.roles.includes(role));

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-50 w-64 transform bg-encre transition-transform lg:static lg:translate-x-0 ${
        mobileOpen ? 'translate-x-0' : '-translate-x-full'
      } ${collapsed ? 'lg:w-20' : 'lg:w-64'}`}
    >
      <div className="flex h-full flex-col">
        <div
          className={`flex items-center border-b border-craie/10 px-4 py-5 ${collapsed ? 'justify-center' : 'gap-3'}`}
        >
          <SealMedallion size="md" />
          {!collapsed && (
            <div>
              <h1 className="font-display text-sm font-medium text-craie">Gestion Scolaire</h1>
              <p className="text-xs capitalize text-craie/60">{role?.replace('_', ' ')}</p>
            </div>
          )}
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {visibleItems.map((item) => (
            <NavItem key={item.path} item={item} collapsed={collapsed} onNavigate={onCloseMobile} />
          ))}
        </nav>
      </div>
    </aside>
  );
}
