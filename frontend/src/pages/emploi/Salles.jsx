import { useEffect, useState } from 'react';
import { emploiApi } from '../../services/api/emploi';
import Table from '../../components/Table';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';

export default function Salles() {
  const toast = useToast();
  const { isAdmin } = useAuth();
  const [salles, setSalles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ libelle: '', capacite: '' });

  const load = () => {
    setLoading(true);
    emploiApi
      .listSalles()
      .then((data) => setSalles(Array.isArray(data) ? data : data.items || []))
      .catch(() => toast.error('Erreur chargement salles'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [toast]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await emploiApi.createSalle({
        libelle: form.libelle,
        capacite: form.capacite ? Number(form.capacite) : null,
      });
      toast.success('Salle créée');
      setModalOpen(false);
      setForm({ libelle: '', capacite: '' });
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const columns = [
    { key: 'libelle', header: 'Salle' },
    { key: 'capacite', header: 'Capacité', render: (r) => r.capacite || '—' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Salles</h1>
          <p className="page-subtitle">Salles de cours disponibles</p>
        </div>
        {isAdmin && (
          <button type="button" className="btn-primary" onClick={() => setModalOpen(true)}>
            + Nouvelle salle
          </button>
        )}
      </div>
      <Table columns={columns} data={salles} loading={loading} emptyMessage="Aucune salle" />
      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Nouvelle salle">
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField
            label="Libellé"
            value={form.libelle}
            onChange={(e) => setForm({ ...form, libelle: e.target.value })}
            required
          />
          <FormField
            label="Capacité"
            type="number"
            value={form.capacite}
            onChange={(e) => setForm({ ...form, capacite: e.target.value })}
          />
          <button type="submit" className="btn-primary w-full">
            Enregistrer
          </button>
        </form>
      </Modal>
    </div>
  );
}
