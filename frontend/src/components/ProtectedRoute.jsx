import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

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
      <div className="flex min-h-[40vh] flex-col items-center justify-center gap-2 p-6 text-center">
        <p className="text-lg font-semibold text-encre">Accès non autorisé</p>
        <p className="page-subtitle">
          Votre rôle ({user.role}) ne permet pas d'accéder à cette page.
        </p>
      </div>
    );
  }

  return children;
}
