import { Link } from 'react-router-dom';

export default function EmptyState({
  icon: Icon,
  title,
  message,
  actionLabel,
  onAction,
  actionHref,
}) {
  return (
    <div className="empty-state">
      {Icon && (
        <div className="empty-state-icon">
          <Icon className="h-5 w-5" strokeWidth={1.75} aria-hidden="true" />
        </div>
      )}
      {title && <p className="empty-state-title">{title}</p>}
      <p className="empty-state-message">{message}</p>
      {actionLabel && (onAction || actionHref) && (
        <div className="mt-5">
          {actionHref ? (
            <Link to={actionHref} className="btn-primary text-sm">
              {actionLabel}
            </Link>
          ) : (
            <button type="button" className="btn-primary text-sm" onClick={onAction}>
              {actionLabel}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
