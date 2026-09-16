/** Affichage minimal des rulesets utilisés sur un bulletin (PR #13 / PR15-C). */

export function formatBulletinRulesets(snapshot) {
  if (!Array.isArray(snapshot) || snapshot.length === 0) {
    return {
      label: 'Sans ruleset',
      title: 'Aucun ruleset actif sur les matières (résultats incomplets ou absents)',
    };
  }
  const labels = snapshot
    .map((s) => (s?.code ? `${s.code} v${s.version ?? '?'}` : null))
    .filter(Boolean);
  if (!labels.length) {
    return {
      label: 'Sans ruleset',
      title: 'Aucun ruleset actif sur les matières (résultats incomplets ou absents)',
    };
  }
  const shown = labels.slice(0, 2).join(', ');
  const extra = labels.length > 2 ? ` +${labels.length - 2}` : '';
  return { label: `${shown}${extra}`, title: labels.join(', ') };
}
