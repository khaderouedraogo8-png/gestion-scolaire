import { useCallback, useEffect, useState } from 'react';
import { frontOfficeApi } from '../../services/api/frontOffice';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function Visiteurs() {
  const toast = useToast();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    nom: '',
    prenom: '',
    motif: '',
    telephone: '',
    piece_identite: '',
    id_eleve_visite: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await frontOfficeApi.listVisiteurs();
      setRows(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Impossible de charger les visiteurs');
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
      await frontOfficeApi.createVisiteur({
        ...form,
        id_eleve_visite: form.id_eleve_visite || null,
      });
      toast.success('Visiteur enregistré');
      setForm({ nom: '', prenom: '', motif: '', telephone: '', piece_identite: '', id_eleve_visite: '' });
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const sortie = async (id) => {
    try {
      await frontOfficeApi.sortieVisiteur(id);
      toast.success('Sortie enregistrée');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Accueil" title="Visiteurs" subtitle="Registre d’entrée et sortie" />

      <form onSubmit={create} className="card-premium grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-3">
        <FormField label="Nom" name="nom" value={form.nom} onChange={(e) => setForm((f) => ({ ...f, nom: e.target.value }))} required />
        <FormField label="Prénom" name="prenom" value={form.prenom} onChange={(e) => setForm((f) => ({ ...f, prenom: e.target.value }))} />
        <FormField label="Motif" name="motif" value={form.motif} onChange={(e) => setForm((f) => ({ ...f, motif: e.target.value }))} />
        <FormField label="Téléphone" name="telephone" value={form.telephone} onChange={(e) => setForm((f) => ({ ...f, telephone: e.target.value }))} />
        <FormField label="Pièce d’identité" name="piece_identite" value={form.piece_identite} onChange={(e) => setForm((f) => ({ ...f, piece_identite: e.target.value }))} />
        <FormField label="ID élève visité" name="id_eleve_visite" value={form.id_eleve_visite} onChange={(e) => setForm((f) => ({ ...f, id_eleve_visite: e.target.value }))} />
        <button type="submit" className="btn-primary w-fit">Enregistrer l’entrée</button>
      </form>

      <Table
        columns={[
          { key: 'nom', header: 'Visiteur', render: (r) => `${r.prenom || ''} ${r.nom}`.trim() },
          { key: 'motif', header: 'Motif', render: (r) => r.motif || '—' },
          {
            key: 'heure_entree',
            header: 'Entrée',
            render: (r) => (r.heure_entree ? new Date(r.heure_entree).toLocaleString('fr-FR') : '—'),
          },
          {
            key: 'heure_sortie',
            header: 'Sortie',
            render: (r) =>
              r.heure_sortie ? (
                new Date(r.heure_sortie).toLocaleString('fr-FR')
              ) : (
                <button type="button" className="text-sm font-medium text-or-cachet hover:underline" onClick={() => sortie(r.id)}>
                  Marquer sortie
                </button>
              ),
          },
        ]}
        data={rows}
        loading={loading}
        emptyMessage="Aucun visiteur."
      />
    </div>
  );
}
