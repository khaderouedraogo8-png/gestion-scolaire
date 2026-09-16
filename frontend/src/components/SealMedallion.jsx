const SIZES = {
  sm: { outer: 'h-7 w-7', text: 'text-[10px]' },
  md: { outer: 'h-9 w-9', text: 'text-xs' },
  lg: { outer: 'h-14 w-14', text: 'text-base' },
};

/** Marque sobre — initiales GS, sans médaillon doré. */
export default function SealMedallion({ size = 'md', className = '' }) {
  const s = SIZES[size] || SIZES.md;

  return (
    <div
      className={`relative flex shrink-0 items-center justify-center rounded-xl bg-or-cachet font-display font-semibold tracking-tight text-blanc ${s.outer} ${s.text} ${className}`}
      aria-hidden="true"
    >
      GS
    </div>
  );
}
