const SIZES = {
  sm: { outer: 'h-7 w-7', text: 'text-[10px]', border: 'border-[1.5px]' },
  md: { outer: 'h-10 w-10', text: 'text-xs', border: 'border-[1.5px]' },
  lg: { outer: 'h-16 w-16', text: 'text-lg', border: 'border-2' },
};

export default function SealMedallion({ size = 'md', className = '' }) {
  const s = SIZES[size] || SIZES.md;

  return (
    <div
      className={`flex shrink-0 items-center justify-center rounded-full border-or-cachet bg-transparent font-display font-medium text-or-cachet ${s.outer} ${s.text} ${s.border} ${className}`}
      aria-hidden="true"
    >
      GS
    </div>
  );
}
