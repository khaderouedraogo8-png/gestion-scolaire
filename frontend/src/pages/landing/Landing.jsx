import { Link } from 'react-router-dom';
import { ArrowRight, BookOpen, Shield, Wallet } from 'lucide-react';
import SealMedallion from '../../components/SealMedallion';

export default function Landing() {
  return (
    <div className="min-h-dvh bg-[#061525] text-blanc">
      <div
        className="relative min-h-dvh overflow-hidden"
        style={{
          backgroundImage:
            'radial-gradient(ellipse 80% 60% at 70% 40%, rgba(201,162,39,0.18) 0%, transparent 55%), linear-gradient(135deg, #061525 0%, #0B1F33 45%, #163A56 100%)',
        }}
      >
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              'url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%23ffffff\' fill-opacity=\'1\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")',
          }}
        />

        <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6 sm:px-8">
          <div className="flex items-center gap-3">
            <SealMedallion size="sm" />
            <span className="hidden text-sm text-blanc/50 sm:inline">Progiciel UEMOA / CEMAC</span>
          </div>
          <nav className="flex items-center gap-3">
            <Link
              to="/login"
              className="rounded-input px-3 py-2 text-sm font-medium text-blanc/80 transition hover:text-blanc"
            >
              Connexion
            </Link>
            <a
              href="mailto:demo@gestion-scolaire.app?subject=Demande%20de%20d%C3%A9mo"
              className="rounded-input border border-or-cachet/50 bg-or-cachet/10 px-4 py-2 text-sm font-semibold text-or-cachet transition hover:bg-or-cachet/20"
            >
              Demander une démo
            </a>
          </nav>
        </header>

        <main className="relative z-10 mx-auto flex max-w-6xl flex-col justify-center px-6 pb-24 pt-10 sm:px-8 sm:pt-16 lg:min-h-[calc(100dvh-5.5rem)] lg:pb-32">
          <p
            className="mb-5 font-display text-5xl font-semibold tracking-tight text-blanc sm:text-6xl lg:text-7xl"
            style={{ animation: 'fadeUp 0.7s ease-out both' }}
          >
            Gestion Scolaire
          </p>
          <h1
            className="max-w-2xl font-sans text-xl font-medium leading-snug text-blanc/85 sm:text-2xl"
            style={{ animation: 'fadeUp 0.7s ease-out 0.12s both' }}
          >
            Pilotage académique, financier et administratif — conçu pour les établissements
            d&apos;Afrique de l&apos;Ouest et Centrale.
          </h1>
          <p
            className="mt-5 max-w-xl text-base leading-relaxed text-blanc/55"
            style={{ animation: 'fadeUp 0.7s ease-out 0.22s both' }}
          >
            Notes, bulletins, recouvrement Mobile Money, SYSCOHADA et portail parents — une
            plateforme claire pour votre école.
          </p>
          <div
            className="mt-10 flex flex-wrap items-center gap-4"
            style={{ animation: 'fadeUp 0.7s ease-out 0.32s both' }}
          >
            <Link
              to="/login"
              className="inline-flex items-center gap-2 rounded-input bg-or-cachet px-6 py-3 text-sm font-semibold text-encre transition hover:bg-[#d4b03a] active:scale-[0.98]"
            >
              Se connecter
              <ArrowRight className="h-4 w-4" strokeWidth={2} />
            </Link>
            <a
              href="mailto:demo@gestion-scolaire.app?subject=Demande%20de%20d%C3%A9mo"
              className="inline-flex items-center gap-2 rounded-input border border-blanc/25 bg-blanc/5 px-6 py-3 text-sm font-semibold text-blanc backdrop-blur-sm transition hover:bg-blanc/10"
            >
              Demander une démo
            </a>
          </div>
        </main>

        <section
          className="relative z-10 border-t border-blanc/10 bg-[#061525]/80 backdrop-blur-sm"
          style={{ animation: 'fadeUp 0.8s ease-out 0.4s both' }}
        >
          <div className="mx-auto grid max-w-6xl gap-8 px-6 py-12 sm:grid-cols-3 sm:px-8">
            <div className="flex gap-3">
              <BookOpen className="mt-0.5 h-5 w-5 shrink-0 text-or-cachet" strokeWidth={1.75} />
              <div>
                <p className="font-display text-sm font-semibold text-blanc">Pédagogie</p>
                <p className="mt-1 text-sm text-blanc/50">Notes, conseils de classe, bulletins.</p>
              </div>
            </div>
            <div className="flex gap-3">
              <Wallet className="mt-0.5 h-5 w-5 shrink-0 text-or-cachet" strokeWidth={1.75} />
              <div>
                <p className="font-display text-sm font-semibold text-blanc">Finance</p>
                <p className="mt-1 text-sm text-blanc/50">Recouvrement, Mobile Money, SYSCOHADA.</p>
              </div>
            </div>
            <div className="flex gap-3">
              <Shield className="mt-0.5 h-5 w-5 shrink-0 text-or-cachet" strokeWidth={1.75} />
              <div>
                <p className="font-display text-sm font-semibold text-blanc">Vie scolaire</p>
                <p className="mt-1 text-sm text-blanc/50">Cantine, transport, RH, inventaire.</p>
              </div>
            </div>
          </div>
        </section>
      </div>

      <style>{`
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(16px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
