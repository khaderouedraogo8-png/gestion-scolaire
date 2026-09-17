import { useCallback, useEffect, useState } from 'react';
import { vieScolaireApi } from '../../services/api/vieScolaire';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function Cantine() {
  const toast = useToast();
  const [abonnements, setAbonnements] = useState([]);
  const [presences, setPresences] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    id_eleve: '',
    formule: 'standard',
    montant: '',
    date_debut: new Date().toISOString().slice(0, 10),
  });
  const [presenceForm, setPresenceForm] = useState({
    id_eleve: '',
    date_presence: new Date().toISOString().slice(0, 10),
    repas: 'midi',
    present: true,
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [a, p] = await Promise.all([
        vieScolaireApi.listCantineAbonnements(),
        vieScolaireApi.listCantinePresences(),
      ]);
      setAbonnements(Array.isArray(a) ? a : []);
      setPresences(Array.isArray(p) ? p : []);
    } catch {
      toast.error('Impossible de charger la cantine');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const createAbo = async (e) => {
    e.preventDefault();
    try {
      await vieScolaireApi.createCantineAbonnement({
        ...form,
        montant: form.montant || null,
      });
      toast.success('Abonnement créé');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const createPresence = async (e) => {
    e.preventDefault();
    try {
      await vieScolaireApi.createCantinePresence(presenceForm);
      toast.success('Présence enregistrée');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Vie scolaire" title="Cantine" subtitle="Abonnements et présences repas" />

      <form onSubmit={createAbo} className="card-premium grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4">
        <FormField label="ID élève" name="id_eleve" value={form.id_eleve} onChange={(e) => setForm((f) => ({ ...f, id_eleve: e.target.value }))} required />
        <FormField label="Formule" name="formule" value={form.formule} onChange={(e) => setForm((f) => ({ ...f, formule: e.target.value }))} />
        <FormField label="Montant" name="montant" value={form.montant} onChange={(e) => setForm((f) => ({ ...f, montant: e.target.value }))} />
        <FormField label="Début" name="date_debut" type="date" value={form.date_debut} onChange={(e) => setForm((f) => ({ ...f, date_debut: e.target.value }))} required />
        <button type="submit" className="btn-primary sm:col-span-2 lg:col-span-4 w-fit">Nouvel abonnement</button>
      </form>

      <Table
        columns={[
          { key: 'id_eleve', header: 'Élève', render: (r) => String(r.id_eleve).slice(0, 8) },
          { key: 'formule', header: 'Formule' },
          { key: 'montant', header: 'Montant', render: (r) => (r.montant != null ? `${r.montant} FCFA` : '—') },
          { key: 'date_debut', header: 'Début' },
          { key: 'actif', header: 'Actif', render: (r) => (r.actif ? 'Oui' : 'Non') },
        ]}
        data={abonnements}
        loading={loading}
        emptyMessage="Aucun abonnement cantine."
      />

      <form onSubmit={createPresence} className="card-premium grid gap-3 p-5 sm:grid-cols-4">
        <FormField label="ID élève" name="p_eleve" value={presenceForm.id_eleve} onChange={(e) => setPresenceForm((f) => ({ ...f, id_eleve: e.target.value }))} required />
        <FormField label="Date" name="date_presence" type="date" value={presenceForm.date_presence} onChange={(e) => setPresenceForm((f) => ({ ...f, date_presence: e.target.value }))} />
        <FormField label="Repas" name="repas" value={presenceForm.repas} onChange={(e) => setPresenceForm((f) => ({ ...f, repas: e.target.value }))} />
        <div className="flex items-end">
          <button type="submit" className="btn-secondary w-full">Pointer présence</button>
        </div>
      </form>

      <Table
        columns={[
          { key: 'id_eleve', header: 'Élève', render: (r) => String(r.id_eleve).slice(0, 8) },
          { key: 'date_presence', header: 'Date' },
          { key: 'repas', header: 'Repas' },
          { key: 'present', header: 'Présent', render: (r) => (r.present ? 'Oui' : 'Non') },
        ]}
        data={presences.slice(0, 50)}
        loading={false}
        emptyMessage="Aucune présence."
      />
    </div>
  );
}
