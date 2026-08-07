import { useCallback, useEffect, useState } from 'react';
import { financeApi } from '../../services/api/finance';
import Table from '../../components/Table';
import { useToast } from '../../components/Toast';

export default function PaiementsParent() {
  const toast = useToast();
  const [paiements, setPaiements] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await financeApi.listPaiements();
      setPaiements(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Erreur chargement paiements');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const handlePdf = async (id) => {
    try {
      const blob = await financeApi.getRecuPdf(id);
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    } catch {
      toast.error('PDF indisponible');
    }
  };

  const columns = [
    { key: 'numero_recu', header: 'N° Reçu' },
    { key: 'eleve_nom', header: 'Élève', render: (r) => r.eleve_nom || '—' },
    { key: 'motif', header: 'Motif' },
    {
      key: 'montant',
      header: 'Montant',
      render: (r) => `${Number(r.montant_verse).toLocaleString()} FCFA`,
    },
    {
      key: 'actions',
      header: '',
      render: (r) =>
        !r.annule ? (
          <button type="button" onClick={() => handlePdf(r.id)} className="text-primary-600 text-sm hover:underline">
            Reçu PDF
          </button>
        ) : null,
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Mes paiements</h1>
        <p className="text-sm text-slate-500">Historique des paiements scolaires</p>
      </div>
      <Table columns={columns} data={paiements.filter((p) => !p.annule)} loading={loading} emptyMessage="Aucun paiement" />
    </div>
  );
}
