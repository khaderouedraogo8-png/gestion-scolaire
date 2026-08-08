import { useCallback, useEffect, useState } from 'react';
import { financeApi } from '../../services/api/finance';
import { configApi } from '../../services/api/config';
import Table from '../../components/Table';
import { useToast } from '../../components/Toast';

export default function Arrieres() {
  const toast = useToast();
  const [arrieres, setArrieres] = useState([]);
  const [annees, setAnnees] = useState([]);
  const [idAnnee, setIdAnnee] = useState('');
  const [loading, setLoading] = useState(true);
  const [relancing, setRelancing] = useState(false);

  useEffect(() => {
    configApi
      .listAnnees()
      .then((a) => {
        const list = Array.isArray(a) ? a : a.items || [];
        setAnnees(list);
        const active = list.find((x) => x.est_active);
        if (active) setIdAnnee(String(active.id));
      })
      .catch(() => toast.error('Erreur chargement années'));
  }, [toast]);

  const load = useCallback(async () => {
    if (!idAnnee) return;
    setLoading(true);
    try {
      const data = await financeApi.listArrieres({ id_annee: idAnnee });
      setArrieres(Array.isArray(data) ? data : data.items || []);
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur chargement arriérés');
    } finally {
      setLoading(false);
    }
  }, [idAnnee, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const columns = [
    { key: 'matricule', header: 'Matricule' },
    { key: 'nom', header: 'Élève', render: (r) => `${r.prenom} ${r.nom}` },
    {
      key: 'total_du',
      header: 'Total dû',
      render: (r) => `${Number(r.total_du).toLocaleString()} FCFA`,
    },
    {
      key: 'total_paye',
      header: 'Payé',
      render: (r) => `${Number(r.total_paye).toLocaleString()} FCFA`,
    },
    {
      key: 'arriere',
      header: 'Arriéré',
      render: (r) => (
        <span className="font-semibold text-brique">
          {Number(r.arriere).toLocaleString()} FCFA
        </span>
      ),
    },
  ];

  const total = arrieres.reduce((s, a) => s + (a.arriere || 0), 0);

  const handleExport = async () => {
    if (!idAnnee) return;
    try {
      const blob = await financeApi.exportArrieresExcel(idAnnee);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'arrieres.xlsx';
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Export Excel téléchargé');
    } catch {
      toast.error('Erreur export Excel');
    }
  };

  const handleRelancer = async () => {
    if (!idAnnee || arrieres.length === 0) return;
    if (!window.confirm(`Envoyer une relance à ${arrieres.length} parent(s) ?`)) return;
    setRelancing(true);
    try {
      const res = await financeApi.relancerArrieres(idAnnee);
      toast.success(res.message || 'Relances programmées');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur relances');
    } finally {
      setRelancing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="page-title">Arriérés</h1>
          <p className="page-subtitle">
            Total impayé : <strong>{total.toLocaleString()} FCFA</strong>
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleRelancer}
            disabled={!idAnnee || arrieres.length === 0 || relancing}
            className="btn-primary"
          >
            {relancing ? 'Envoi…' : 'Relancer les parents'}
          </button>
          <button type="button" onClick={handleExport} disabled={!idAnnee} className="btn-secondary">
            Export Excel
          </button>
          <select
          className="input w-auto"
          value={idAnnee}
          onChange={(e) => setIdAnnee(e.target.value)}
        >
          <option value="">Année scolaire</option>
          {annees.map((a) => (
            <option key={a.id} value={a.id}>
              {a.libelle}
            </option>
          ))}
        </select>
        </div>
      </div>
      <Table columns={columns} data={arrieres} loading={loading} emptyMessage="Aucun arriéré" />
    </div>
  );
}
