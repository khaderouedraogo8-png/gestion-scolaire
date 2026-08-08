import { useCallback, useEffect, useState } from 'react';
import { financeApi } from '../../services/api/finance';
import Table from '../../components/Table';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';

export default function Recus() {
  const toast = useToast();
  const { isAdmin } = useAuth();
  const [paiements, setPaiements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [annulModal, setAnnulModal] = useState(null);
  const [motif, setMotif] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await financeApi.listPaiements();
      setPaiements(Array.isArray(data) ? data : data.items || []);
    } catch {
      toast.error('Erreur chargement reçus');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const handleAnnuler = async (e) => {
    e.preventDefault();
    try {
      await financeApi.annulerPaiement(annulModal.id, motif);
      toast.success('Paiement annulé (historique conservé)');
      setAnnulModal(null);
      setMotif('');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur annulation');
    }
  };

  const handlePdf = async (id) => {
    try {
      const blob = await financeApi.getRecuPdf(id);
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    } catch (err) {
      toast.error(err.response?.data?.message || 'PDF indisponible');
    }
  };

  const columns = [
    { key: 'numero_recu', header: 'N° Reçu' },
    {
      key: 'eleve',
      header: 'Élève',
      render: (r) => r.eleve_nom || '—',
    },
    { key: 'motif', header: 'Motif' },
    {
      key: 'montant_verse',
      header: 'Montant',
      render: (r) => `${Number(r.montant_verse).toLocaleString()} FCFA`,
    },
    { key: 'mode_paiement', header: 'Mode' },
    {
      key: 'date_paiement',
      header: 'Date',
      render: (r) => new Date(r.date_paiement).toLocaleDateString('fr-FR'),
    },
    {
      key: 'statut',
      header: 'Statut',
      render: (r) =>
        r.annule ? (
          <span className="badge-neutral">Annulé</span>
        ) : (
          <span className="badge-success">Valide</span>
        ),
    },
    {
      key: 'actions',
      header: '',
      render: (r) => (
        <div className="flex gap-2">
          {!r.annule && (
            <button
              type="button"
              onClick={() => handlePdf(r.id)}
              className="text-xs text-or-cachet hover:underline"
            >
              PDF
            </button>
          )}
          {isAdmin && !r.annule && (
            <button
              type="button"
              onClick={() => setAnnulModal(r)}
              className="text-xs text-brique hover:underline"
            >
              Annuler
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Reçus de paiement</h1>
        <p className="page-subtitle">Aucune suppression — annulation tracée uniquement</p>
      </div>
      <Table columns={columns} data={paiements} loading={loading} emptyMessage="Aucun paiement" />

      <Modal
        isOpen={Boolean(annulModal)}
        onClose={() => setAnnulModal(null)}
        title={`Annuler ${annulModal?.numero_recu || ''}`}
      >
        <form onSubmit={handleAnnuler} className="space-y-4">
          <FormField
            label="Motif d'annulation"
            value={motif}
            onChange={(e) => setMotif(e.target.value)}
            required
          />
          <button type="submit" className="btn-primary w-full">
            Confirmer l'annulation
          </button>
        </form>
      </Modal>
    </div>
  );
}
