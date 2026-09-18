import { useCallback, useEffect, useState } from 'react';
import { elearningApi } from '../../services/api/elearning';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';

export default function Devoirs() {
  const toast = useToast();
  const { isEnseignant, isAdmin } = useAuth();
  const canWrite = isEnseignant || isAdmin;
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    titre: '',
    consignes: '',
    id_classe: '',
    date_limite: '',
    note_max: '20',
    publie: true,
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await elearningApi.listDevoirs();
      setRows(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Impossible de charger les devoirs');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const create = async (e) => {
    e.preventDefault();
    try {
      await elearningApi.createDevoir({
        titre: form.titre,
        consignes: form.consignes || null,
        id_classe: form.id_classe || null,
        date_limite: form.date_limite || null,
        note_max: form.note_max || '20',
        publie: form.publie,
      });
      toast.success('Devoir créé');
      setForm({ titre: '', consignes: '', id_classe: '', date_limite: '', note_max: '20', publie: true });
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="E-learning" title="Devoirs" subtitle="Travaux à rendre et consignes" />

      {canWrite && (
        <form onSubmit={create} className="card-premium grid gap-3 p-5 sm:grid-cols-2">
          <FormField label="Titre" name="titre" value={form.titre} onChange={(e) => setForm((f) => ({ ...f, titre: e.target.value }))} required />
          <FormField label="ID classe" name="id_classe" value={form.id_classe} onChange={(e) => setForm((f) => ({ ...f, id_classe: e.target.value }))} />
          <FormField label="Date limite" name="date_limite" type="datetime-local" value={form.date_limite} onChange={(e) => setForm((f) => ({ ...f, date_limite: e.target.value }))} />
          <FormField label="Note max" name="note_max" value={form.note_max} onChange={(e) => setForm((f) => ({ ...f, note_max: e.target.value }))} />
          <FormField label="Consignes" name="consignes" type="textarea" value={form.consignes} onChange={(e) => setForm((f) => ({ ...f, consignes: e.target.value }))} />
          <button type="submit" className="btn-primary w-fit">Publier</button>
        </form>
      )}

      <Table
        columns={[
          { key: 'titre', header: 'Titre' },
          {
            key: 'date_limite',
            header: 'Échéance',
            render: (r) => (r.date_limite ? new Date(r.date_limite).toLocaleString('fr-FR') : '—'),
          },
          { key: 'publie', header: 'Publié', render: (r) => (r.publie ? 'Oui' : 'Non') },
          { key: 'consignes', header: 'Consignes', render: (r) => (r.consignes ? String(r.consignes).slice(0, 60) : '—') },
        ]}
        data={rows}
        loading={loading}
        emptyMessage="Aucun devoir."
      />
    </div>
  );
}
