import { useEffect, useState } from 'react';
import { financeApi } from '../../services/api/finance';
import { configApi } from '../../services/api/config';
import { elevesApi } from '../../services/api/eleves';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function Encaissement() {
  const toast = useToast();
  const [eleves, setEleves] = useState([]);
  const [annees, setAnnees] = useState([]);
  const [form, setForm] = useState({
    id_eleve: '',
    id_annee: '',
    motif: 'Scolarité',
    montant_verse: '',
    mode_paiement: 'Espèces',
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    Promise.all([elevesApi.list(), configApi.listAnnees()])
      .then(([e, a]) => {
        const eleveList = e.items || e || [];
        const anneeList = Array.isArray(a) ? a : a.items || [];
        setEleves(eleveList);
        setAnnees(anneeList);
        const active = anneeList.find((x) => x.est_active);
        if (active) {
          setForm((f) => ({ ...f, id_annee: String(active.id) }));
        }
      })
      .catch(() => toast.error('Erreur chargement des données'));
  }, [toast]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const result = await financeApi.encaisser({
        ...form,
        montant_verse: parseFloat(form.montant_verse),
      });
      toast.success(`Paiement enregistré — Reçu ${result.numero_recu}`);
      setForm((f) => ({ ...f, montant_verse: '' }));
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur encaissement');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Encaissement</h1>
        <p className="text-sm text-slate-500">Génère un reçu numéroté automatiquement</p>
      </div>
      <form onSubmit={handleSubmit} className="card space-y-4">
        <FormField
          label="Élève"
          name="id_eleve"
          type="select"
          value={form.id_eleve}
          onChange={(e) => setForm({ ...form, id_eleve: e.target.value })}
          required
          options={eleves.map((el) => ({
            value: String(el.id),
            label: `${el.prenom} ${el.nom} (${el.matricule})`,
          }))}
        />
        <FormField
          label="Année scolaire"
          name="id_annee"
          type="select"
          value={form.id_annee}
          onChange={(e) => setForm({ ...form, id_annee: e.target.value })}
          required
          options={annees.map((a) => ({ value: String(a.id), label: a.libelle }))}
        />
        <FormField
          label="Motif"
          value={form.motif}
          onChange={(e) => setForm({ ...form, motif: e.target.value })}
          required
        />
        <FormField
          label="Montant (FCFA)"
          type="number"
          value={form.montant_verse}
          onChange={(e) => setForm({ ...form, montant_verse: e.target.value })}
          required
        />
        <FormField
          label="Mode de paiement"
          name="mode_paiement"
          type="select"
          value={form.mode_paiement}
          onChange={(e) => setForm({ ...form, mode_paiement: e.target.value })}
          options={[
            { value: 'Espèces', label: 'Espèces' },
            { value: 'Mobile Money', label: 'Mobile Money' },
            { value: 'Virement', label: 'Virement' },
          ]}
        />
        <button type="submit" className="btn-primary w-full" disabled={loading}>
          {loading ? 'Enregistrement...' : 'Encaisser et générer reçu'}
        </button>
      </form>
    </div>
  );
}
