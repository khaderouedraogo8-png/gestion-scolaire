import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { homePathForRole } from '../../utils/homePath';
import Landing from './Landing';

/** `/` public : Landing si non connecté, sinon redirection rôle. */
export default function PublicHome() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const role = useAuthStore((s) => s.user?.role);

  if (isAuthenticated) {
    return <Navigate to={homePathForRole(role)} replace />;
  }

  return <Landing />;
}
