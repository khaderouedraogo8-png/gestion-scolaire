const CYCLE_LABELS = {
  premier: 'Premier cycle',
  second: 'Second cycle',
};

export function cycleLabel(cycle) {
  return CYCLE_LABELS[cycle] || cycle;
}

export function toClassSlug(libelle) {
  return libelle
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

export function findClassBySlug(classes, slug) {
  return (classes || []).find((c) => toClassSlug(c.libelle) === slug);
}
