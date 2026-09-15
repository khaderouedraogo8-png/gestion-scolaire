/** Affichage des moyennes académiques — missing ≠ 0 (PR14). */

export function formatMoyenneDisplay(moyenne) {
  if (moyenne == null || Number.isNaN(Number(moyenne))) {
    return '—';
  }
  return `${Number(moyenne).toFixed(2)}/20`;
}

export function formatResultSource(source) {
  if (source === 'rules_engine') return 'Ruleset';
  if (source === 'legacy') return 'Legacy';
  return source || '—';
}

export function formatRulesetRef(row) {
  if (!row?.ruleset_code) return '—';
  const v = row.ruleset_version != null ? ` v${row.ruleset_version}` : '';
  return `${row.ruleset_code}${v}`;
}
