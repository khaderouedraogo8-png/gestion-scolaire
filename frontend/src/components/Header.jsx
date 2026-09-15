import { LogOut, Menu, PanelLeftClose, PanelLeftOpen, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

export default function Header({
  onMenuClick,
  mobileMenuOpen,
  sidebarCollapsed,
  onToggleSidebar,
}) {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const initials = user
    ? `${user.prenom?.[0] || ''}${user.nom?.[0] || ''}`.toUpperCase() || 'U'
    : 'U';

  return (
    <header className="header-premium sticky top-0 z-30 flex h-[4.25rem] items-center justify-between px-4 lg:px-8">
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={onMenuClick}
          className="rounded-input p-2.5 text-texte-secondaire transition-colors hover:bg-or-cachet-clair hover:text-encre lg:hidden"
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
          className="hidden rounded-input p-2.5 text-texte-secondaire transition-colors hover:bg-or-cachet-clair hover:text-encre lg:block"
          aria-label={sidebarCollapsed ? 'Déplier le menu' : 'Réduire le menu'}
        >
          {sidebarCollapsed ? (
            <PanelLeftOpen className="h-5 w-5" strokeWidth={1.75} />
          ) : (
            <PanelLeftClose className="h-5 w-5" strokeWidth={1.75} />
          )}
        </button>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        <div className="hidden items-center gap-3 rounded-card border border-bordure/70 bg-blanc/80 px-3 py-1.5 shadow-card sm:flex">
          <div
            className="flex h-9 w-9 items-center justify-center rounded-full border border-or-cachet/30 text-sm font-medium text-or-cachet"
            style={{
              background:
                'radial-gradient(circle at 30% 25%, rgba(184,134,46,0.22), rgba(184,134,46,0.08))',
            }}
          >
            {initials}
          </div>
          <div className="text-left">
            <p className="text-sm font-medium leading-tight text-encre">
              {user?.prenom} {user?.nom}
            </p>
            <p className="text-[11px] capitalize tracking-wide text-texte-secondaire">
              {user?.role?.replace('_', ' ')}
            </p>
          </div>
        </div>
        <div
          className="flex h-9 w-9 items-center justify-center rounded-full border border-or-cachet/30 text-sm font-medium text-or-cachet sm:hidden"
          style={{
            background:
              'radial-gradient(circle at 30% 25%, rgba(184,134,46,0.22), rgba(184,134,46,0.08))',
          }}
        >
          {initials}
        </div>
        <button
          type="button"
          onClick={handleLogout}
          className="btn-secondary hidden px-3 py-2 text-xs sm:inline-flex"
        >
          <LogOut className="h-3.5 w-3.5" strokeWidth={1.75} />
          Déconnexion
        </button>
      </div>
    </header>
  );
}
