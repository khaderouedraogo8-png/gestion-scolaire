/**
 * Libellés structure académique — alignés sur les choix backend
 * (PROGRAM_TYPE_CHOICES / PERIOD_TYPE_CHOICES).
 * Architecture extensible : ajouter une entrée ici quand le backend en accepte une nouvelle.
 */

export const PROGRAM_CODE_GENERAL = 'GENERAL';

export const PROGRAM_TYPE_OPTIONS = [
  { value: 'general', label: 'Général' },
  { value: 'technique', label: 'Technique' },
  { value: 'professionnel', label: 'Professionnel' },
  { value: 'custom', label: 'Personnalisé' },
];

export const PERIOD_TYPE_OPTIONS = [
  { value: 'trimestre', label: 'Trimestre' },
  { value: 'semestre', label: 'Semestre' },
  { value: 'custom', label: 'Personnalisée' },
  { value: 'annuel', label: 'Annuelle' },
];

export const ACTIVE_FILTER_OPTIONS = [
  { value: '', label: 'Tous les statuts' },
  { value: 'true', label: 'Actifs' },
  { value: 'false', label: 'Inactifs' },
];

export function programTypeLabel(value) {
  if (!value) return '—';
  const found = PROGRAM_TYPE_OPTIONS.find((o) => o.value === value);
  return found ? found.label : String(value);
}

export function periodTypeLabel(value) {
  if (!value) return '—';
  const found = PERIOD_TYPE_OPTIONS.find((o) => o.value === value);
  return found ? found.label : String(value);
}

export function isGeneralProgram(program) {
  return Boolean(program && String(program.code || '').toUpperCase() === PROGRAM_CODE_GENERAL);
}

export function programShortName(program) {
  if (!program) return '';
  return program.name || program.code || '';
}

export function formatNiveauWithProgram(niveau, programById) {
  const libelle = niveau?.libelle || niveau?.nom || '—';
  const program =
    niveau?.program ||
    (programById && niveau?.id_program ? programById[String(niveau.id_program)] : null);
  const progName = programShortName(program);
  if (!progName) return libelle;
  return `${libelle} · ${progName}`;
}

export function apiErrorMessage(err, fallback = 'Une erreur est survenue') {
  if (!err) return fallback;
  if (!err.response) {
    return 'Erreur réseau. Vérifiez votre connexion puis réessayez.';
  }
  const status = err.response.status;
  const data = err.response.data || {};
  const msg =
    data.message ||
    data.error ||
    (Array.isArray(data.errors) ? data.errors[0] : null) ||
    (typeof data.detail === 'string' ? data.detail : null);

  if (status === 403) return msg || 'Accès non autorisé pour cette action.';
  if (status === 404) return msg || 'Ressource introuvable.';
  if (status === 409) return msg || 'Conflit : cette ressource existe déjà ou est protégée.';
  if (status === 400) return msg || 'Données invalides. Vérifiez le formulaire.';
  if (status >= 500) return msg || 'Erreur serveur. Réessayez plus tard.';
  return msg || fallback;
}

export function asList(payload) {
  if (Array.isArray(payload)) return payload;
  if (payload?.items && Array.isArray(payload.items)) return payload.items;
  return [];
}
