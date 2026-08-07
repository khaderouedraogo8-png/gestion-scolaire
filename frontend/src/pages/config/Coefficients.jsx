import { useEffect, useState } from 'react';
import { notesApi } from '../../services/api/notes';
import { configApi } from '../../services/api/config';
import FormField from '../../components/FormField';
import Modal from '../../components/Modal';
import { useToast } from '../../components/Toast';

export default function Coefficients() {
  const toast = useToast();
  const [coefficients, setCoefficients] = useState([]);
  const [matieres, setMatieres] = useState([]);
  const [niveaux, setNiveaux] = useState([]);
  const [niveauFilter, setNiveauFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState({ id_matiere: '', id_niveau: '', coefficient: '1' });

  const load = async () => {
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
      toast.error('Erreur chargement coefficients');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [niveauFilter]);

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
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const handleDelete = async (id) => {
    try {
      await notesApi.deleteCoefficient(id);
      toast.success('Coefficient supprimé');
      load();
    } catch {
      toast.error('Erreur suppression');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Coefficients par niveau</h1>
          <p className="text-sm text-slate-500">Pondération des matières pour le calcul des moyennes</p>
        </div>
        <button type="button" onClick={() => setModal(true)} className="btn-primary">
          + Coefficient
        </button>
      </div>

      <select value={niveauFilter} onChange={(e) => setNiveauFilter(e.target.value)} className="input w-auto">
        <option value="">Tous les niveaux</option>
        {niveaux.map((n) => (
          <option key={n.id} value={n.id}>
            {n.libelle}
          </option>
        ))}
      </select>

      {loading ? (
        <p className="text-slate-500">Chargement...</p>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Matière</th>
                <th className="px-4 py-3">Niveau</th>
                <th className="px-4 py-3">Coefficient</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {coefficients.map((c) => (
                <tr key={c.id} className="border-t border-slate-100">
                  <td className="px-4 py-3">{c.matiere_libelle}</td>
                  <td className="px-4 py-3">{c.niveau_libelle}</td>
                  <td className="px-4 py-3 font-medium">{c.coefficient}</td>
                  <td className="px-4 py-3 text-right">
                    <button type="button" onClick={() => handleDelete(c.id)} className="text-red-600 hover:underline">
                      Supprimer
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

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
