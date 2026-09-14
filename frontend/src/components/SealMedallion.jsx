const SIZES = {
  sm: { outer: 'h-7 w-7', text: 'text-[10px]' },
  md: { outer: 'h-9 w-9', text: 'text-xs' },
  lg: { outer: 'h-14 w-14', text: 'text-base' },
};

/** Marque compacte : pastille brand, plus de sceau doré baroque. */
export default function SealMedallion({ size = 'md', className = '' }) {
  const s = SIZES[size] || SIZES.md;

  return (
    <div
      className={`relative flex shrink-0 items-center justify-center rounded-full bg-or-cachet-clair font-display font-semibold text-or-cachet ring-1 ring-or-cachet/25 ${s.outer} ${s.text} ${className}`}
      aria-hidden="true"
    >
      <span className="relative z-10 tracking-tight">GS</span>
    </div>
  );
}
