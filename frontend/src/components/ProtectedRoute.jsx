import { Navigate, useLocation, Link } from 'react-router-dom';
import { ShieldOff } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { homePathForRole } from '../utils/homePath';

export default function ProtectedRoute({ children, roles = [] }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (user?.doit_changer_mdp && location.pathname !== '/change-password') {
    return <Navigate to="/change-password" replace />;
  }

  if (roles.length > 0 && user?.role && !roles.includes(user.role)) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-6">
        <div className="state-panel" role="alert">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-brique-clair text-brique">
            <ShieldOff className="h-6 w-6" strokeWidth={1.75} aria-hidden="true" />
          </div>
          <h1 className="font-display text-lg font-semibold text-encre">Accès non autorisé</h1>
          <p className="mt-2 text-sm leading-relaxed text-texte-secondaire">
            Votre rôle ({user.role.replace('_', ' ')}) ne permet pas d&apos;accéder à cette page.
          </p>
          <Link to={homePathForRole(user.role)} className="btn-primary mt-6">
            Retour à l&apos;accueil
          </Link>
        </div>
      </div>
    );
  }

  return children;
}
