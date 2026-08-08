import { useEffect, useState } from 'react';
import { configApi } from '../../services/api/config';
import Table from '../../components/Table';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function Niveaux() {
  const toast = useToast();
  const [niveaux, setNiveaux] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ libelle: '', ordre: '', cycle: 'premier' });

  const load = () => {
    setLoading(true);
    configApi
      .listNiveaux()
      .then((data) => setNiveaux(Array.isArray(data) ? data : data.items || []))
      .catch(() => toast.error('Erreur chargement niveaux'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [toast]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await configApi.createNiveau({
        libelle: form.libelle,
        ordre: Number(form.ordre),
        cycle: form.cycle,
      });
      toast.success('Niveau créé');
      setModalOpen(false);
      setForm({ libelle: '', ordre: '', cycle: 'premier' });
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const columns = [
    { key: 'ordre', header: 'Ordre' },
    { key: 'libelle', header: 'Niveau' },
    {
      key: 'cycle',
      header: 'Cycle',
      render: (r) => (r.cycle === 'second' ? 'Second cycle' : 'Premier cycle'),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Niveaux d'étude</h1>
          <p className="page-subtitle">6ème à Terminale</p>
        </div>
        <button type="button" className="btn-primary" onClick={() => setModalOpen(true)}>
          + Nouveau niveau
        </button>
      </div>
      <Table columns={columns} data={niveaux} loading={loading} emptyMessage="Aucun niveau" />
      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Nouveau niveau">
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField
            label="Libellé"
            value={form.libelle}
            onChange={(e) => setForm({ ...form, libelle: e.target.value })}
            required
          />
          <FormField
            label="Ordre"
            type="number"
            value={form.ordre}
            onChange={(e) => setForm({ ...form, ordre: e.target.value })}
            required
          />
          <FormField
            label="Cycle"
            name="cycle"
            type="select"
            value={form.cycle}
            onChange={(e) => setForm({ ...form, cycle: e.target.value })}
            options={[
              { value: 'premier', label: 'Premier cycle' },
              { value: 'second', label: 'Second cycle' },
            ]}
          />
          <button type="submit" className="btn-primary w-full">
            Enregistrer
          </button>
        </form>
      </Modal>
    </div>
  );
}
