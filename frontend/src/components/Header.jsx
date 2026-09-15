import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Bell,
  LogOut,
  Menu,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Sun,
  X,
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';

const ADMIN_NOTIF_ROLES = ['administrateur', 'directeur', 'secretariat'];

/** Header aéré : recherche globale, thème, identité — première barre “SaaS premium”. */
export default function Header({
  onMenuClick,
  mobileMenuOpen,
  sidebarCollapsed,
  onToggleSidebar,
}) {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const [search, setSearch] = useState('');
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'));

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('gs-theme', dark ? 'dark' : 'light');
  }, [dark]);

  useEffect(() => {
    const saved = localStorage.getItem('gs-theme');
    if (saved === 'dark') setDark(true);
  }, []);

  const canSeeNotifs = user?.role && ADMIN_NOTIF_ROLES.includes(user.role);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleSearch = (e) => {
    e.preventDefault();
    const q = search.trim();
    navigate(q ? `/eleves/recherche?q=${encodeURIComponent(q)}` : '/eleves/recherche');
  };

  const initials = user
    ? `${user.prenom?.[0] || ''}${user.nom?.[0] || ''}`.toUpperCase() || 'U'
    : 'U';

  return (
    <header className="header-premium sticky top-0 z-30 flex h-16 items-center justify-between gap-3 px-4 lg:px-8">
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <button
          type="button"
          onClick={onMenuClick}
          className="rounded-input p-2.5 text-texte-secondaire transition-colors duration-base hover:bg-craie hover:text-encre lg:hidden"
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
          className="hidden rounded-input p-2.5 text-texte-secondaire transition-colors duration-base hover:bg-craie hover:text-encre lg:block"
          aria-label={sidebarCollapsed ? 'Déplier le menu' : 'Réduire le menu'}
        >
          {sidebarCollapsed ? (
            <PanelLeftOpen className="h-5 w-5" strokeWidth={1.75} />
          ) : (
            <PanelLeftClose className="h-5 w-5" strokeWidth={1.75} />
          )}
        </button>

        {user?.role !== 'parent' && (
          <form onSubmit={handleSearch} className="relative ml-1 hidden min-w-0 flex-1 md:block md:max-w-md">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-texte-secondaire"
              strokeWidth={1.75}
            />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Rechercher un élève…"
              className="input !py-2 pl-9 pr-3 text-sm"
              aria-label="Recherche élève"
            />
          </form>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
        {user?.role !== 'parent' && (
          <Link
            to="/eleves/recherche"
            className="rounded-input p-2.5 text-texte-secondaire transition-colors hover:bg-craie hover:text-encre md:hidden"
            aria-label="Rechercher"
          >
            <Search className="h-5 w-5" strokeWidth={1.75} />
          </Link>
        )}

        <button
          type="button"
          onClick={() => setDark((v) => !v)}
          className="rounded-input p-2.5 text-texte-secondaire transition-colors hover:bg-craie hover:text-encre"
          aria-label={dark ? 'Mode clair' : 'Mode sombre'}
        >
          {dark ? (
            <Sun className="h-5 w-5" strokeWidth={1.75} />
          ) : (
            <Moon className="h-5 w-5" strokeWidth={1.75} />
          )}
        </button>

        {canSeeNotifs && (
          <Link
            to="/notifications"
            className="relative rounded-input p-2.5 text-texte-secondaire transition-colors hover:bg-craie hover:text-encre"
            aria-label="Notifications"
          >
            <Bell className="h-5 w-5" strokeWidth={1.75} />
            <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-brique" />
          </Link>
        )}

        <div className="hidden items-center gap-3 rounded-card border border-bordure bg-blanc px-3 py-1.5 shadow-card sm:flex">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-or-cachet-clair text-xs font-semibold text-or-cachet">
            {initials}
          </div>
          <div className="text-left">
            <p className="text-sm font-semibold leading-tight text-encre">
              {user?.prenom} {user?.nom}
            </p>
            <p className="text-2xs capitalize tracking-wide text-texte-secondaire">
              {user?.role?.replace('_', ' ')}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={handleLogout}
          className="btn-secondary hidden px-3 py-2 text-xs sm:inline-flex"
        >
          <LogOut className="h-3.5 w-3.5" strokeWidth={1.75} />
          Déconnexion
        </button>
        <button
          type="button"
          onClick={handleLogout}
          className="rounded-input p-2.5 text-texte-secondaire transition-colors hover:bg-brique-clair hover:text-brique sm:hidden"
          aria-label="Déconnexion"
        >
          <LogOut className="h-5 w-5" strokeWidth={1.75} />
        </button>
      </div>
    </header>
  );
}
