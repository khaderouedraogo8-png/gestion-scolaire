/** Affichage minimal des rulesets utilisés sur un bulletin (PR #13). */

export function formatBulletinRulesets(snapshot) {
  if (!Array.isArray(snapshot) || snapshot.length === 0) {
    return { label: 'Legacy', title: 'Calcul legacy (sans ruleset actif)' };
  }
  const labels = snapshot
    .map((s) => (s?.code ? `${s.code} v${s.version ?? '?'}` : null))
    .filter(Boolean);
  if (!labels.length) {
    return { label: 'Legacy', title: 'Calcul legacy (sans ruleset actif)' };
  }
  const shown = labels.slice(0, 2).join(', ');
  const extra = labels.length > 2 ? ` +${labels.length - 2}` : '';
  return { label: `${shown}${extra}`, title: labels.join(', ') };
}
