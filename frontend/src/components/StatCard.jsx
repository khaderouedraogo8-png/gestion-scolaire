/** Mini sparkline — tendance discrète intégrée au flux (réf. Metric Flow). */
function Sparkline({ tone = 'neutral', variant = 'line', onBrand = false }) {
  const stroke = onBrand
    ? 'rgba(255,255,255,0.9)'
    : tone === 'positive'
      ? '#059669'
      : tone === 'negative'
        ? '#E11D48'
        : tone === 'warning'
          ? '#D97706'
          : '#0F766E';
  const muted = onBrand ? 'rgba(255,255,255,0.35)' : `${stroke}55`;
  const gradId = `spark-fill-${tone}-${onBrand ? 'b' : 'n'}`;

  if (variant === 'bars') {
    const heights = [40, 55, 35, 70, 50, 85, 60];
    return (
      <svg viewBox="0 0 56 28" className="h-8 w-14" aria-hidden="true">
        {heights.map((h, i) => (
          <rect
            key={i}
            x={i * 8}
            y={28 - h * 0.28}
            width="5"
            height={h * 0.28}
            rx="1.5"
            fill={i === heights.length - 1 ? stroke : muted}
          />
        ))}
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 72 28" className="h-8 w-[4.5rem]" aria-hidden="true">
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.22" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path
        d="M0 20 C8 18, 12 10, 20 12 S32 22, 40 14 S52 6, 72 8 L72 28 L0 28 Z"
        fill={`url(#${gradId})`}
      />
      <path
        d="M0 20 C8 18, 12 10, 20 12 S32 22, 40 14 S52 6, 72 8"
        fill="none"
        stroke={stroke}
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="72" cy="8" r="2.5" fill={stroke} />
    </svg>
  );
}

const ACCENT = {
  neutral: {
    iconWrap: 'bg-or-cachet-clair text-or-cachet',
    pill: 'bg-or-cachet-clair text-or-cachet',
  },
  positive: {
    iconWrap: 'bg-feuille-clair text-feuille',
    pill: 'bg-feuille-clair text-feuille',
  },
  negative: {
    iconWrap: 'bg-brique-clair text-brique',
    pill: 'bg-brique-clair text-brique',
  },
  warning: {
    iconWrap: 'bg-ambre-clair text-ambre',
    pill: 'bg-ambre-clair text-ambre',
  },
};

/**
 * KPI premium : label discret → valeur dominante → trend pill + sparkline.
 * Choix : hiérarchie Metric Flow, accent sémantique uniquement sur le pill.
 */
export default function StatCard({
  title,
  value,
  subtitle,
  change,
  tone = 'neutral',
  icon: Icon,
  delay = 0,
  featured = false,
  sparkVariant = 'line',
}) {
  const accent = ACCENT[tone] || ACCENT.neutral;

  return (
    <div
      className={`stat-card group ${featured ? 'stat-card-featured' : ''}`}
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="stat-card-label">{title}</p>
        {Icon && (
          <div className={`stat-card-icon ${featured ? 'bg-blanc/20 text-blanc' : accent.iconWrap}`}>
            <Icon className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" />
          </div>
        )}
      </div>

      <p className="stat-card-value">{value ?? '—'}</p>

      <div className="mt-auto flex items-end justify-between gap-3 pt-4">
        <div className="min-w-0">
          {change != null && change !== '' && (
            <span className={`stat-card-pill ${featured ? 'bg-blanc/20 text-blanc' : accent.pill}`}>
              {change}
            </span>
          )}
          {subtitle && <p className="stat-card-sub truncate">{subtitle}</p>}
        </div>
        <Sparkline tone={tone} variant={sparkVariant} onBrand={featured} />
      </div>
    </div>
  );
}
