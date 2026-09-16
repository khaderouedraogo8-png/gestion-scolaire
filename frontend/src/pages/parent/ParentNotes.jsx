import { useEffect, useState } from 'react';
import { FileText } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import EmptyState from '../../components/EmptyState';
import Card from '../../components/Card';
import Table from '../../components/Table';
import useParentChildren from '../../hooks/useParentChildren';
import { notesApi } from '../../services/api/notes';
import { elevesApi } from '../../services/api/eleves';
import { configApi } from '../../services/api/config';
import { useToast } from '../../components/Toast';

export default function ParentNotes() {
  const toast = useToast();
  const { children, selectedId, selectChild, loading: loadingChildren } = useParentChildren();
  const [periodes, setPeriodes] = useState([]);
  const [idPeriod, setIdPeriod] = useState('');
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [classeId, setClasseId] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!selectedId) return;
      try {
        const detail = await elevesApi.get(selectedId);
        const inscriptions = detail.inscriptions || [];
        const list = Array.isArray(inscriptions) ? inscriptions : [];
        const active =
          list.find((i) => i.statut === 'inscrit' || i.statut === 'reinscrit') || list[0];
        const cid = active?.id_classe || active?.classe?.id;
        if (!cancelled) setClasseId(cid ? String(cid) : '');

        const annees = await configApi.listAnnees();
        const aList = Array.isArray(annees) ? annees : annees.items || [];
        const activeAnnee = aList.find((a) => a.est_active) || aList[0];
        if (activeAnnee) {
          const trim = await configApi.listTrimestres(activeAnnee.id);
          const tList = Array.isArray(trim) ? trim : trim.items || [];
          if (!cancelled) {
            setPeriodes(tList);
            if (tList[0]) setIdPeriod(String(tList[0].id));
          }
        }
      } catch {
        if (!cancelled) toast.error('Impossible de charger le contexte élève.');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedId, toast]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!selectedId || !classeId || !idPeriod) {
        setRows([]);
        return;
      }
      setLoading(true);
      try {
        const data = await notesApi.listResultats({
          id_eleve: selectedId,
          id_classe: classeId,
          id_period: idPeriod,
        });
        if (!cancelled) {
          setRows(
            (data.items || []).map((r, i) => ({
              id: r.id || `${r.id_matiere || i}`,
              matiere: r.matiere_libelle || r.matiere || '—',
              moyenne: r.moyenne != null ? Number(r.moyenne).toFixed(2) : '—',
              scale_max: r.scale_max ?? 20,
              appreciation: r.appreciation || '—',
            }))
          );
        }
      } catch {
        if (!cancelled) {
          setRows([]);
          toast.error('Impossible de charger les résultats.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedId, classeId, idPeriod, toast]);

  if (loadingChildren) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-32">
        <div className="loading-ring" />
      </div>
    );
  }

  const columns = [
    { key: 'matiere', header: 'Matière' },
    { key: 'moyenne', header: 'Moyenne' },
    { key: 'scale_max', header: 'Échelle' },
    { key: 'appreciation', header: 'Appréciation' },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Espace parent"
        title="Notes & résultats"
        subtitle="Résultats académiques pour vos enfants"
      />

      {!children?.length ? (
        <EmptyState icon={FileText} message="Aucun enfant lié à votre compte." />
      ) : (
        <>
          <div className="flex flex-wrap gap-4">
            <label className="text-sm">
              <span className="mb-1 block text-texte-secondaire">Enfant</span>
              <select
                className="input"
                value={selectedId}
                onChange={(e) => selectChild(e.target.value)}
              >
                {children.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.prenom} {c.nom}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-texte-secondaire">Période</span>
              <select
                className="input"
                value={idPeriod}
                onChange={(e) => setIdPeriod(e.target.value)}
              >
                {periodes.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label || p.libelle || `Période ${p.numero || p.sequence}`}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <Card premium>
            <Table columns={columns} data={rows} loading={loading} emptyMessage="Aucun résultat pour cette période." />
          </Card>
        </>
      )}
    </div>
  );
}
