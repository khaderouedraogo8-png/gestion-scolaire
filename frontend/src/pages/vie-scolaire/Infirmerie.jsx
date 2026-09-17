import { useCallback, useEffect, useState } from 'react';
import { vieScolaireApi } from '../../services/api/vieScolaire';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function Infirmerie() {
  const toast = useToast();
  const [soins, setSoins] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    id_eleve: '',
    motif: '',
    traitement: '',
    notes: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await vieScolaireApi.listInfirmerieSoins();
      setSoins(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Impossible de charger l’infirmerie');
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
      await vieScolaireApi.createInfirmerieSoin(form);
      toast.success('Soin enregistré');
      setForm((f) => ({ ...f, motif: '', traitement: '', notes: '' }));
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Vie scolaire" title="Infirmerie" subtitle="Registre des soins" />

      <form onSubmit={create} className="card-premium grid gap-3 p-5 sm:grid-cols-2">
        <FormField label="ID élève" name="id_eleve" value={form.id_eleve} onChange={(e) => setForm((f) => ({ ...f, id_eleve: e.target.value }))} required />
        <FormField label="Motif" name="motif" value={form.motif} onChange={(e) => setForm((f) => ({ ...f, motif: e.target.value }))} required />
        <FormField label="Traitement" name="traitement" value={form.traitement} onChange={(e) => setForm((f) => ({ ...f, traitement: e.target.value }))} />
        <FormField label="Notes" name="notes" type="textarea" value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))} />
        <button type="submit" className="btn-primary w-fit">Enregistrer</button>
      </form>

      <Table
        columns={[
          { key: 'date_soin', header: 'Date', render: (r) => r.date_soin || r.created_at?.slice(0, 10) },
          { key: 'id_eleve', header: 'Élève', render: (r) => String(r.id_eleve).slice(0, 8) },
          { key: 'motif', header: 'Motif' },
          { key: 'traitement', header: 'Traitement', render: (r) => r.traitement || '—' },
        ]}
        data={soins}
        loading={loading}
        emptyMessage="Aucun soin enregistré."
      />
    </div>
  );
}
