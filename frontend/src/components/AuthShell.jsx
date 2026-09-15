import SealMedallion from './SealMedallion';

const HIGHLIGHTS = [
  'Pilotage élèves, notes et bulletins',
  'Finance, reçus et arriérés en un coup d’œil',
  'Absences, documents et communication',
];

/**
 * Première impression confiance : panneau brand sombre + carte claire.
 * Pas de sceau doré institutionnel — identité SaaS pétrole.
 */
export default function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div className="flex min-h-dvh">
      <aside className="auth-panel">
        <div className="auth-panel-glow" aria-hidden="true" />
        <div className="relative z-10 max-w-md animate-fade-in">
          <SealMedallion size="lg" className="mb-10 !border-or-cachet/50 !text-or-cachet" />
          <p className="page-eyebrow !text-or-cachet/90">Plateforme scolaire</p>
          <h1 className="font-display text-4xl font-semibold tracking-tight text-blanc xl:text-[2.75rem] xl:leading-[1.1]">
            Gestion Scolaire
          </h1>
          <p className="mt-5 text-base leading-relaxed text-blanc/70 xl:text-lg">
            L’outil premium pour diriger votre établissement — clair, fiable, conçu pour
            convaincre dès la première connexion.
          </p>
          <ul className="mt-10 space-y-3">
            {HIGHLIGHTS.map((item) => (
              <li key={item} className="flex items-start gap-3 text-sm text-blanc/75">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-or-cachet" aria-hidden="true" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
          <div className="mt-12 h-0.5 w-14 rounded-full bg-gradient-to-r from-or-cachet to-or-cachet/10" />
        </div>
      </aside>

      <div className="relative flex flex-1 items-center justify-center overflow-hidden p-6 sm:p-8">
        <div
          className="pointer-events-none absolute inset-0 opacity-70"
          style={{
            backgroundImage:
              'radial-gradient(ellipse 70% 50% at 80% 15%, rgba(15,118,110,0.08), transparent 55%)',
          }}
          aria-hidden="true"
        />
        <div className="relative w-full max-w-md animate-fade-in">
          <div className="card-premium p-7 sm:p-9">
            <div className="mb-8 flex flex-col items-center text-center lg:items-start lg:text-left">
              <SealMedallion size="md" className="mb-5 lg:hidden" />
              <p className="page-eyebrow mb-2 lg:hidden">Gestion Scolaire</p>
              <h2 className="page-title !text-[1.75rem] sm:!text-[1.85rem]">{title}</h2>
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
