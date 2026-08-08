import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { notesApi } from '../../services/api/notes';
import FormField from '../../components/FormField';
import Modal from '../../components/Modal';
import { useToast } from '../../components/Toast';

export default function Matieres() {
  const toast = useToast();
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
      toast.error('Erreur chargement matières');
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
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Supprimer cette matière ?')) return;
    try {
      await notesApi.deleteMatiere(id);
      toast.success('Matière supprimée');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur suppression');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-or-cachet-clair border-t-or-cachet" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Matières</h1>
          <p className="page-subtitle">Référentiel des matières enseignées</p>
        </div>
        <button type="button" onClick={openCreate} className="btn-primary">
          + Nouvelle matière
        </button>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-craie text-left text-xs uppercase text-texte-secondaire">
            <tr>
              <th className="px-4 py-3">Libellé</th>
              <th className="px-4 py-3">Code</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {matieres.map((m) => (
              <tr key={m.id} className="border-t border-bordure/50">
                <td className="px-4 py-3 font-medium">{m.libelle}</td>
                <td className="px-4 py-3">{m.code || '—'}</td>
                <td className="px-4 py-3 text-right">
                  <button type="button" onClick={() => openEdit(m)} className="text-or-cachet hover:underline">
                    Modifier
                  </button>
                  <button type="button" onClick={() => handleDelete(m.id)} className="ml-3 text-brique hover:underline">
                    Supprimer
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

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
