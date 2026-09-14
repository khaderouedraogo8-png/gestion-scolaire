import { Link } from 'react-router-dom';
import {
  ArrowRight,
  BookOpen,
  ClipboardList,
  FileText,
  GraduationCap,
  Wallet,
} from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import EmptyState from '../../components/EmptyState';
import useAuth from '../../hooks/useAuth';
import useParentChildren from '../../hooks/useParentChildren';

const CARDS = [
  {
    to: '/eleves',
    icon: GraduationCap,
    title: 'Mes enfants',
    subtitle: 'Fiches élèves et inscriptions',
    countKey: 'enfants',
  },
  {
    to: '/notes/bulletins',
    icon: FileText,
    title: 'Bulletins',
    subtitle: 'Bulletins publiés (PDF)',
  },
  {
    to: '/finance/paiements',
    icon: Wallet,
    title: 'Paiements',
    subtitle: 'Historique et reçus',
  },
  {
    to: '/absences',
    icon: ClipboardList,
    title: 'Absences',
    subtitle: 'Suivi des absences de vos enfants',
  },
  {
    to: '/parent/pedagogie',
    icon: BookOpen,
    title: 'Programme pédagogique',
    subtitle: 'Devoirs, compositions et cahier de texte',
  },
];

export default function ParentHome() {
  const { user } = useAuth();
  const { children, loading, error, selectedChild } = useParentChildren();

  const enfantsCount = children.length;
  const enfantsHint =
    enfantsCount === 0
      ? 'Aucun enfant lié pour l’instant'
      : enfantsCount === 1
        ? `${children[0].prenom} ${children[0].nom}`
        : `${enfantsCount} enfants suivis`;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Espace parent"
        title={`Bonjour, ${user?.prenom || 'parent'}`}
        subtitle="Consultez les informations de vos enfants en un seul endroit"
      />

      {error && (
        <div className="auth-alert auth-alert-error">
          <p>{error}</p>
        </div>
      )}

      {!loading && enfantsCount > 0 && (
        <section className="card-premium p-6">
          <h2 className="section-title !mb-3 !text-base">Vos enfants</h2>
          <ul className="flex flex-wrap gap-2">
            {children.map((c) => (
              <li key={c.id}>
                <Link
                  to={`/eleves/${c.id}`}
                  className={`nav-pill ${
                    selectedChild?.id === c.id ? '!border-or-cachet !bg-or-cachet-clair' : ''
                  }`}
                >
                  {c.prenom} {c.nom}
                  {c.classe_nom ? ` · ${c.classe_nom}` : ''}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {!loading && enfantsCount === 0 && !error && (
        <EmptyState
          icon={GraduationCap}
          title="Aucun enfant lié"
          message="Votre compte n’est pas encore associé à une fiche élève. Contactez le secrétariat de l’établissement."
          actionLabel="Voir les bulletins"
          actionHref="/notes/bulletins"
        />
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {CARDS.map(({ to, icon: Icon, title, subtitle, countKey }, index) => (
          <Link
            key={to}
            to={to}
            className="cycle-card group"
            style={{ animation: `slide-up 0.4s ease-out ${index * 60}ms both` }}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="stat-card-icon bg-or-cachet-clair text-or-cachet">
                <Icon className="h-[18px] w-[18px]" strokeWidth={1.75} aria-hidden="true" />
              </div>
              {countKey === 'enfants' && !loading && (
                <span className="badge-info tabular-nums">{enfantsCount}</span>
              )}
            </div>
            <div className="mt-4">
              <h2 className="font-display text-lg font-medium text-encre">{title}</h2>
              <p className="mt-1.5 text-sm leading-relaxed text-texte-secondaire">
                {countKey === 'enfants' ? enfantsHint : subtitle}
              </p>
            </div>
            <span className="cycle-card-arrow">
              Accéder
              <ArrowRight className="h-4 w-4" strokeWidth={1.75} />
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
