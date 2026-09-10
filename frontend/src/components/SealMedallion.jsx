const SIZES = {
  sm: { outer: 'h-7 w-7', text: 'text-[10px]', border: 'border-[1.5px]', inset: 'inset-[2px]' },
  md: { outer: 'h-10 w-10', text: 'text-xs', border: 'border-[1.5px]', inset: 'inset-[2.5px]' },
  lg: { outer: 'h-16 w-16', text: 'text-lg', border: 'border-2', inset: 'inset-[3px]' },
  xl: { outer: 'h-20 w-20', text: 'text-xl', border: 'border-2', inset: 'inset-[4px]' },
};

export default function SealMedallion({ size = 'md', className = '' }) {
  const s = SIZES[size] || SIZES.md;
  const isLarge = size === 'lg' || size === 'xl';

  return (
    <div
      className={`relative flex shrink-0 items-center justify-center rounded-full font-display font-medium tracking-wide text-or-cachet ${s.outer} ${s.text} ${className}`}
      aria-hidden="true"
    >
      <span
        className={`absolute inset-0 rounded-full border-or-cachet/45 ${s.border}`}
        style={{
          background:
            'radial-gradient(circle at 35% 30%, rgba(184,134,46,0.18), transparent 55%), linear-gradient(145deg, rgba(184,134,46,0.12), transparent 60%)',
        }}
      />
      <span
        className={`absolute ${s.inset} rounded-full border-or-cachet/25 ${isLarge ? 'border' : 'border-[0.5px]'}`}
      />
      {isLarge && (
        <span
          className="absolute inset-[7px] rounded-full border border-dashed border-or-cachet/20"
          aria-hidden="true"
        />
      )}
      <span className="relative z-10 drop-shadow-[0_1px_0_rgba(255,255,255,0.15)]">GS</span>
    </div>
  );
}
