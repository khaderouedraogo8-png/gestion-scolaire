export default function EmptyState({ icon: Icon, title, message, action }) {
  return (
    <div className="empty-state">
      {Icon && (
        <div className="empty-state-icon">
          <Icon className="h-5 w-5" strokeWidth={1.75} aria-hidden="true" />
        </div>
      )}
      {title && <p className="empty-state-title">{title}</p>}
      {message && <p className="empty-state-message">{message}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
