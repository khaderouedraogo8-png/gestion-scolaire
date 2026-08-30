import SealMedallion from './SealMedallion';

export default function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div className="flex min-h-dvh">
      <div className="sidebar-premium relative hidden w-1/2 flex-col justify-center overflow-hidden p-12 lg:flex">
        <div
          className="pointer-events-none absolute inset-0 opacity-30"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 80%, rgba(184,134,46,0.25) 0%, transparent 50%), radial-gradient(circle at 80% 20%, rgba(255,255,255,0.06) 0%, transparent 40%)',
          }}
        />
        <div className="relative max-w-md">
          <SealMedallion size="lg" className="mb-8" />
          <p className="page-eyebrow !text-or-cachet/80">Établissement scolaire</p>
          <h1 className="font-display text-4xl font-medium tracking-tight text-craie">
            Gestion Scolaire
          </h1>
          <p className="mt-5 text-lg leading-relaxed text-craie/65">
            Plateforme complète de gestion pour votre établissement : élèves, notes, finances,
            absences et bien plus.
          </p>
          <div className="mt-10 h-0.5 w-16 rounded-full bg-or-cachet" />
        </div>
      </div>

      <div className="flex flex-1 items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="card-premium p-8">
            <div className="mb-8 flex flex-col items-center text-center lg:items-start lg:text-left">
              <SealMedallion size="lg" className="mb-6 lg:hidden" />
              <h2 className="page-title">{title}</h2>
              {subtitle && <p className="page-subtitle mt-2">{subtitle}</p>}
              <div className="page-title-accent mx-auto lg:mx-0" aria-hidden="true" />
            </div>
            {children}
          </div>
          {footer && <div className="mt-6 text-center">{footer}</div>}
        </div>
      </div>
    </div>
  );
}
