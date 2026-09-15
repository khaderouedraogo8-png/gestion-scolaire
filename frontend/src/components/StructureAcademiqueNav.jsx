import { NavLink } from 'react-router-dom';

const LINKS = [
  { to: '/etablissement/programmes', label: 'Programmes' },
  { to: '/etablissement/periodes', label: 'Périodes' },
  { to: '/etablissement/niveaux', label: 'Niveaux' },
  { to: '/etablissement/classes', label: 'Classes' },
];

export default function StructureAcademiqueNav() {
  return (
    <nav
      aria-label="Structure académique"
      className="flex flex-wrap gap-1 rounded-card border border-bordure bg-blanc p-1"
    >
      {LINKS.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          className={({ isActive }) =>
            `rounded-input px-3 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-or-cachet ${
              isActive
                ? 'bg-or-cachet-clair text-encre'
                : 'text-texte-secondaire hover:bg-craie hover:text-encre'
            }`
          }
        >
          {link.label}
        </NavLink>
      ))}
    </nav>
  );
}
