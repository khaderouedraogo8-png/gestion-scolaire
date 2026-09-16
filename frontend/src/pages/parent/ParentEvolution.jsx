import { useEffect, useState } from 'react';
import { LineChart } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import EmptyState from '../../components/EmptyState';
import Card from '../../components/Card';
import { dashboardApi } from '../../services/api/dashboard';
import { useToast } from '../../components/Toast';

export default function ParentEvolution() {
  const toast = useToast();
  const [enfants, setEnfants] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await dashboardApi.getParentEvolution();
        if (!cancelled) setEnfants(data.enfants || []);
      } catch {
        if (!cancelled) toast.error('Impossible de charger l’évolution.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [toast]);

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
        eyebrow="Espace parent"
        title="Évolution scolaire"
        subtitle="Moyennes (bulletins publiés) et absences par période"
      />

      {!enfants.length ? (
        <EmptyState icon={LineChart} message="Aucune donnée d’évolution disponible." />
      ) : (
        enfants.map((e) => (
          <Card key={e.id_eleve} premium>
            <h2 className="font-display text-lg font-medium text-encre">
              {e.prenom} {e.nom}
            </h2>
            <div className="mt-4 grid gap-6 md:grid-cols-2">
              <div>
                <h3 className="mb-2 text-sm font-medium text-encre">Moyennes par période</h3>
                {!e.moyennes_par_periode?.length ? (
                  <p className="text-sm text-texte-secondaire">Aucun bulletin publié.</p>
                ) : (
                  <ul className="space-y-2">
                    {e.moyennes_par_periode.map((m) => (
                      <li
                        key={m.id_period}
                        className="flex justify-between rounded-input border border-bordure/60 px-3 py-2 text-sm"
                      >
                        <span>{m.periode}</span>
                        <span className="tabular-nums font-medium">
                          {m.moyenne_generale != null ? m.moyenne_generale.toFixed(2) : '—'}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div>
                <h3 className="mb-2 text-sm font-medium text-encre">Absences par période</h3>
                {!e.absences_par_periode?.length ? (
                  <p className="text-sm text-texte-secondaire">Aucune absence enregistrée.</p>
                ) : (
                  <ul className="space-y-2">
                    {e.absences_par_periode.map((a) => (
                      <li
                        key={a.periode}
                        className="flex justify-between rounded-input border border-bordure/60 px-3 py-2 text-sm"
                      >
                        <span>{a.periode}</span>
                        <span className="tabular-nums font-medium">{a.count}</span>
                      </li>
                    ))}
                  </ul>
                )}
                <p className="mt-2 text-xs text-texte-secondaire">
                  Total absences : {e.total_absences ?? 0}
                </p>
              </div>
            </div>
          </Card>
        ))
      )}
    </div>
  );
}
