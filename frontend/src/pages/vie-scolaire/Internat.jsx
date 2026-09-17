import { useCallback, useEffect, useState } from 'react';
import { vieScolaireApi } from '../../services/api/vieScolaire';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function Internat() {
  const toast = useToast();
  const [chambres, setChambres] = useState([]);
  const [affectations, setAffectations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [chambre, setChambre] = useState({ numero: '', capacite: '4', batiment: '', genre: '' });
  const [aff, setAff] = useState({ id_eleve: '', id_chambre: '', date_debut: new Date().toISOString().slice(0, 10) });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [c, a] = await Promise.all([
        vieScolaireApi.listInternatChambres(),
        vieScolaireApi.listInternatAffectations(),
      ]);
      setChambres(Array.isArray(c) ? c : []);
      setAffectations(Array.isArray(a) ? a : []);
    } catch {
      toast.error('Impossible de charger l’internat');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const createChambre = async (e) => {
    e.preventDefault();
    try {
      await vieScolaireApi.createInternatChambre({
        numero: chambre.numero,
        capacite: Number(chambre.capacite) || 4,
        batiment: chambre.batiment || null,
        genre: chambre.genre || null,
      });
      toast.success('Chambre créée');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const createAff = async (e) => {
    e.preventDefault();
    try {
      await vieScolaireApi.createInternatAffectation(aff);
      toast.success('Affectation enregistrée');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Vie scolaire" title="Internat" subtitle="Chambres et affectations" />

      <form onSubmit={createChambre} className="card-premium grid gap-3 p-5 sm:grid-cols-4">
        <FormField label="Numéro" name="numero" value={chambre.numero} onChange={(e) => setChambre((f) => ({ ...f, numero: e.target.value }))} required />
        <FormField label="Capacité" name="capacite" value={chambre.capacite} onChange={(e) => setChambre((f) => ({ ...f, capacite: e.target.value }))} />
        <FormField label="Bâtiment" name="batiment" value={chambre.batiment} onChange={(e) => setChambre((f) => ({ ...f, batiment: e.target.value }))} />
        <div className="flex items-end">
          <button type="submit" className="btn-primary w-full">Ajouter</button>
        </div>
      </form>

      <Table
        columns={[
          { key: 'numero', header: 'N°' },
          { key: 'batiment', header: 'Bâtiment', render: (r) => r.batiment || '—' },
          { key: 'capacite', header: 'Capacité' },
        ]}
        data={chambres}
        loading={loading}
        emptyMessage="Aucune chambre."
      />

      <form onSubmit={createAff} className="card-premium grid gap-3 p-5 sm:grid-cols-4">
        <FormField label="ID élève" name="id_eleve" value={aff.id_eleve} onChange={(e) => setAff((f) => ({ ...f, id_eleve: e.target.value }))} required />
        <FormField
          label="Chambre"
          name="id_chambre"
          type="select"
          value={aff.id_chambre}
          onChange={(e) => setAff((f) => ({ ...f, id_chambre: e.target.value }))}
          options={chambres.map((c) => ({ value: String(c.id), label: c.numero }))}
        />
        <FormField label="Début" name="date_debut" type="date" value={aff.date_debut} onChange={(e) => setAff((f) => ({ ...f, date_debut: e.target.value }))} />
        <div className="flex items-end">
          <button type="submit" className="btn-secondary w-full">Affecter</button>
        </div>
      </form>

      <Table
        columns={[
          { key: 'id_eleve', header: 'Élève', render: (r) => String(r.id_eleve).slice(0, 8) },
          { key: 'id_chambre', header: 'Chambre', render: (r) => String(r.id_chambre).slice(0, 8) },
          { key: 'date_debut', header: 'Début' },
        ]}
        data={affectations}
        loading={false}
        emptyMessage="Aucune affectation."
      />
    </div>
  );
}
