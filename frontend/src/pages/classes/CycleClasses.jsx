import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Breadcrumb from '../../components/Breadcrumb';
import Card from '../../components/Card';
import { configApi } from '../../services/api/config';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';
import { cycleLabel, toClassSlug } from '../../utils/classNavigation';

export default function CycleClasses() {
  const { cycle } = useParams();
  const toast = useToast();
  const [classes, setClasses] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      try {
        const annees = await configApi.listAnnees();
        const list = Array.isArray(annees) ? annees : annees.items || [];
        const active = list.find((a) => a.est_active);
        const data = await configApi.listClassesNav({
          cycle,
          id_annee: active?.id,
          enriched: true,
        });
        if (!cancelled) setClasses(Array.isArray(data) ? data : []);
      } catch {
        if (!cancelled) toast.error('Impossible de charger les classes.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [cycle, toast]);

  return (
    <div className="space-y-8">
      <Breadcrumb
        items={[
          { label: 'Classes', to: '/classes' },
          { label: cycleLabel(cycle) },
        ]}
      />
      <PageHeader
        eyebrow="Élèves"
        title={cycleLabel(cycle)}
        subtitle="Sélectionnez une classe"
      />

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-or-cachet-clair border-t-or-cachet" />
        </div>
      ) : classes.length === 0 ? (
        <p className="text-sm text-texte-secondaire">Aucune classe pour ce cycle pour l'instant.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {classes.map((classe) => (
            <Link key={classe.id} to={`/classes/${cycle}/${toClassSlug(classe.libelle)}`}>
              <Card className="transition-colors hover:border-or-cachet/40">
                <h2 className="font-display text-lg font-medium text-encre">{classe.libelle}</h2>
                <dl className="mt-3 space-y-1 text-sm text-texte-secondaire">
                  <div className="flex justify-between">
                    <dt>Effectif</dt>
                    <dd className="tabular-nums text-encre">{classe.effectif ?? 0}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt>Absences du jour</dt>
                    <dd className="tabular-nums text-encre">{classe.absences_jour ?? 0}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt>Non justifiées (7 j.)</dt>
                    <dd className="tabular-nums text-brique">{classe.non_justifiees_en_attente ?? 0}</dd>
                  </div>
                </dl>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
