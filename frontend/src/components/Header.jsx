import { Menu, PanelLeftClose } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

export default function Header({ onMenuClick, sidebarCollapsed, onToggleSidebar }) {
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
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-bordure bg-blanc px-4 lg:px-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onMenuClick}
          className="rounded-input p-2 text-texte-secondaire hover:bg-or-cachet-clair lg:hidden"
          aria-label="Ouvrir le menu"
        >
          <Menu className="h-6 w-6" strokeWidth={1.75} />
        </button>
        <button
          type="button"
          onClick={onToggleSidebar}
          className="hidden rounded-input p-2 text-texte-secondaire hover:bg-or-cachet-clair lg:block"
          aria-label="Réduire le menu"
        >
          <PanelLeftClose className="h-5 w-5" strokeWidth={1.75} />
        </button>
      </div>

      <div className="flex items-center gap-4">
        <div className="hidden text-right sm:block">
          <p className="text-sm font-medium text-encre">
            {user?.prenom} {user?.nom}
          </p>
          <p className="text-xs capitalize text-texte-secondaire">{user?.role?.replace('_', ' ')}</p>
        </div>
        <div className="flex h-9 w-9 items-center justify-center rounded-full border border-or-cachet bg-or-cachet-clair text-sm font-medium text-or-cachet">
          {initials}
        </div>
        <button type="button" onClick={handleLogout} className="btn-ghost text-sm">
          Déconnexion
        </button>
      </div>
    </header>
  );
}
