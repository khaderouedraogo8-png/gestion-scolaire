import { useCallback, useEffect, useRef, useState } from 'react';
import { notesApi } from '../../services/api/notes';
import { configApi } from '../../services/api/config';
import Table from '../../components/Table';
import { emptyIcons } from '../../utils/emptyIcons';
import FormField from '../../components/FormField';
import Modal from '../../components/Modal';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';

export default function Coefficients() {
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;

  const [coefficients, setCoefficients] = useState([]);
  const [matieres, setMatieres] = useState([]);
  const [niveaux, setNiveaux] = useState([]);
  const [niveauFilter, setNiveauFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState({ id_matiere: '', id_niveau: '', coefficient: '1' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [coefs, mats, nivs] = await Promise.all([
        notesApi.listCoefficients(niveauFilter ? { id_niveau: niveauFilter } : {}),
        notesApi.listMatieres(),
        configApi.listNiveaux(),
      ]);
      setCoefficients(Array.isArray(coefs) ? coefs : []);
      setMatieres(Array.isArray(mats) ? mats : []);
      setNiveaux(Array.isArray(nivs) ? nivs : nivs.items || []);
    } catch {
      toastRef.current.error('Impossible de charger les coefficients. Réessayez.');
    } finally {
      setLoading(false);
    }
  }, [niveauFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await notesApi.saveCoefficient({
        id_matiere: form.id_matiere,
        id_niveau: form.id_niveau,
        coefficient: Number(form.coefficient),
      });
      toast.success('Coefficient enregistré');
      setModal(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur lors de l\'enregistrement');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Supprimer ce coefficient ?')) return;
    try {
      await notesApi.deleteCoefficient(id);
      toast.success('Coefficient supprimé');
      load();
    } catch {
      toast.error('Impossible de supprimer ce coefficient');
    }
  };

  const columns = [
    { key: 'matiere', header: 'Matière', render: (r) => r.matiere_libelle },
    { key: 'niveau', header: 'Niveau', render: (r) => r.niveau_libelle },
    {
      key: 'coefficient',
      header: 'Coefficient',
      align: 'right',
      render: (r) => <span className="font-medium tabular-nums">{r.coefficient}</span>,
    },
    {
      key: 'actions',
      header: '',
      render: (r) => (
        <button type="button" onClick={() => handleDelete(r.id)} className="text-brique hover:underline">
          Supprimer
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Configuration"
        title="Coefficients par niveau"
        subtitle="Pondération des matières pour le calcul des moyennes"
        actions={
          <button type="button" onClick={() => setModal(true)} className="btn-primary">
            + Coefficient
          </button>
        }
      />

      <Table
        columns={columns}
        data={coefficients}
        loading={loading}
        filters={
          <select value={niveauFilter} onChange={(e) => setNiveauFilter(e.target.value)} className="input w-auto">
            <option value="">Tous les niveaux</option>
            {niveaux.map((n) => (
              <option key={n.id} value={n.id}>
                {n.libelle}
              </option>
            ))}
          </select>
        }
        emptyIcon={emptyIcons.coefficients}
        emptyMessage="Aucun coefficient pour l'instant — ajoutez-en un via le bouton ci-dessus."
      />

      <Modal isOpen={modal} onClose={() => setModal(false)} title="Nouveau coefficient">
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField
            label="Matière"
            type="select"
            value={form.id_matiere}
            onChange={(e) => setForm({ ...form, id_matiere: e.target.value })}
            required
            options={matieres.map((m) => ({ value: m.id, label: m.libelle }))}
          />
          <FormField
            label="Niveau"
            type="select"
            value={form.id_niveau}
            onChange={(e) => setForm({ ...form, id_niveau: e.target.value })}
            required
            options={niveaux.map((n) => ({ value: n.id, label: n.libelle }))}
          />
          <FormField
            label="Coefficient"
            type="number"
            value={form.coefficient}
            onChange={(e) => setForm({ ...form, coefficient: e.target.value })}
            required
          />
          <button type="submit" className="btn-primary w-full">
            Enregistrer
          </button>
        </form>
      </Modal>
    </div>
  );
}
