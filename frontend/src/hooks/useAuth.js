import { useAuthStore } from '../store/authStore';

export function useAuth() {
  const user = useAuthStore((s) => s.user);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isLoading = useAuthStore((s) => s.isLoading);
  const error = useAuthStore((s) => s.error);
  const login = useAuthStore((s) => s.login);
  const logout = useAuthStore((s) => s.logout);
  const changePassword = useAuthStore((s) => s.changePassword);
  const clearError = useAuthStore((s) => s.clearError);
  const hasRole = useAuthStore((s) => s.hasRole);
  const hasAnyRole = useAuthStore((s) => s.hasAnyRole);

  const isAdmin = hasAnyRole(['administrateur', 'directeur']);
  const isEnseignant = hasRole('enseignant');
  const isComptable = hasRole('agent_comptable');
  const isSecretariat = hasRole('secretariat');
  const isParent = hasRole('parent');

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    changePassword,
    clearError,
    hasRole,
    hasAnyRole,
    isAdmin,
    isEnseignant,
    isComptable,
    isSecretariat,
    isParent,
  };
}

export default useAuth;
