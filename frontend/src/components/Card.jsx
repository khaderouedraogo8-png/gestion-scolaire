export default function Card({ children, className = '', premium = false, interactive = false, ...rest }) {
  const base = premium ? 'card-premium' : 'card';
  const hover = interactive ? ' card-interactive' : '';
  return (
    <div className={`${base}${hover} ${className}`} {...rest}>
      {children}
    </div>
  );
}
