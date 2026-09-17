import { useCallback, useEffect, useState } from 'react';
import { rhApi } from '../../services/api/rh';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function Contrats() {
  const toast = useToast();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    type_contrat: 'cdi',
    date_debut: new Date().toISOString().slice(0, 10),
    date_fin: '',
    salaire_base: '',
    poste: '',
    id_utilisateur: '',
    id_enseignant: '',
    statut: 'actif',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await rhApi.listContrats();
      setRows(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Impossible de charger les contrats');
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
      await rhApi.createContrat({
        type_contrat: form.type_contrat,
        date_debut: form.date_debut,
        date_fin: form.date_fin || null,
        salaire_base: form.salaire_base || null,
        poste: form.poste || null,
        id_utilisateur: form.id_utilisateur || null,
        id_enseignant: form.id_enseignant || null,
        statut: form.statut,
      });
      toast.success('Contrat créé');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="RH" title="Contrats" subtitle="Contrats du personnel" />

      <form onSubmit={create} className="card-premium grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-3">
        <FormField
          label="Type"
          name="type_contrat"
          type="select"
          value={form.type_contrat}
          onChange={(e) => setForm((f) => ({ ...f, type_contrat: e.target.value }))}
          options={[
            { value: 'cdi', label: 'CDI' },
            { value: 'cdd', label: 'CDD' },
            { value: 'vacation', label: 'Vacation' },
            { value: 'stage', label: 'Stage' },
          ]}
        />
        <FormField label="Poste" name="poste" value={form.poste} onChange={(e) => setForm((f) => ({ ...f, poste: e.target.value }))} />
        <FormField label="Début" name="date_debut" type="date" value={form.date_debut} onChange={(e) => setForm((f) => ({ ...f, date_debut: e.target.value }))} required />
        <FormField label="Fin" name="date_fin" type="date" value={form.date_fin} onChange={(e) => setForm((f) => ({ ...f, date_fin: e.target.value }))} />
        <FormField label="Salaire base" name="salaire_base" value={form.salaire_base} onChange={(e) => setForm((f) => ({ ...f, salaire_base: e.target.value }))} />
        <FormField label="ID utilisateur" name="id_utilisateur" value={form.id_utilisateur} onChange={(e) => setForm((f) => ({ ...f, id_utilisateur: e.target.value }))} />
        <button type="submit" className="btn-primary w-fit">Créer le contrat</button>
      </form>

      <Table
        columns={[
          { key: 'poste', header: 'Poste', render: (r) => r.poste || '—' },
          { key: 'type_contrat', header: 'Type' },
          { key: 'date_debut', header: 'Début' },
          { key: 'date_fin', header: 'Fin', render: (r) => r.date_fin || '—' },
          {
            key: 'salaire_base',
            header: 'Salaire',
            render: (r) => (r.salaire_base != null ? `${Number(r.salaire_base).toLocaleString('fr-FR')} FCFA` : '—'),
          },
          { key: 'statut', header: 'Statut' },
        ]}
        data={rows}
        loading={loading}
        emptyMessage="Aucun contrat."
      />
    </div>
  );
}
