import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, Circle, Rocket } from 'lucide-react';
import { configApi } from '../../services/api/config';
import PageHeader from '../../components/PageHeader';
import EmptyState from '../../components/EmptyState';
import { useToast } from '../../components/Toast';

const STEPS = [
  {
    key: 'niveaux',
    label: 'Niveaux d\'étude',
    description: 'Définir les cycles et niveaux (6e, 5e, Terminale…)',
    path: '/etablissement/niveaux',
  },
  {
    key: 'classes',
    label: 'Classes',
    description: 'Créer les classes pour l\'année scolaire active',
    path: '/etablissement/classes',
  },
  {
    key: 'frais',
    label: 'Frais scolaires',
    description: 'Paramétrer montants et échéanciers par niveau',
    path: '/finance/frais',
  },
  {
    key: 'eleves',
    label: 'Élèves',
    description: 'Inscrire ou importer les élèves',
    path: '/eleves',
  },
  {
    key: 'enseignants',
    label: 'Enseignants',
    description: 'Ajouter le corps enseignant et les affectations',
    path: '/emploi/enseignants',
  },
];

export default function GettingStarted() {
  const toast = useToast();
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    configApi
      .getSetupProgress()
      .then(setProgress)
      .catch(() => toast.error('Impossible de charger la progression'))
      .finally(() => setLoading(false));
  }, [toast]);

  const completedCount = STEPS.filter((s) => progress?.[s.key]?.done).length;
  const allDone = completedCount === STEPS.length;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-32">
        <div className="loading-ring" />
        <p className="text-sm text-texte-secondaire">Chargement…</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Configuration"
        title="Démarrage"
        subtitle="Suivez ces étapes pour mettre votre établissement en service"
        actions={
          allDone ? (
            <Link to="/dashboard" className="btn-primary">
              Aller au tableau de bord
            </Link>
          ) : null
        }
      />

      <div className="card-premium">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-or-cachet-clair text-or-cachet">
            <Rocket className="h-5 w-5" strokeWidth={1.75} />
          </div>
          <div>
            <p className="font-medium text-encre">
              {completedCount} / {STEPS.length} étapes complétées
            </p>
            <div className="mt-1.5 h-1.5 w-48 overflow-hidden rounded-full bg-craie">
              <div
                className="h-full rounded-full bg-or-cachet transition-all"
                style={{ width: `${(completedCount / STEPS.length) * 100}%` }}
              />
            </div>
          </div>
        </div>

        {allDone ? (
          <EmptyState
            icon={CheckCircle2}
            title="Configuration terminée"
            message="Votre établissement est prêt. Vous pouvez commencer à utiliser toutes les fonctionnalités."
            action={
              <Link to="/dashboard" className="btn-primary">
                Tableau de bord
              </Link>
            }
          />
        ) : (
          <ol className="space-y-3">
            {STEPS.map((step, index) => {
              const stepData = progress?.[step.key] || {};
              const done = Boolean(stepData.done);
              const count = stepData.count;

              return (
                <li
                  key={step.key}
                  className={`flex items-start gap-4 rounded-lg border p-4 transition-colors ${
                    done
                      ? 'border-feuille/30 bg-feuille-clair/30'
                      : 'border-bordure bg-blanc hover:border-or-cachet/30'
                  }`}
                >
                  <span className="mt-0.5 shrink-0">
                    {done ? (
                      <CheckCircle2 className="h-5 w-5 text-feuille" strokeWidth={1.75} />
                    ) : (
                      <Circle className="h-5 w-5 text-texte-secondaire/40" strokeWidth={1.75} />
                    )}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium uppercase tracking-wide text-texte-secondaire">
                      Étape {index + 1}
                    </p>
                    <p className="font-medium text-encre">{step.label}</p>
                    <p className="mt-0.5 text-sm text-texte-secondaire">{step.description}</p>
                    {count != null && (
                      <p className="mt-1 text-xs text-texte-secondaire">
                        {count} enregistrement{count > 1 ? 's' : ''}
                      </p>
                    )}
                  </div>
                  {!done && (
                    <Link to={step.path} className="btn-secondary shrink-0 text-xs">
                      Configurer
                    </Link>
                  )}
                  {done && (
                    <Link
                      to={step.path}
                      className="shrink-0 text-xs text-or-cachet hover:underline"
                    >
                      Voir
                    </Link>
                  )}
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </div>
  );
}
