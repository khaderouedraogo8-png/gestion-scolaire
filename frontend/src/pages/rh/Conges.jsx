import { useCallback, useEffect, useState } from 'react';
import { rhApi } from '../../services/api/rh';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function Conges() {
  const toast = useToast();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    id_utilisateur: '',
    type_conge: 'annuel',
    date_debut: '',
    date_fin: '',
    motif: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await rhApi.listConges();
      setRows(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Impossible de charger les congés');
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
      await rhApi.createConge(form);
      toast.success('Demande enregistrée');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const setStatut = async (id, statut) => {
    try {
      await rhApi.patchCongeStatut(id, statut);
      toast.success(`Congé ${statut}`);
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="RH" title="Congés" subtitle="Demandes et validations" />

      <form onSubmit={create} className="card-premium grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-3">
        <FormField label="ID utilisateur" name="id_utilisateur" value={form.id_utilisateur} onChange={(e) => setForm((f) => ({ ...f, id_utilisateur: e.target.value }))} required />
        <FormField
          label="Type"
          name="type_conge"
          type="select"
          value={form.type_conge}
          onChange={(e) => setForm((f) => ({ ...f, type_conge: e.target.value }))}
          options={[
            { value: 'annuel', label: 'Annuel' },
            { value: 'maladie', label: 'Maladie' },
            { value: 'exceptionnel', label: 'Exceptionnel' },
            { value: 'maternite', label: 'Maternité' },
          ]}
        />
        <FormField label="Début" name="date_debut" type="date" value={form.date_debut} onChange={(e) => setForm((f) => ({ ...f, date_debut: e.target.value }))} required />
        <FormField label="Fin" name="date_fin" type="date" value={form.date_fin} onChange={(e) => setForm((f) => ({ ...f, date_fin: e.target.value }))} required />
        <FormField label="Motif" name="motif" value={form.motif} onChange={(e) => setForm((f) => ({ ...f, motif: e.target.value }))} />
        <div className="flex items-end">
          <button type="submit" className="btn-primary w-full">Demander</button>
        </div>
      </form>

      <Table
        columns={[
          { key: 'id_utilisateur', header: 'Utilisateur', render: (r) => String(r.id_utilisateur).slice(0, 8) },
          { key: 'type_conge', header: 'Type' },
          { key: 'date_debut', header: 'Début' },
          { key: 'date_fin', header: 'Fin' },
          { key: 'statut', header: 'Statut' },
          {
            key: 'actions',
            header: '',
            render: (r) =>
              r.statut === 'demande' ? (
                <span className="flex gap-2">
                  <button type="button" className="text-xs font-medium text-emerald-700 hover:underline" onClick={() => setStatut(r.id, 'approuve')}>
                    Approuver
                  </button>
                  <button type="button" className="text-xs font-medium text-brique hover:underline" onClick={() => setStatut(r.id, 'refuse')}>
                    Refuser
                  </button>
                </span>
              ) : null,
          },
        ]}
        data={rows}
        loading={loading}
        emptyMessage="Aucun congé."
      />
    </div>
  );
}
