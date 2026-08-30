import { Link } from 'react-router-dom';
import {
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
        subtitle="Consultez les informations de vos enfants"
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {CARDS.map(({ to, icon: Icon, title, subtitle }) => (
          <Link
            key={to}
            to={to}
            className="card-premium group flex flex-col gap-3 transition-colors hover:border-or-cachet/35"
          >
            <div className="stat-card-icon bg-or-cachet-clair text-or-cachet">
              <Icon className="h-[18px] w-[18px]" strokeWidth={1.75} aria-hidden="true" />
            </div>
            <div>
              <h2 className="font-display text-base font-medium text-encre">{title}</h2>
              <p className="mt-1 text-sm text-texte-secondaire">{subtitle}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
