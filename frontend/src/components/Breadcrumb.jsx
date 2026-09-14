import { Link } from 'react-router-dom';

export default function Breadcrumb({ items = [] }) {
  if (!items.length) return null;

  return (
    <nav
      aria-label="Fil d'Ariane"
      className="mb-2 flex flex-wrap items-center gap-y-1 text-[13px] text-texte-secondaire"
    >
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        return (
          <span key={`${item.label}-${index}`} className="inline-flex items-center">
            {index > 0 && (
              <span className="mx-2 text-bordure" aria-hidden="true">
                /
              </span>
            )}
            {item.to && !isLast ? (
              <Link
                to={item.to}
                className="rounded-badge px-1 py-0.5 text-or-cachet transition-colors hover:bg-or-cachet-clair"
              >
                {item.label}
              </Link>
            ) : (
              <span className={isLast ? 'px-1 font-medium text-encre' : 'px-1'}>{item.label}</span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
