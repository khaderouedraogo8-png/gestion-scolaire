const VARIANTS = {
  success: 'badge-success',
  warning: 'badge-warning',
  danger: 'badge-danger',
  info: 'badge-info',
  neutral: 'badge-neutral',
};

export default function Badge({ variant = 'neutral', children, className = '' }) {
  return <span className={`${VARIANTS[variant] || VARIANTS.neutral} ${className}`}>{children}</span>;
}
