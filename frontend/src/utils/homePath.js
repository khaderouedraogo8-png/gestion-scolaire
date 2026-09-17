/** Redirection post-auth selon le rôle (espaces métier). */
const DASHBOARD_ROLES = [
  'administrateur',
  'directeur',
  'agent_comptable',
  'secretariat',
  'enseignant',
  'surveillant',
  'super_admin',
];

export function homePathForRole(role) {
  if (role === 'super_admin') return '/platform/schools';
  if (role === 'parent') return '/parent';
  if (role === 'eleve') return '/eleve';
  if (role === 'enseignant') return '/dashboard';
  if (role === 'surveillant') return '/dashboard';
  if (role && DASHBOARD_ROLES.includes(role)) return '/dashboard';
  return '/classes';
}
