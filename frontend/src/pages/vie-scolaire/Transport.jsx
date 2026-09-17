import { useCallback, useEffect, useState } from 'react';
import { vieScolaireApi } from '../../services/api/vieScolaire';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function Transport() {
  const toast = useToast();
  const [itineraires, setItineraires] = useState([]);
  const [eleves, setEleves] = useState([]);
  const [loading, setLoading] = useState(true);
  const [itineraire, setItineraire] = useState({ libelle: '', description: '' });
  const [affectation, setAffectation] = useState({ id_eleve: '', id_itineraire: '', id_arret: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [i, e] = await Promise.all([
        vieScolaireApi.listTransportItineraires(),
        vieScolaireApi.listTransportEleves(),
      ]);
      setItineraires(Array.isArray(i) ? i : []);
      setEleves(Array.isArray(e) ? e : []);
    } catch {
      toast.error('Impossible de charger le transport');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const createItineraire = async (e) => {
    e.preventDefault();
    try {
      await vieScolaireApi.createTransportItineraire(itineraire);
      toast.success('Itinéraire créé');
      setItineraire({ libelle: '', description: '' });
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const linkEleve = async (e) => {
    e.preventDefault();
    try {
      await vieScolaireApi.createTransportEleve({
        id_eleve: affectation.id_eleve,
        id_itineraire: affectation.id_itineraire,
        id_arret: affectation.id_arret || null,
      });
      toast.success('Élève affecté');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Vie scolaire" title="Transport" subtitle="Itinéraires et élèves transportés" />

      <form onSubmit={createItineraire} className="card-premium flex flex-wrap gap-3 p-5">
        <div className="min-w-[10rem] flex-1">
          <FormField label="Libellé itinéraire" name="libelle" value={itineraire.libelle} onChange={(e) => setItineraire((f) => ({ ...f, libelle: e.target.value }))} required />
        </div>
        <div className="min-w-[10rem] flex-1">
          <FormField label="Description" name="description" value={itineraire.description} onChange={(e) => setItineraire((f) => ({ ...f, description: e.target.value }))} />
        </div>
        <div className="flex items-end">
          <button type="submit" className="btn-primary">Créer</button>
        </div>
      </form>

      <Table
        columns={[
          { key: 'libelle', header: 'Itinéraire' },
          { key: 'description', header: 'Description', render: (r) => r.description || '—' },
        ]}
        data={itineraires}
        loading={loading}
        emptyMessage="Aucun itinéraire."
      />

      <form onSubmit={linkEleve} className="card-premium grid gap-3 p-5 sm:grid-cols-3">
        <FormField label="ID élève" name="id_eleve" value={affectation.id_eleve} onChange={(e) => setAffectation((f) => ({ ...f, id_eleve: e.target.value }))} required />
        <FormField
          label="Itinéraire"
          name="id_itineraire"
          type="select"
          value={affectation.id_itineraire}
          onChange={(e) => setAffectation((f) => ({ ...f, id_itineraire: e.target.value }))}
          options={itineraires.map((i) => ({ value: String(i.id), label: i.libelle }))}
        />
        <div className="flex items-end">
          <button type="submit" className="btn-secondary w-full">Affecter</button>
        </div>
      </form>

      <Table
        columns={[
          { key: 'id_eleve', header: 'Élève', render: (r) => String(r.id_eleve).slice(0, 8) },
          { key: 'id_itineraire', header: 'Itinéraire', render: (r) => String(r.id_itineraire).slice(0, 8) },
        ]}
        data={eleves}
        loading={false}
        emptyMessage="Aucun élève transporté."
      />
    </div>
  );
}
