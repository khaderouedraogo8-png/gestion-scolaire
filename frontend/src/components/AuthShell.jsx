import SealMedallion from './SealMedallion';

const HIGHLIGHTS = [
  'Élèves, notes et bulletins officiels',
  'Finances, reçus et arriérés',
  'Absences, documents et communication',
];

export default function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div className="flex min-h-dvh">
      <aside className="auth-panel">
        <div className="auth-panel-glow" aria-hidden="true" />
        <div className="auth-seal-watermark" aria-hidden="true" />

        <div className="relative z-10 max-w-md animate-[slide-up_0.6s_ease-out]">
          <SealMedallion size="xl" className="mb-10" />
          <p className="page-eyebrow !mb-3 !text-or-cachet/90">Établissement scolaire</p>
          <h1 className="font-display text-[2.75rem] font-medium leading-[1.1] tracking-tight text-craie xl:text-5xl">
            Gestion Scolaire
          </h1>
          <p className="mt-5 text-base leading-relaxed text-craie/70 xl:text-lg">
            Une plateforme claire et fiable pour piloter la vie de votre établissement — du
            premier jour de classe au bulletin final.
          </p>

          <ul className="mt-10 space-y-3">
            {HIGHLIGHTS.map((item) => (
              <li key={item} className="flex items-start gap-3 text-sm text-craie/75">
                <span
                  className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-or-cachet"
                  aria-hidden="true"
                />
                <span>{item}</span>
              </li>
            ))}
          </ul>

          <div className="mt-12 h-0.5 w-16 rounded-full bg-gradient-to-r from-or-cachet to-or-cachet/10" />
        </div>
      </aside>

      <div className="relative flex flex-1 items-center justify-center overflow-hidden p-6 sm:p-8">
        <div
          className="pointer-events-none absolute inset-0 opacity-60"
          style={{
            backgroundImage:
              'radial-gradient(ellipse 70% 50% at 80% 20%, rgba(184,134,46,0.08), transparent 55%)',
          }}
          aria-hidden="true"
        />
        <div className="relative w-full max-w-md animate-[slide-up_0.5s_ease-out]">
          <div className="card-premium p-7 sm:p-9">
            <div className="mb-8 flex flex-col items-center text-center lg:items-start lg:text-left">
              <SealMedallion size="lg" className="mb-6 lg:hidden" />
              <h2 className="page-title !text-[1.85rem] sm:!text-3xl">{title}</h2>
              {subtitle && <p className="page-subtitle mt-2">{subtitle}</p>}
              <div className="page-title-accent mx-auto lg:mx-0" aria-hidden="true" />
            </div>
            {children}
          </div>
          {footer && <div className="mt-7 text-center">{footer}</div>}
        </div>
      </div>
    </div>
  );
}
