/** Affichage des moyennes académiques — missing ≠ 0 (PR14/PR15). */

export function formatMoyenneDisplay(moyenne, scaleMax = 20) {
  if (moyenne == null || Number.isNaN(Number(moyenne))) {
    return '—';
  }
  const scale =
    scaleMax != null && !Number.isNaN(Number(scaleMax)) ? Number(scaleMax) : 20;
  return `${Number(moyenne).toFixed(2)}/${scale}`;
}

export function formatResultSource(source) {
  if (source === 'rules_engine') return 'Ruleset';
  if (source === 'legacy') return 'Legacy (historique)';
  return source || '—';
}

export function formatRulesetRef(row) {
  if (!row?.ruleset_code) {
    if (row?.incomplete) return 'Incomplet';
    return '—';
  }
  const v = row.ruleset_version != null ? ` v${row.ruleset_version}` : '';
  return `${row.ruleset_code}${v}`;
}
