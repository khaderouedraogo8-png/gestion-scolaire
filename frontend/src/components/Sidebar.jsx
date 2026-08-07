import { Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

const ADMIN_ROLES = ['administrateur', 'directeur'];

const menuItems = [
  {
    label: 'Accueil',
    path: '/parent',
    icon: '🏠',
    roles: ['parent'],
  },
  {
    label: 'Bulletins',
    path: '/notes/bulletins',
    icon: '📝',
    roles: ['parent'],
  },
  {
    label: 'Absences',
    path: '/absences',
    icon: '📋',
    roles: ['parent'],
  },
  {
    label: 'Tableau de bord',
    path: '/dashboard',
    icon: '📊',
    roles: [...ADMIN_ROLES, 'agent_comptable', 'secretariat'],
  },
  {
    label: 'Élèves',
    path: '/eleves',
    icon: '👨‍🎓',
    roles: [...ADMIN_ROLES, 'agent_comptable', 'secretariat', 'parent'],
  },
  {
    label: 'Notes & Bulletins',
    path: '/notes/evaluations',
    icon: '📝',
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
    icon: '💰',
    roles: [...ADMIN_ROLES, 'agent_comptable', 'secretariat'],
    children: [
      { label: 'Frais scolaires', path: '/finance/frais' },
      { label: 'Encaissement', path: '/finance/encaissement' },
      { label: 'Arriérés', path: '/finance/arrieres' },
      { label: 'Reçus', path: '/finance/recus' },
    ],
  },
  {
    label: 'Paiements',
    path: '/finance/paiements',
    icon: '💰',
    roles: ['parent'],
  },
  {
    label: 'Emploi du temps',
    path: '/emploi/temps',
    icon: '📅',
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
    icon: '📋',
    roles: [...ADMIN_ROLES, 'enseignant', 'secretariat'],
    children: [
      { label: 'Absences', path: '/absences' },
      { label: 'Discipline', path: '/absences/discipline' },
    ],
  },
  {
    label: 'Documents',
    path: '/documents',
    icon: '📄',
    roles: [...ADMIN_ROLES, 'secretariat'],
    children: [
      { label: 'Génération', path: '/documents' },
      { label: 'Vérifier QR', path: '/documents/verifier-qr' },
    ],
  },
  {
    label: 'Notifications',
    path: '/notifications',
    icon: '🔔',
    roles: [...ADMIN_ROLES, 'secretariat'],
  },
  {
    label: 'Configuration',
    path: '/config/etablissement',
    icon: '⚙️',
    roles: ADMIN_ROLES,
    children: [
      { label: 'Établissement', path: '/config/etablissement' },
      { label: 'Années scolaires', path: '/config/annees' },
      { label: 'Trimestres', path: '/config/trimestres' },
      { label: 'Niveaux', path: '/config/niveaux' },
      { label: 'Classes', path: '/config/classes' },
      { label: 'Matières', path: '/config/matieres' },
      { label: 'Coefficients', path: '/config/coefficients' },
      { label: 'Utilisateurs', path: '/config/utilisateurs' },
      { label: 'Journal audit', path: '/config/audit' },
    ],
  },
];

function NavItem({ item, collapsed, onNavigate }) {
  const location = useLocation();
  const isActive =
    location.pathname === item.path ||
    item.children?.some((c) => location.pathname.startsWith(c.path));

  if (item.children) {
    return (
      <div className="space-y-1">
        <Link
          to={item.path}
          onClick={onNavigate}
          className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
            isActive
              ? 'bg-primary-50 text-primary-700'
              : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
          }`}
        >
          <span className="text-lg">{item.icon}</span>
          {!collapsed && <span>{item.label}</span>}
        </Link>
        {!collapsed && isActive && (
          <div className="ml-9 space-y-1 border-l border-slate-200 pl-3">
            {item.children.map((child) => (
              <Link
                key={child.path}
                to={child.path}
                onClick={onNavigate}
                className={`block rounded-md px-2 py-1.5 text-xs transition-colors ${
                  location.pathname === child.path || location.pathname.startsWith(child.path + '/')
                    ? 'font-medium text-primary-700'
                    : 'text-slate-500 hover:text-slate-800'
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
      className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
        isActive
          ? 'bg-primary-50 text-primary-700'
          : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
      }`}
    >
      <span className="text-lg">{item.icon}</span>
      {!collapsed && <span>{item.label}</span>}
    </Link>
  );
}

export default function Sidebar({ collapsed, mobileOpen, onCloseMobile }) {
  const user = useAuthStore((s) => s.user);
  const role = user?.role;

  const visibleItems = menuItems.filter((item) => role && item.roles.includes(role));

  const sidebarContent = (
    <div className="flex h-full flex-col">
      <div className={`flex items-center border-b border-slate-200 px-4 py-5 ${collapsed ? 'justify-center' : 'gap-3'}`}>
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-600 text-white font-bold">
          GS
        </div>
        {!collapsed && (
          <div>
            <h1 className="text-sm font-bold text-slate-900">Gestion Scolaire</h1>
            <p className="text-xs text-slate-500 capitalize">{role?.replace('_', ' ')}</p>
          </div>
        )}
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto p-3">
        {visibleItems.map((item) => (
          <NavItem key={item.path} item={item} collapsed={collapsed} onNavigate={onCloseMobile} />
        ))}
      </nav>
    </div>
  );

  return (
    <>
      {mobileOpen && (
        <div className="fixed inset-0 z-40 bg-slate-900/50 lg:hidden" onClick={onCloseMobile} />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 transform border-r border-slate-200 bg-white transition-transform lg:static lg:translate-x-0 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        } ${collapsed ? 'lg:w-20' : 'lg:w-64'}`}
      >
        {sidebarContent}
      </aside>
    </>
  );
}
