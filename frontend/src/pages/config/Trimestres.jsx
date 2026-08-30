import { useCallback, useEffect, useRef, useState } from 'react';
import { configApi } from '../../services/api/config';
import Table from '../../components/Table';
import { emptyIcons } from '../../utils/emptyIcons';
import FormField from '../../components/FormField';
import Modal from '../../components/Modal';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';

export default function Trimestres() {
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;

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
    configApi
      .listAnnees()
      .then((data) => {
        const list = data.items || data || [];
        setAnnees(list);
        const active = list.find((a) => a.est_active) || list[0];
        if (active) setAnneeId(String(active.id));
      })
      .catch(() => toastRef.current.error('Impossible de charger les années. Réessayez.'));
  }, []);

  const load = useCallback(async () => {
    if (!anneeId) return;
    setLoading(true);
    try {
      const data = await configApi.listTrimestres(anneeId);
      setTrimestres(Array.isArray(data) ? data : data.items || []);
    } catch {
      toastRef.current.error('Impossible de charger les trimestres. Réessayez.');
    } finally {
      setLoading(false);
    }
  }, [anneeId]);

  useEffect(() => {
    load();
  }, [load]);

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
      toast.error(err.response?.data?.message || 'Erreur lors de l\'enregistrement');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Supprimer ce trimestre ?')) return;
    try {
      await configApi.deleteTrimestre(id);
      toast.success('Trimestre supprimé');
      load();
    } catch {
      toast.error('Impossible de supprimer ce trimestre');
    }
  };

  const columns = [
    {
      key: 'numero',
      header: 'N°',
      render: (r) => `Trimestre ${r.numero}`,
    },
    { key: 'date_debut', header: 'Début' },
    { key: 'date_fin', header: 'Fin' },
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
        title="Trimestres"
        subtitle="Périodes d'évaluation par année scolaire"
        actions={
          <>
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
          </>
        }
      />

      <Table
        columns={columns}
        data={trimestres}
        loading={loading}
        emptyIcon={emptyIcons.trimestres}
        emptyMessage="Aucun trimestre pour l'instant — ajoutez-en un pour cette année scolaire."
      />

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
