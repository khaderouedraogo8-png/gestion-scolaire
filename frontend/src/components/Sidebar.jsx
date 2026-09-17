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
  TrendingUp,
  Rocket,
  UserPlus,
  Users,
  Bus,
  UtensilsCrossed,
  BedDouble,
  Cross,
  Library,
  Briefcase,
  DoorOpen,
  Package,
  Laptop,
  Smartphone,
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
  evolution: TrendingUp,
  demarrage: Rocket,
  admission: UserPlus,
  fratries: Users,
  viesco: Bus,
  cantine: UtensilsCrossed,
  internat: BedDouble,
  infirmiere: Cross,
  biblio: Library,
  rh: Briefcase,
  frontoffice: DoorOpen,
  inventaire: Package,
  elearning: Laptop,
  mobile: Smartphone,
};

/**
 * section: groupe visuel sidebar (n’affecte pas le RBAC)
 */
const menuItems = [
  {
    label: 'Écoles plateforme',
    path: '/platform/schools',
    icon: 'dashboard',
    roles: PLATFORM_ROLES,
    section: 'plateforme',
  },
  {
    label: 'Onboarding',
    path: '/platform/onboarding',
    icon: 'config',
    roles: PLATFORM_ROLES,
    section: 'plateforme',
  },
  { label: 'Accueil', path: '/parent', icon: 'home', roles: ['parent'], section: 'parent' },
  {
    label: 'Programme pédagogique',
    path: '/parent/pedagogie',
    icon: 'pedagogie',
    roles: ['parent'],
    section: 'parent',
  },
  { label: 'Notes & résultats', path: '/parent/notes', icon: 'notes', roles: ['parent'], section: 'parent' },
  { label: 'Évolution', path: '/parent/evolution', icon: 'evolution', roles: ['parent'], section: 'parent' },
  { label: 'Bulletins', path: '/notes/bulletins', icon: 'notes', roles: ['parent'], section: 'parent' },
  { label: 'Absences', path: '/absences', icon: 'absences', roles: ['parent'], section: 'parent' },
  {
    label: 'Notifications',
    path: '/parent/notifications',
    icon: 'notifications',
    roles: ['parent'],
    section: 'parent',
  },
  { label: 'Paiements', path: '/finance/paiements', icon: 'paiements', roles: ['parent'], section: 'parent' },
  {
    label: 'Mobile Money',
    path: '/finance/mobile-money',
    icon: 'mobile',
    roles: ['parent'],
    section: 'parent',
  },
  {
    label: 'Élèves',
    path: '/eleves',
    icon: 'eleves',
    roles: ['parent'],
    section: 'parent',
  },
  { label: 'Mon espace', path: '/eleve', icon: 'home', roles: ['eleve'], section: 'eleve' },
  { label: 'Devoirs', path: '/elearning/devoirs', icon: 'elearning', roles: ['eleve'], section: 'eleve' },
  {
    label: 'Tableau de bord',
    path: '/dashboard',
    icon: 'dashboard',
    roles: [...ADMIN_ROLES, 'agent_comptable', 'secretariat', 'enseignant', 'surveillant'],
    section: 'principal',
  },
  {
    label: 'Démarrage',
    path: '/setup',
    icon: 'demarrage',
    roles: [...ADMIN_ROLES, 'secretariat'],
    section: 'principal',
  },
  {
    label: 'Élèves',
    path: '/classes',
    icon: 'eleves',
    roles: [...ADMIN_ROLES, 'agent_comptable', 'secretariat', 'enseignant'],
    section: 'principal',
    children: [
      { label: 'Par classes', path: '/classes', roles: [...ADMIN_ROLES, 'agent_comptable', 'secretariat', 'enseignant'] },
      { label: 'Liste / recherche', path: '/eleves', roles: [...ADMIN_ROLES, 'agent_comptable', 'secretariat', 'enseignant'] },
      { label: 'Fratries & remises', path: '/eleves/fratries', roles: [...ADMIN_ROLES, 'secretariat', 'agent_comptable'] },
      { label: 'Admissions', path: '/admission', roles: [...ADMIN_ROLES, 'secretariat'] },
    ],
  },
  {
    label: 'Notes & Bulletins',
    path: '/notes/evaluations',
    icon: 'notes',
    roles: [...ADMIN_ROLES, 'enseignant', 'secretariat'],
    section: 'academique',
    children: [
      { label: 'Évaluations', path: '/notes/evaluations', roles: [...ADMIN_ROLES, 'enseignant', 'secretariat'] },
      { label: 'Saisie des notes', path: '/notes/saisie', roles: [...ADMIN_ROLES, 'enseignant'] },
      { label: 'Résultats', path: '/notes/resultats', roles: [...ADMIN_ROLES, 'enseignant', 'secretariat'] },
      { label: 'Bulletins', path: '/notes/bulletins', roles: [...ADMIN_ROLES, 'enseignant', 'secretariat'] },
      { label: 'Conseil de classe', path: '/notes/conseil-classe', roles: [...ADMIN_ROLES, 'enseignant', 'secretariat'] },
    ],
  },
  {
    label: 'E-learning',
    path: '/elearning/devoirs',
    icon: 'elearning',
    roles: [...ADMIN_ROLES, 'enseignant', 'secretariat'],
    section: 'academique',
    children: [
      { label: 'Devoirs', path: '/elearning/devoirs', roles: [...ADMIN_ROLES, 'enseignant', 'secretariat'] },
      { label: 'Quiz', path: '/elearning/quiz', roles: [...ADMIN_ROLES, 'enseignant'] },
    ],
  },
  {
    label: 'Emploi du temps',
    path: '/emploi/temps',
    icon: 'emploi',
    roles: [...ADMIN_ROLES, 'enseignant'],
    section: 'academique',
    children: [
      { label: 'Enseignants', path: '/emploi/enseignants', roles: [...ADMIN_ROLES, 'enseignant'] },
      { label: 'Emploi du temps', path: '/emploi/temps', roles: [...ADMIN_ROLES, 'enseignant'] },
      { label: 'Affectations', path: '/emploi/affectations', roles: ADMIN_ROLES },
      { label: 'Salles', path: '/emploi/salles', roles: [...ADMIN_ROLES, 'enseignant'] },
    ],
  },
  {
    label: 'Finance',
    path: '/finance/frais',
    icon: 'finance',
    roles: [...ADMIN_ROLES, 'agent_comptable'],
    section: 'finance',
    children: [
      { label: 'Frais scolaires', path: '/finance/frais', roles: [...ADMIN_ROLES, 'agent_comptable'] },
      { label: 'Encaissement', path: '/finance/encaissement', roles: [...ADMIN_ROLES, 'agent_comptable'] },
      { label: 'Recouvrement', path: '/finance/recouvrement', roles: [...ADMIN_ROLES, 'agent_comptable', 'secretariat'] },
      { label: 'Arriérés', path: '/finance/arrieres', roles: [...ADMIN_ROLES, 'agent_comptable'] },
      { label: 'Mobile Money', path: '/finance/mobile-money', roles: [...ADMIN_ROLES, 'agent_comptable'] },
      { label: 'Reçus', path: '/finance/recus', roles: [...ADMIN_ROLES, 'agent_comptable'] },
      { label: 'Plan SYSCOHADA', path: '/finance/syscohada', roles: [...ADMIN_ROLES, 'agent_comptable'] },
      { label: 'Écritures', path: '/finance/ecritures', roles: [...ADMIN_ROLES, 'agent_comptable'] },
      { label: 'Paie', path: '/finance/paie', roles: [...ADMIN_ROLES, 'agent_comptable'] },
    ],
  },
  {
    label: 'Absences & Discipline',
    path: '/absences',
    icon: 'absences',
    roles: [...ADMIN_ROLES, 'enseignant', 'secretariat', 'surveillant'],
    section: 'administration',
    children: [
      { label: 'Absences', path: '/absences', roles: [...ADMIN_ROLES, 'enseignant', 'secretariat', 'surveillant'] },
      { label: 'Appel mobile', path: '/absences/appel', roles: [...ADMIN_ROLES, 'enseignant', 'secretariat', 'surveillant'] },
      { label: 'Discipline', path: '/absences/discipline', roles: [...ADMIN_ROLES, 'enseignant', 'secretariat', 'surveillant'] },
    ],
  },
  {
    label: 'Vie scolaire',
    path: '/vie-scolaire/cantine',
    icon: 'viesco',
    roles: [...ADMIN_ROLES, 'secretariat'],
    section: 'vie_scolaire',
    children: [
      { label: 'Cantine', path: '/vie-scolaire/cantine', roles: [...ADMIN_ROLES, 'secretariat'] },
      { label: 'Transport', path: '/vie-scolaire/transport', roles: [...ADMIN_ROLES, 'secretariat'] },
      { label: 'Internat', path: '/vie-scolaire/internat', roles: [...ADMIN_ROLES, 'secretariat'] },
      { label: 'Infirmerie', path: '/vie-scolaire/infirmerie', roles: [...ADMIN_ROLES, 'secretariat'] },
      { label: 'Bibliothèque', path: '/vie-scolaire/bibliotheque', roles: [...ADMIN_ROLES, 'secretariat', 'enseignant'] },
    ],
  },
  {
    label: 'Accueil',
    path: '/front-office/visiteurs',
    icon: 'frontoffice',
    roles: [...ADMIN_ROLES, 'secretariat', 'surveillant'],
    section: 'vie_scolaire',
    children: [
      { label: 'Visiteurs', path: '/front-office/visiteurs', roles: [...ADMIN_ROLES, 'secretariat', 'surveillant'] },
      { label: 'Sorties élèves', path: '/front-office/sorties', roles: [...ADMIN_ROLES, 'secretariat', 'surveillant'] },
    ],
  },
  {
    label: 'RH',
    path: '/rh/contrats',
    icon: 'rh',
    roles: ADMIN_ROLES,
    section: 'administration',
    children: [
      { label: 'Contrats', path: '/rh/contrats', roles: ADMIN_ROLES },
      { label: 'Congés', path: '/rh/conges', roles: ADMIN_ROLES },
    ],
  },
  {
    label: 'Inventaire',
    path: '/inventaire',
    icon: 'inventaire',
    roles: [...ADMIN_ROLES, 'secretariat'],
    section: 'administration',
  },
  {
    label: 'Documents',
    path: '/documents',
    icon: 'documents',
    roles: [...ADMIN_ROLES, 'secretariat'],
    section: 'administration',
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
    section: 'administration',
  },
  {
    label: 'Configuration',
    path: '/config/etablissement',
    icon: 'config',
    roles: ADMIN_ROLES,
    section: 'config',
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
      { label: 'Types d’évaluation', path: '/config/types-evaluation', roles: ADMIN_ROLES },
      { label: 'Règles de notation', path: '/config/regles-notation', roles: ADMIN_ROLES },
      { label: 'Utilisateurs', path: '/config/utilisateurs', roles: ADMIN_ROLES },
      { label: 'Journal audit', path: '/config/audit', roles: ADMIN_ROLES },
    ],
  },
];

const SECTION_LABELS = {
  plateforme: 'Plateforme',
  principal: 'Principal',
  academique: 'Académique',
  finance: 'Finance',
  administration: 'Administration',
  vie_scolaire: 'Vie scolaire',
  config: 'Paramètres',
  parent: 'Mon espace',
  eleve: 'Espace élève',
};

const SECTION_ORDER = [
  'plateforme',
  'parent',
  'eleve',
  'principal',
  'academique',
  'finance',
  'vie_scolaire',
  'administration',
  'config',
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
    ? 'bg-blanc/10 text-blanc shadow-sm ring-1 ring-inset ring-blanc/10'
    : 'text-blanc/65 hover:bg-blanc/[0.06] hover:text-blanc';

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
      <div className="space-y-0.5">
        <Link
          to={item.path}
          onClick={onNavigate}
          className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150 ${linkClass} ${
            isActive ? '[&_svg]:text-or-cachet' : ''
          }`}
        >
          <NavIcon name={item.icon} />
          {!collapsed && <span className="truncate">{item.label}</span>}
        </Link>
        {!collapsed && isActive && (
          <div className="ml-4 space-y-0.5 border-l border-blanc/10 pl-3">
            {item.children.filter(childVisible).map((child) => {
              const childActive =
                location.pathname === child.path ||
                location.pathname.startsWith(`${child.path}/`);
              return (
                <Link
                  key={child.path}
                  to={child.path}
                  onClick={onNavigate}
                  className={`block rounded-md px-2.5 py-1.5 text-xs transition-colors ${
                    childActive
                      ? 'font-semibold text-or-cachet'
                      : 'text-blanc/50 hover:text-blanc/90'
                  }`}
                >
                  {child.label}
                </Link>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  return (
    <Link
      to={item.path}
      onClick={onNavigate}
      className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150 ${linkClass} ${
        isActive ? '[&_svg]:text-or-cachet' : ''
      }`}
    >
      <NavIcon name={item.icon} />
      {!collapsed && <span className="truncate">{item.label}</span>}
    </Link>
  );
}

function groupBySection(items) {
  const groups = {};
  for (const item of items) {
    const key = item.section || 'principal';
    if (!groups[key]) groups[key] = [];
    groups[key].push(item);
  }
  return SECTION_ORDER.filter((k) => groups[k]?.length).map((k) => ({
    key: k,
    label: SECTION_LABELS[k],
    items: groups[k],
  }));
}

export default function Sidebar({ collapsed, mobileOpen, onCloseMobile }) {
  const user = useAuthStore((s) => s.user);
  const currentSchool = useAuthStore((s) => s.currentSchool);
  const actingSchoolId = useAuthStore((s) => s.actingSchoolId);
  const role = user?.role;
  const visibleItems = menuItems.filter((item) => {
    if (!role) return false;
    if (item.roles.includes(role)) return true;
    if (role === 'super_admin' && actingSchoolId) {
      return item.roles.some((r) => ADMIN_ROLES.includes(r));
    }
    return false;
  });
  const sections = groupBySection(visibleItems);
  const schoolLabel =
    currentSchool?.name || currentSchool?.nom || currentSchool?.code || null;

  return (
    <aside
      className={`sidebar-premium fixed inset-y-0 left-0 z-50 flex w-[16.5rem] transform flex-col transition-transform duration-300 ease-out lg:static lg:translate-x-0 ${
        mobileOpen ? 'translate-x-0' : '-translate-x-full'
      } ${collapsed ? 'lg:w-[4.5rem]' : 'lg:w-[16.5rem]'}`}
      style={{ boxShadow: '4px 0 24px rgba(6, 21, 37, 0.18)' }}
    >
      <div
        className={`flex items-center border-b border-blanc/[0.08] px-4 py-4 ${
          collapsed ? 'justify-center' : 'gap-3'
        }`}
      >
        <SealMedallion size="md" />
        {!collapsed && (
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-[0.9375rem] font-semibold tracking-tight text-blanc">
              Gestion Scolaire
            </h1>
            <p className="truncate text-[11px] text-blanc/45">
              {schoolLabel || role?.replace('_', ' ') || 'Établissement'}
            </p>
          </div>
        )}
        {mobileOpen && (
          <button
            type="button"
            onClick={onCloseMobile}
            className="rounded-input p-2 text-blanc/60 transition-colors hover:bg-blanc/10 hover:text-blanc lg:hidden"
            aria-label="Fermer le menu"
          >
            <X className="h-5 w-5" strokeWidth={1.75} />
          </button>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto px-2.5 py-3" aria-label="Navigation principale">
        {sections.map((section) => (
          <div key={section.key}>
            {!collapsed && section.label && (
              <p className="sidebar-section-label">{section.label}</p>
            )}
            {collapsed && <div className="my-2 border-t border-blanc/[0.06] first:hidden" />}
            <div className="space-y-0.5">
              {section.items.map((item) => (
                <NavItem
                  key={`${item.path}-${item.label}`}
                  item={item}
                  collapsed={collapsed}
                  onNavigate={onCloseMobile}
                  role={role}
                />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {!collapsed && user && (
        <div className="border-t border-blanc/[0.08] px-4 py-3">
          <p className="truncate text-xs font-medium text-blanc/80">
            {user.prenom} {user.nom}
          </p>
          <p className="truncate text-[11px] capitalize text-blanc/40">
            {user.role?.replace('_', ' ')}
          </p>
        </div>
      )}
    </aside>
  );
}
