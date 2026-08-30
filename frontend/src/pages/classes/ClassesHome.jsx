import { Link } from 'react-router-dom';
import Card from '../../components/Card';
import PageHeader from '../../components/PageHeader';
import { cycleLabel } from '../../utils/classNavigation';

const CYCLES = [
  {
    id: 'premier',
    title: 'Premier cycle',
    description: '6ème, 5ème, 4ème, 3ème',
  },
  {
    id: 'second',
    title: 'Second cycle',
    description: 'Seconde, Première, Terminale',
  },
];

export default function ClassesHome() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Élèves"
        title="Classes"
        subtitle="Choisissez un cycle pour accéder aux classes"
        actions={
          <Link to="/eleves/recherche" className="btn-secondary text-sm">
            Recherche globale
          </Link>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2">
        {CYCLES.map((cycle) => (
          <Link key={cycle.id} to={`/classes/${cycle.id}`}>
            <Card className="transition-colors hover:border-or-cachet/40">
              <h2 className="font-display text-xl font-medium text-encre">{cycleLabel(cycle.id)}</h2>
              <p className="mt-2 text-sm text-texte-secondaire">{cycle.description}</p>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
