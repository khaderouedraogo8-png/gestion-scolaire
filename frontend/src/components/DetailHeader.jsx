export default function DetailHeader({ breadcrumb, eyebrow, title, subtitle, media, actions }) {
  return (
    <div className="detail-header">
      {breadcrumb}
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div className="flex min-w-0 flex-1 items-start gap-4">
          {media}
          <div className="min-w-0">
            {eyebrow && <p className="page-eyebrow">{eyebrow}</p>}
            <h1 className="page-title">{title}</h1>
            {subtitle &&
              (typeof subtitle === 'string' ? (
                <p className="page-subtitle">{subtitle}</p>
              ) : (
                <div className="page-subtitle">{subtitle}</div>
              ))}
            <div className="page-title-accent" aria-hidden="true" />
          </div>
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}
