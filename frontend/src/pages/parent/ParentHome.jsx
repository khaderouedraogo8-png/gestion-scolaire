import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Bell,
  BookOpen,
  ClipboardList,
  FileText,
  GraduationCap,
  LineChart,
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
    to: '/parent/notes',
    icon: FileText,
    title: 'Notes & résultats',
    subtitle: 'Notes publiées et résultats académiques',
  },
  {
    to: '/parent/evolution',
    icon: LineChart,
    title: 'Évolution scolaire',
    subtitle: 'Moyennes et absences par période',
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
  {
    to: '/parent/notifications',
    icon: Bell,
    title: 'Notifications',
    subtitle: 'Boîte de réception',
  },
];

export default function ParentHome() {
  const { user } = useAuth();

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Espace parent"
        title={`Bonjour, ${user?.prenom || 'parent'}`}
        subtitle="Consultez les informations scolaires de vos enfants en un coup d’œil."
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {CARDS.map(({ to, icon: Icon, title, subtitle }) => (
          <Link
            key={to}
            to={to}
            className="card group flex flex-col gap-4 transition-all duration-150 hover:border-or-cachet/30 hover:shadow-soft"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="stat-card-icon bg-or-cachet-clair text-or-cachet">
                <Icon className="h-[18px] w-[18px]" strokeWidth={1.75} aria-hidden="true" />
              </div>
              <ArrowRight
                className="h-4 w-4 text-texte-secondaire/40 transition-all group-hover:translate-x-0.5 group-hover:text-or-cachet"
                strokeWidth={1.75}
                aria-hidden="true"
              />
            </div>
            <div>
              <h2 className="font-display text-[0.9375rem] font-semibold text-encre">{title}</h2>
              <p className="mt-1 text-sm leading-relaxed text-texte-secondaire">{subtitle}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
