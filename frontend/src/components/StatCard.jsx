const UNDERLINE = {
  neutral: 'bg-or-cachet',
  positive: 'bg-feuille',
  negative: 'bg-brique',
  warning: 'bg-ambre',
};

export default function StatCard({ title, value, subtitle, tone = 'neutral' }) {
  return (
    <div className="card">
      <p className="text-[11px] text-texte-secondaire">{title}</p>
      <p className="mt-1 font-display text-[26px] font-medium tabular-nums text-encre">{value ?? '—'}</p>
      <div className={`mt-2 h-0.5 w-6 ${UNDERLINE[tone] || UNDERLINE.neutral}`} />
      {subtitle && <p className="mt-2 text-xs text-texte-secondaire">{subtitle}</p>}
    </div>
  );
}
