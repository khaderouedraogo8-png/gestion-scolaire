import SealMedallion from './SealMedallion';

export default function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div className="flex min-h-dvh bg-craie">
      <div className="sidebar-premium relative hidden w-[44%] flex-col justify-between overflow-hidden p-10 xl:p-14 lg:flex">
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage:
              'radial-gradient(circle at 15% 85%, rgba(14,116,144,0.22) 0%, transparent 45%), radial-gradient(circle at 90% 10%, rgba(255,255,255,0.05) 0%, transparent 35%)',
          }}
        />
        <div className="relative">
          <SealMedallion size="md" />
        </div>
        <div className="relative max-w-md">
          <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-or-cachet">
            Établissement scolaire
          </p>
          <h1 className="font-display text-4xl font-semibold tracking-tight text-blanc xl:text-[2.75rem]">
            Gestion Scolaire
          </h1>
          <p className="mt-5 text-base leading-relaxed text-blanc/60">
            Pilotage académique, administratif et financier — une plateforme claire pour
            votre établissement.
          </p>
          <ul className="mt-10 space-y-3 text-sm text-blanc/55">
            <li className="flex items-center gap-2.5">
              <span className="h-1.5 w-1.5 rounded-full bg-or-cachet" aria-hidden="true" />
              Effectifs, notes et bulletins
            </li>
            <li className="flex items-center gap-2.5">
              <span className="h-1.5 w-1.5 rounded-full bg-or-cachet" aria-hidden="true" />
              Finance et recouvrement
            </li>
            <li className="flex items-center gap-2.5">
              <span className="h-1.5 w-1.5 rounded-full bg-or-cachet" aria-hidden="true" />
              Portail parents sécurisé
            </li>
          </ul>
        </div>
        <p className="relative text-xs text-blanc/35">© {new Date().getFullYear()} Gestion Scolaire</p>
      </div>

      <div className="flex flex-1 items-center justify-center p-5 sm:p-8">
        <div className="w-full max-w-[26rem]">
          <div className="mb-8 flex flex-col items-center text-center lg:hidden">
            <SealMedallion size="lg" className="mb-4" />
            <p className="font-display text-lg font-semibold text-encre">Gestion Scolaire</p>
          </div>
          <div className="card border-bordure/80 p-7 shadow-elevated sm:p-8">
            <div className="mb-7">
              <h2 className="font-display text-2xl font-semibold tracking-tight text-encre">
                {title}
              </h2>
              {subtitle && (
                <p className="mt-2 text-sm leading-relaxed text-texte-secondaire">{subtitle}</p>
              )}
            </div>
            {children}
          </div>
          {footer && <div className="mt-6 text-center">{footer}</div>}
        </div>
      </div>
    </div>
  );
}
