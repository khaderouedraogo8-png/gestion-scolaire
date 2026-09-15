/**
 * Libellés UI pour les Rulesets de notation (Step 5).
 * Les valeurs API restent exactement celles du backend (minuscules).
 * Aucune logique de calcul de moyenne ici — affichage / validation formulaire uniquement.
 */

export const RULESET_STATUS = Object.freeze({
  DRAFT: 'draft',
  ACTIVE: 'active',
  ARCHIVED: 'archived',
})

export const RULESET_STATUS_OPTIONS = [
  { value: '', label: 'Tous les statuts' },
  { value: 'draft', label: 'Brouillon' },
  { value: 'active', label: 'Actif' },
  { value: 'archived', label: 'Archivé' },
]

export const ROUNDING_MODE_OPTIONS = [
  {
    value: 'half_up',
    label: 'HALF_UP — arrondi classique',
    description: '0.5 s\'arrondit vers le haut (ex. 12.5 → 13 à 0 décimale).',
  },
  {
    value: 'half_even',
    label: 'HALF_EVEN — arrondi banquier',
    description: '0.5 s\'arrondit vers le chiffre pair le plus proche.',
  },
  {
    value: 'down',
    label: 'DOWN — vers zéro',
    description: 'Troncature vers zéro.',
  },
  {
    value: 'up',
    label: 'UP — loin de zéro',
    description: 'Éloignement de zéro.',
  },
]

export const EVALUATION_CONTEXT_OPTIONS = [
  { value: 'normal', label: 'Normal' },
  { value: 'examen_blanc', label: 'Examen blanc' },
  { value: 'rattrapage', label: 'Rattrapage' },
  { value: 'session_2', label: 'Session 2' },
]

/**
 * Politique moteur Step 4 (lecture seule) — pas de champ API manquant.
 * Distingue clairement missing ≠ zero.
 */
export const ENGINE_MISSING_POLICY_INFO = [
  {
    id: 'required_missing',
    name: 'Composante obligatoire manquante',
    effect: 'Résultat incomplet — aucune moyenne inventée',
    description:
      'Si une composante obligatoire (is_required) n\'a pas de note, le moteur ne calcule pas la moyenne. La note manquante n\'est jamais affichée ni traitée comme 0.',
  },
  {
    id: 'optional_missing',
    name: 'Composante optionnelle manquante',
    effect: 'Renormalisation sur les poids présents',
    description:
      'Les composantes optionnelles sans note sont exclues ; les poids des notes présentes sont renormalisés pour totaliser 100 %. Ce n\'est pas un ZERO silencieux.',
  },
  {
    id: 'explicit_zero',
    name: 'Note explicite = 0',
    effect: 'Compte dans le calcul',
    description:
      'Une note saisie à 0 est une vraie note. Elle est distincte de l\'absence de note (missing). L\'UI doit afficher « — » pour missing et « 0 » pour zéro explicite.',
  },
]

export function rulesetStatusLabel(status) {
  const map = { draft: 'Brouillon', active: 'Actif', archived: 'Archivé' }
  return map[status] || status || '—'
}

export function rulesetStatusBadgeVariant(status) {
  if (status === 'active') return 'success'
  if (status === 'draft') return 'warning'
  if (status === 'archived') return 'neutral'
  return 'neutral'
}

export function roundingModeLabel(mode) {
  return ROUNDING_MODE_OPTIONS.find((o) => o.value === mode)?.label || mode || '—'
}

export function evaluationContextLabel(ctx) {
  return EVALUATION_CONTEXT_OPTIONS.find((o) => o.value === ctx)?.label || ctx || '—'
}

/** Somme des poids (affichage / feedback formulaire uniquement). */
export function sumWeights(components) {
  if (!Array.isArray(components) || !components.length) return 0
  return components.reduce((acc, c) => acc + (Number(c.weight) || 0), 0)
}

export function weightsAreValid(components) {
  if (!Array.isArray(components) || !components.length) return false
  const total = sumWeights(components)
  return Math.abs(total - 100) < 0.005
}

export function formatWeight(w) {
  if (w === null || w === undefined || w === '') return '—'
  const n = Number(w)
  if (Number.isNaN(n)) return '—'
  return `${n.toFixed(2)} %`
}

export function formatScaleMax(scaleMax) {
  if (scaleMax === null || scaleMax === undefined || scaleMax === '') return '—'
  const n = Number(scaleMax)
  if (Number.isNaN(n)) return '—'
  return `Note maximale : ${n}`
}
