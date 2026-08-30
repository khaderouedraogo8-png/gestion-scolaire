const SIZES = {
  sm: { outer: 'h-7 w-7', text: 'text-[10px]', border: 'border-[1.5px]' },
  md: { outer: 'h-10 w-10', text: 'text-xs', border: 'border-[1.5px]' },
  lg: { outer: 'h-16 w-16', text: 'text-lg', border: 'border-2' },
};

export default function SealMedallion({ size = 'md', className = '' }) {
  const s = SIZES[size] || SIZES.md;

  return (
    <div
      className={`relative flex shrink-0 items-center justify-center rounded-full font-display font-medium text-or-cachet ${s.outer} ${s.text} ${className}`}
      aria-hidden="true"
    >
      <span
        className={`absolute inset-0 rounded-full border-or-cachet/40 ${s.border} bg-gradient-to-br from-or-cachet/10 to-transparent`}
      />
      <span
        className={`absolute inset-[2px] rounded-full border-or-cachet/20 ${size === 'lg' ? 'border' : 'border-[0.5px]'}`}
      />
      <span className="relative z-10">GS</span>
    </div>
  );
}
