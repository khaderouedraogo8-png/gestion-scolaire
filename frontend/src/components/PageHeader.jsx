export default function PageHeader({ eyebrow, title, subtitle, actions }) {
  return (
    <div className="page-header">
      <div className="page-header-content">
        {eyebrow && <p className="page-eyebrow">{eyebrow}</p>}
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
        <div className="page-title-accent" aria-hidden="true" />
      </div>
      {actions && (
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end">
          {actions}
        </div>
      )}
    </div>
  );
}
