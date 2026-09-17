import { useCallback, useEffect, useState } from 'react';
import { frontOfficeApi } from '../../services/api/frontOffice';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function Sorties() {
  const toast = useToast();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ id_eleve: '', motif: '', recupere_par: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await frontOfficeApi.listSorties();
      setRows(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Impossible de charger les sorties');
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
      await frontOfficeApi.createSortie(form);
      toast.success('Sortie enregistrée');
      setForm({ id_eleve: '', motif: '', recupere_par: '' });
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const retour = async (id) => {
    try {
      await frontOfficeApi.retourSortie(id);
      toast.success('Retour enregistré');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Accueil" title="Sorties élèves" subtitle="Autorisations de sortie anticipée" />

      <form onSubmit={create} className="card-premium grid gap-3 p-5 sm:grid-cols-3">
        <FormField label="ID élève" name="id_eleve" value={form.id_eleve} onChange={(e) => setForm((f) => ({ ...f, id_eleve: e.target.value }))} required />
        <FormField label="Motif" name="motif" value={form.motif} onChange={(e) => setForm((f) => ({ ...f, motif: e.target.value }))} />
        <FormField label="Récupéré par" name="recupere_par" value={form.recupere_par} onChange={(e) => setForm((f) => ({ ...f, recupere_par: e.target.value }))} />
        <button type="submit" className="btn-primary w-fit">Enregistrer la sortie</button>
      </form>

      <Table
        columns={[
          { key: 'id_eleve', header: 'Élève', render: (r) => String(r.id_eleve).slice(0, 8) },
          { key: 'motif', header: 'Motif', render: (r) => r.motif || '—' },
          { key: 'recupere_par', header: 'Récupéré par', render: (r) => r.recupere_par || '—' },
          { key: 'statut', header: 'Statut' },
          {
            key: 'actions',
            header: '',
            render: (r) =>
              r.statut === 'sorti' && !r.heure_retour ? (
                <button type="button" className="text-sm font-medium text-or-cachet hover:underline" onClick={() => retour(r.id)}>
                  Retour
                </button>
              ) : (
                '—'
              ),
          },
        ]}
        data={rows}
        loading={loading}
        emptyMessage="Aucune sortie."
      />
    </div>
  );
}
