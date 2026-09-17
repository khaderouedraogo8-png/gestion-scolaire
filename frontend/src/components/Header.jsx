import { Bell, LogOut, Menu, PanelLeftClose, PanelLeftOpen, X } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

const ROLE_LABELS = {
  administrateur: 'Administrateur',
  directeur: 'Directeur',
  secretariat: 'Secrétariat',
  agent_comptable: 'Comptable',
  enseignant: 'Enseignant',
  surveillant: 'Surveillant',
  parent: 'Parent',
  eleve: 'Élève',
  super_admin: 'Super admin',
};

export default function Header({
  onMenuClick,
  mobileMenuOpen,
  sidebarCollapsed,
  onToggleSidebar,
}) {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const currentSchool = useAuthStore((s) => s.currentSchool);
  const actingSchoolId = useAuthStore((s) => s.actingSchoolId);
  const logout = useAuthStore((s) => s.logout);
  const exitSchoolContext = useAuthStore((s) => s.exitSchoolContext);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleExitContext = async () => {
    try {
      await exitSchoolContext();
      navigate('/platform/schools');
    } catch {
      /* ignore */
    }
  };

  const initials = user
    ? `${user.prenom?.[0] || ''}${user.nom?.[0] || ''}`.toUpperCase() || 'U'
    : 'U';

  const schoolLabel =
    currentSchool?.name || currentSchool?.nom || currentSchool?.code || null;

  const roleLabel = ROLE_LABELS[user?.role] || user?.role?.replace('_', ' ');

  const notifPath =
    user?.role === 'parent' ? '/parent/notifications' : '/notifications';
  const showNotif =
    user?.role &&
    ['parent', 'administrateur', 'directeur', 'secretariat'].includes(user.role);

  return (
    <header className="header-premium sticky top-0 z-30 flex h-14 items-center justify-between gap-3 px-4 lg:h-[3.75rem] lg:px-6">
      <div className="flex min-w-0 items-center gap-1.5">
        <button
          type="button"
          onClick={onMenuClick}
          className="rounded-input p-2 text-texte-secondaire transition-colors hover:bg-craie hover:text-encre lg:hidden"
          aria-label={mobileMenuOpen ? 'Fermer le menu' : 'Ouvrir le menu'}
          aria-expanded={mobileMenuOpen}
        >
          {mobileMenuOpen ? (
            <X className="h-5 w-5" strokeWidth={1.75} />
          ) : (
            <Menu className="h-5 w-5" strokeWidth={1.75} />
          )}
        </button>
        <button
          type="button"
          onClick={onToggleSidebar}
          className="hidden rounded-input p-2 text-texte-secondaire transition-colors hover:bg-craie hover:text-encre lg:inline-flex"
          aria-label={sidebarCollapsed ? 'Déplier le menu' : 'Réduire le menu'}
        >
          {sidebarCollapsed ? (
            <PanelLeftOpen className="h-5 w-5" strokeWidth={1.75} />
          ) : (
            <PanelLeftClose className="h-5 w-5" strokeWidth={1.75} />
          )}
        </button>
        {schoolLabel && (
          <div className="hidden min-w-0 items-center gap-2 truncate rounded-lg border border-bordure bg-craie/60 px-3 py-1.5 sm:flex">
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-feuille" aria-hidden="true" />
            <span className="truncate text-xs font-medium text-encre">{schoolLabel}</span>
            {actingSchoolId && (
              <span className="shrink-0 text-[10px] font-medium uppercase tracking-wide text-or-cachet">
                plateforme
              </span>
            )}
          </div>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
        {actingSchoolId && (
          <button
            type="button"
            onClick={handleExitContext}
            className="btn-secondary hidden px-3 py-1.5 text-xs sm:inline-flex"
          >
            Quitter l&apos;école
          </button>
        )}
        {showNotif && (
          <Link
            to={notifPath}
            className="rounded-input p-2 text-texte-secondaire transition-colors hover:bg-craie hover:text-encre"
            aria-label="Notifications"
          >
            <Bell className="h-5 w-5" strokeWidth={1.75} />
          </Link>
        )}
        <div className="hidden items-center gap-2.5 rounded-lg border border-bordure bg-blanc px-2.5 py-1 sm:flex">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-full bg-encre text-xs font-semibold text-blanc"
            aria-hidden="true"
          >
            {initials}
          </div>
          <div className="min-w-0 text-left">
            <p className="truncate text-sm font-medium leading-tight text-encre">
              {user?.prenom} {user?.nom}
            </p>
            <p className="truncate text-[11px] text-texte-secondaire">{roleLabel}</p>
          </div>
        </div>
        <div
          className="flex h-8 w-8 items-center justify-center rounded-full bg-encre text-xs font-semibold text-blanc sm:hidden"
          aria-hidden="true"
        >
          {initials}
        </div>
        <button
          type="button"
          onClick={handleLogout}
          className="btn-ghost px-2.5 py-2 text-xs"
          aria-label="Déconnexion"
        >
          <LogOut className="h-4 w-4" strokeWidth={1.75} />
          <span className="hidden sm:inline">Déconnexion</span>
        </button>
      </div>
    </header>
  );
}
