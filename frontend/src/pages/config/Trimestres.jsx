import { useEffect, useState } from 'react';
import { configApi } from '../../services/api/config';
import FormField from '../../components/FormField';
import Modal from '../../components/Modal';
import { useToast } from '../../components/Toast';

export default function Trimestres() {
  const toast = useToast();
  const [annees, setAnnees] = useState([]);
  const [anneeId, setAnneeId] = useState('');
  const [trimestres, setTrimestres] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState({
    numero: '1',
    date_debut: '',
    date_fin: '',
  });

  useEffect(() => {
    configApi.listAnnees().then((data) => {
      const list = data.items || data || [];
      setAnnees(list);
      const active = list.find((a) => a.est_active) || list[0];
      if (active) setAnneeId(String(active.id));
    });
  }, []);

  const load = async () => {
    if (!anneeId) return;
    setLoading(true);
    try {
      const data = await configApi.listTrimestres(anneeId);
      setTrimestres(Array.isArray(data) ? data : data.items || []);
    } catch {
      toast.error('Erreur chargement trimestres');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [anneeId]);

  const openCreate = () => {
    setEditId(null);
    setForm({ numero: '1', date_debut: '', date_fin: '' });
    setModal(true);
  };

  const openEdit = (t) => {
    setEditId(t.id);
    setForm({
      numero: String(t.numero),
      date_debut: t.date_debut,
      date_fin: t.date_fin,
    });
    setModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = {
      id_annee: anneeId,
      numero: Number(form.numero),
      date_debut: form.date_debut,
      date_fin: form.date_fin,
    };
    try {
      if (editId) {
        await configApi.updateTrimestre(editId, payload);
        toast.success('Trimestre mis à jour');
      } else {
        await configApi.createTrimestre(payload);
        toast.success('Trimestre créé');
      }
      setModal(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Supprimer ce trimestre ?')) return;
    try {
      await configApi.deleteTrimestre(id);
      toast.success('Trimestre supprimé');
      load();
    } catch {
      toast.error('Erreur suppression');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Trimestres</h1>
          <p className="text-sm text-slate-500">Périodes d'évaluation par année scolaire</p>
        </div>
        <div className="flex gap-2">
          <select
            className="input w-auto"
            value={anneeId}
            onChange={(e) => setAnneeId(e.target.value)}
          >
            {annees.map((a) => (
              <option key={a.id} value={a.id}>
                {a.libelle}
              </option>
            ))}
          </select>
          <button type="button" onClick={openCreate} className="btn-primary">
            + Trimestre
          </button>
        </div>
      </div>

      {loading ? (
        <p className="text-slate-500">Chargement…</p>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">N°</th>
                <th className="px-4 py-3">Début</th>
                <th className="px-4 py-3">Fin</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {trimestres.map((t) => (
                <tr key={t.id} className="border-t border-slate-100">
                  <td className="px-4 py-3">Trimestre {t.numero}</td>
                  <td className="px-4 py-3">{t.date_debut}</td>
                  <td className="px-4 py-3">{t.date_fin}</td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <button type="button" onClick={() => openEdit(t)} className="text-primary-600 hover:underline">
                      Modifier
                    </button>
                    <button type="button" onClick={() => handleDelete(t.id)} className="text-red-600 hover:underline">
                      Supprimer
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal
        isOpen={modal}
        onClose={() => setModal(false)}
        title={editId ? 'Modifier le trimestre' : 'Nouveau trimestre'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField
            label="Numéro"
            type="select"
            value={form.numero}
            onChange={(e) => setForm({ ...form, numero: e.target.value })}
            options={[
              { value: '1', label: 'Trimestre 1' },
              { value: '2', label: 'Trimestre 2' },
              { value: '3', label: 'Trimestre 3' },
            ]}
            required
          />
          <FormField
            label="Date début"
            type="date"
            value={form.date_debut}
            onChange={(e) => setForm({ ...form, date_debut: e.target.value })}
            required
          />
          <FormField
            label="Date fin"
            type="date"
            value={form.date_fin}
            onChange={(e) => setForm({ ...form, date_fin: e.target.value })}
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
