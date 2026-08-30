import { useEffect, useRef, useState } from 'react';
import { notesApi } from '../../services/api/notes';
import Table from '../../components/Table';
import { emptyIcons } from '../../utils/emptyIcons';
import FormField from '../../components/FormField';
import Modal from '../../components/Modal';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';

export default function Matieres() {
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;

  const [matieres, setMatieres] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState({ libelle: '', code: '' });
  const [editId, setEditId] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await notesApi.listMatieres();
      setMatieres(Array.isArray(data) ? data : []);
    } catch {
      toastRef.current.error('Impossible de charger les matières. Réessayez.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const openCreate = () => {
    setEditId(null);
    setForm({ libelle: '', code: '' });
    setModal(true);
  };

  const openEdit = (m) => {
    setEditId(m.id);
    setForm({ libelle: m.libelle, code: m.code || '' });
    setModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editId) {
        await notesApi.updateMatiere(editId, form);
        toast.success('Matière mise à jour');
      } else {
        await notesApi.createMatiere(form);
        toast.success('Matière créée');
      }
      setModal(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur lors de l\'enregistrement');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Supprimer cette matière ?')) return;
    try {
      await notesApi.deleteMatiere(id);
      toast.success('Matière supprimée');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Impossible de supprimer cette matière');
    }
  };

  const columns = [
    {
      key: 'libelle',
      header: 'Libellé',
      render: (r) => <span className="font-medium">{r.libelle}</span>,
    },
    { key: 'code', header: 'Code', render: (r) => r.code || '—' },
    {
      key: 'actions',
      header: '',
      render: (r) => (
        <div className="space-x-3 text-right">
          <button type="button" onClick={() => openEdit(r)} className="text-or-cachet hover:underline">
            Modifier
          </button>
          <button type="button" onClick={() => handleDelete(r.id)} className="text-brique hover:underline">
            Supprimer
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Configuration"
        title="Matières"
        subtitle="Référentiel des matières enseignées"
        actions={
          <button type="button" onClick={openCreate} className="btn-primary">
            + Nouvelle matière
          </button>
        }
      />

      <Table
        columns={columns}
        data={matieres}
        loading={loading}
        emptyIcon={emptyIcons.matieres}
        emptyMessage="Aucune matière pour l'instant — créez-en une via le bouton ci-dessus."
      />

      <Modal isOpen={modal} onClose={() => setModal(false)} title={editId ? 'Modifier matière' : 'Nouvelle matière'}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField label="Libellé" value={form.libelle} onChange={(e) => setForm({ ...form, libelle: e.target.value })} required />
          <FormField label="Code" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
          <button type="submit" className="btn-primary w-full">
            Enregistrer
          </button>
        </form>
      </Modal>
    </div>
  );
}
