/** Mini sparkline décorative — suggère la tendance sans chart lib. */
function Sparkline({ tone = 'neutral' }) {
  const stroke =
    tone === 'positive' ? '#059669' : tone === 'negative' ? '#E11D48' : tone === 'warning' ? '#D97706' : '#0F766E';
  return (
    <svg viewBox="0 0 64 24" className="h-7 w-14 opacity-80" aria-hidden="true">
      <path
        d="M1 18 C10 16, 14 8, 22 10 S34 20, 42 12 S54 4, 63 6"
        fill="none"
        stroke={stroke}
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  );
}

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

/** KPI card : chiffre dominant, accent sémantique, sparkline discrète. */
export default function StatCard({ title, value, subtitle, tone = 'neutral', icon: Icon, delay = 0 }) {
  const accent = ACCENT[tone] || ACCENT.neutral;

  return (
    <div className="stat-card group" style={{ animationDelay: `${delay}ms` }}>
      <div className="flex items-start justify-between gap-3">
        {Icon && (
          <div className={`stat-card-icon ${accent.iconWrap}`}>
            <Icon className="h-[18px] w-[18px]" strokeWidth={1.75} aria-hidden="true" />
          </div>
        )}
        <Sparkline tone={tone} />
      </div>
      <p className="stat-card-label">{title}</p>
      <p className="stat-card-value">{value ?? '—'}</p>
      <div className={`stat-card-bar ${accent.bar}`} />
      {subtitle && <p className="stat-card-sub">{subtitle}</p>}
    </div>
  );
}
