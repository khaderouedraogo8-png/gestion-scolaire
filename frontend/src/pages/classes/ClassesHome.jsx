import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import PageHeader from '../../components/PageHeader';
import { cycleLabel } from '../../utils/classNavigation';

const CYCLES = [
  {
    id: 'premier',
    title: 'Premier cycle',
    description: '6ème, 5ème, 4ème et 3ème — collège',
    levels: ['6ème', '5ème', '4ème', '3ème'],
  },
  {
    id: 'second',
    title: 'Second cycle',
    description: 'Seconde, Première et Terminale — lycée',
    levels: ['Seconde', 'Première', 'Terminale'],
  },
];

export default function ClassesHome() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Élèves"
        title="Classes"
        subtitle="Choisissez un cycle pour accéder aux classes et à leur suivi pédagogique"
        actions={
          <Link to="/eleves/recherche" className="btn-secondary text-sm">
            Recherche globale
          </Link>
        }
      />

      <div className="grid gap-5 sm:grid-cols-2">
        {CYCLES.map((cycle, index) => (
          <Link
            key={cycle.id}
            to={`/classes/${cycle.id}`}
            className="cycle-card"
            style={{ animation: `slide-up 0.45s ease-out ${index * 80}ms both` }}
          >
            <p className="page-eyebrow !mb-3">Cycle</p>
            <h2 className="font-display text-2xl font-medium tracking-tight text-encre">
              {cycleLabel(cycle.id)}
            </h2>
            <p className="mt-2.5 text-sm leading-relaxed text-texte-secondaire">{cycle.description}</p>
            <div className="mt-5 flex flex-wrap gap-1.5">
              {cycle.levels.map((level) => (
                <span key={level} className="badge-neutral">
                  {level}
                </span>
              ))}
            </div>
            <span className="cycle-card-arrow">
              Ouvrir
              <ArrowRight className="h-4 w-4" strokeWidth={1.75} />
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
