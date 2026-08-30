const ACCENT = {
  neutral: {
    iconWrap: 'bg-or-cachet-clair text-or-cachet',
    bar: 'bg-or-cachet',
  },
  positive: {
    iconWrap: 'bg-feuille-clair text-feuille',
    bar: 'bg-feuille',
  },
  negative: {
    iconWrap: 'bg-brique-clair text-brique',
    bar: 'bg-brique',
  },
  warning: {
    iconWrap: 'bg-ambre-clair text-ambre',
    bar: 'bg-ambre',
  },
};

export default function StatCard({ title, value, subtitle, tone = 'neutral', icon: Icon, delay = 0 }) {
  const accent = ACCENT[tone] || ACCENT.neutral;

  return (
    <div className="stat-card group" style={{ animationDelay: `${delay}ms` }}>
      {Icon && (
        <div className={`stat-card-icon ${accent.iconWrap}`}>
          <Icon className="h-[18px] w-[18px]" strokeWidth={1.75} aria-hidden="true" />
        </div>
      )}
      <p className="stat-card-label">{title}</p>
      <p className="stat-card-value">{value ?? '—'}</p>
      <div className={`stat-card-bar ${accent.bar}`} />
      {subtitle && <p className="stat-card-sub">{subtitle}</p>}
    </div>
  );
}
