import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Bell,
  LogOut,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  X,
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { notificationsApi } from '../services/api/notifications';

const ADMIN_NOTIF_ROLES = ['administrateur', 'directeur', 'secretariat'];

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
  const [pendingCount, setPendingCount] = useState(0);

  const canSeeNotifs = useMemo(
    () => user?.role && ADMIN_NOTIF_ROLES.includes(user.role),
    [user?.role]
  );

  useEffect(() => {
    if (!canSeeNotifs) return undefined;
    let cancelled = false;
    notificationsApi
      .list({ statut: 'en_attente', per_page: 50 })
      .then((data) => {
        if (cancelled) return;
        const items = Array.isArray(data) ? data : data?.items || [];
        const total = data?.total ?? items.length;
        setPendingCount(Number(total) || 0);
      })
      .catch(() => {
        if (!cancelled) setPendingCount(0);
      });
    return () => {
      cancelled = true;
    };
  }, [canSeeNotifs]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleSearch = (e) => {
    e.preventDefault();
    const q = search.trim();
    if (!q) {
      navigate('/eleves/recherche');
      return;
    }
    navigate(`/eleves/recherche?q=${encodeURIComponent(q)}`);
  };

  const initials = user
    ? `${user.prenom?.[0] || ''}${user.nom?.[0] || ''}`.toUpperCase() || 'U'
    : 'U';

  return (
    <header className="header-premium sticky top-0 z-30 flex h-[4.25rem] items-center justify-between gap-3 px-4 lg:px-8">
      <div className="flex min-w-0 flex-1 items-center gap-2">
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

        {user?.role !== 'parent' && (
          <form
            onSubmit={handleSearch}
            className="relative ml-1 hidden min-w-0 flex-1 md:block md:max-w-md"
          >
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

      <div className="flex shrink-0 items-center gap-1.5 sm:gap-2.5">
        {user?.role !== 'parent' && (
          <Link
            to="/eleves/recherche"
            className="rounded-input p-2.5 text-texte-secondaire transition-colors hover:bg-or-cachet-clair hover:text-encre md:hidden"
            aria-label="Rechercher un élève"
          >
            <Search className="h-5 w-5" strokeWidth={1.75} />
          </Link>
        )}

        {canSeeNotifs && (
          <Link
            to="/notifications"
            className="relative rounded-input p-2.5 text-texte-secondaire transition-colors hover:bg-or-cachet-clair hover:text-encre"
            aria-label={
              pendingCount > 0
                ? `Notifications, ${pendingCount} en attente`
                : 'Notifications'
            }
          >
            <Bell className="h-5 w-5" strokeWidth={1.75} />
            {pendingCount > 0 && (
              <span className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-brique px-1 text-[10px] font-medium text-blanc">
                {pendingCount > 99 ? '99+' : pendingCount}
              </span>
            )}
          </Link>
        )}

        <div className="hidden items-center gap-3 rounded-card border border-bordure/60 bg-blanc/80 px-3 py-1.5 shadow-card sm:flex">
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
