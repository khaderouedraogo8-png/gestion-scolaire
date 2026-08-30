import { Link } from 'react-router-dom';

export default function Breadcrumb({ items = [] }) {
  if (!items.length) return null;

  return (
    <nav aria-label="Fil d'Ariane" className="text-sm text-texte-secondaire">
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        return (
          <span key={`${item.label}-${index}`}>
            {index > 0 && <span className="mx-2 text-bordure">›</span>}
            {item.to && !isLast ? (
              <Link to={item.to} className="text-or-cachet hover:underline">
                {item.label}
              </Link>
            ) : (
              <span className={isLast ? 'font-medium text-encre' : ''}>{item.label}</span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
