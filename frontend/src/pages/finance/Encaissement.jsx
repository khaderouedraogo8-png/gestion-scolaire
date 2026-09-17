import { useEffect, useState } from 'react';
import { financeApi } from '../../services/api/finance';
import { configApi } from '../../services/api/config';
import { elevesApi } from '../../services/api/eleves';
import FormField from '../../components/FormField';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';

export default function Encaissement() {
  const toast = useToast();
  const [eleves, setEleves] = useState([]);
  const [annees, setAnnees] = useState([]);
  const [echeances, setEcheances] = useState([]);
  const [integrations, setIntegrations] = useState(null);
  const [form, setForm] = useState({
    id_eleve: '',
    id_annee: '',
    id_echeance: '',
    motif: 'Scolarité',
    montant_verse: '',
    mode_paiement: 'Espèces',
  });
  const [loading, setLoading] = useState(false);
  const [loadingEcheances, setLoadingEcheances] = useState(false);

  useEffect(() => {
    Promise.all([elevesApi.list(), configApi.listAnnees(), financeApi.getIntegrations().catch(() => null)])
      .then(([e, a, integ]) => {
        const eleveList = e.items || e || [];
        const anneeList = Array.isArray(a) ? a : a.items || [];
        setEleves(eleveList);
        setAnnees(anneeList);
        setIntegrations(integ);
        const active = anneeList.find((x) => x.est_active);
        if (active) {
          setForm((f) => ({ ...f, id_annee: String(active.id) }));
        }
      })
      .catch(() => toast.error('Erreur chargement des données'));
  }, [toast]);

  useEffect(() => {
    if (!form.id_eleve || !form.id_annee) {
      setEcheances([]);
      return;
    }
    let cancelled = false;
    setLoadingEcheances(true);
    financeApi
      .listEcheancesEleve({ id_eleve: form.id_eleve, id_annee: form.id_annee })
      .catch(() =>
        financeApi.getEcheances({ id_eleve: form.id_eleve, id_annee: form.id_annee })
      )
      .then((data) => {
        if (!cancelled) {
          const list = Array.isArray(data) ? data : data.items || data.echeances || [];
          setEcheances(list);
        }
      })
      .catch(() => {
        if (!cancelled) setEcheances([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingEcheances(false);
      });
    return () => {
      cancelled = true;
    };
  }, [form.id_eleve, form.id_annee]);

  const mobileMoneyNonConfigure =
    form.mode_paiement === 'Mobile Money' &&
    (integrations?.mobile_money === 'NON_CONFIGURE' ||
      integrations?.status === 'NON_CONFIGURE' ||
      (Array.isArray(integrations?.providers) &&
        integrations.providers.every((p) => p.status === 'NON_CONFIGURE')));

  const handleEcheanceChange = (idEcheance) => {
    const selected = echeances.find((ec) => String(ec.id) === idEcheance);
    setForm((f) => ({
      ...f,
      id_echeance: idEcheance,
      montant_verse: selected?.montant_restant ?? selected?.montant ?? f.montant_verse,
      motif: selected?.libelle || selected?.motif || f.motif,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload = {
        ...form,
        montant_verse: parseFloat(form.montant_verse),
      };
      if (!payload.id_echeance) delete payload.id_echeance;
      const result = await financeApi.encaisser(payload);
      toast.success(`Paiement enregistré — Reçu ${result.numero_recu}`);
      setForm((f) => ({ ...f, montant_verse: '', id_echeance: '' }));
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur encaissement');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-lg space-y-8">
      <PageHeader
        eyebrow="Finance"
        title="Encaissement"
        subtitle="Génère un reçu numéroté automatiquement"
      />
      <form onSubmit={handleSubmit} className="card space-y-4">
        <FormField
          label="Élève"
          name="id_eleve"
          type="select"
          value={form.id_eleve}
          onChange={(e) => setForm({ ...form, id_eleve: e.target.value, id_echeance: '' })}
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
          onChange={(e) => setForm({ ...form, id_annee: e.target.value, id_echeance: '' })}
          required
          options={annees.map((a) => ({ value: String(a.id), label: a.libelle }))}
        />
        <FormField
          label="Échéance (recommandé)"
          name="id_echeance"
          type="select"
          value={form.id_echeance}
          onChange={(e) => handleEcheanceChange(e.target.value)}
          options={[
            { value: '', label: loadingEcheances ? 'Chargement…' : '— Sans échéance —' },
            ...echeances.map((ec) => ({
              value: String(ec.id),
              label: `${ec.libelle || 'Tranche'} — ${Number(ec.montant_restant ?? ec.montant).toLocaleString()} F (${ec.date_echeance})`,
            })),
          ]}
        />
        {form.id_eleve && form.id_annee && !loadingEcheances && echeances.length === 0 && (
          <p className="text-xs text-texte-secondaire">
            Aucune échéance trouvée pour cet élève — l'encaissement reste possible sans rattachement.
          </p>
        )}
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
        {mobileMoneyNonConfigure && (
          <div className="rounded-lg border border-ambre/40 bg-ambre-clair/50 px-3 py-2 text-xs text-encre">
            Mobile Money non configuré pour cet établissement. L'encaissement sera enregistré
            manuellement — contactez l'administrateur pour activer l'intégration.
          </div>
        )}
        <button type="submit" className="btn-primary w-full" disabled={loading}>
          {loading ? 'Enregistrement...' : 'Encaisser et générer reçu'}
        </button>
      </form>
    </div>
  );
}
