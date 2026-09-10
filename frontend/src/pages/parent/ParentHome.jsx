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
import useAuth from '../../hooks/useAuth';

const CARDS = [
  {
    to: '/eleves',
    icon: GraduationCap,
    title: 'Mes enfants',
    subtitle: 'Fiches élèves et inscriptions',
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

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Espace parent"
        title={`Bonjour, ${user?.prenom || 'parent'}`}
        subtitle="Consultez les informations de vos enfants en un seul endroit"
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {CARDS.map(({ to, icon: Icon, title, subtitle }, index) => (
          <Link
            key={to}
            to={to}
            className="cycle-card group"
            style={{ animation: `slide-up 0.4s ease-out ${index * 60}ms both` }}
          >
            <div className="stat-card-icon bg-or-cachet-clair text-or-cachet">
              <Icon className="h-[18px] w-[18px]" strokeWidth={1.75} aria-hidden="true" />
            </div>
            <div className="mt-4">
              <h2 className="font-display text-lg font-medium text-encre">{title}</h2>
              <p className="mt-1.5 text-sm leading-relaxed text-texte-secondaire">{subtitle}</p>
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
