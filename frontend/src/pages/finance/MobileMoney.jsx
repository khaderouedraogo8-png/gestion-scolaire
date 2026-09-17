import { useState } from 'react';
import { Smartphone } from 'lucide-react';
import { financeApi } from '../../services/api/finance';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

const OPERATEURS = [
  { value: 'orange_money', label: 'Orange Money' },
  { value: 'moov_money', label: 'Moov Money' },
  { value: 'mtn_momo', label: 'MTN MoMo' },
  { value: 'wave', label: 'Wave' },
];

export default function MobileMoney() {
  const toast = useToast();
  const [form, setForm] = useState({
    operateur: 'orange_money',
    montant: '',
    telephone: '',
    id_eleve: '',
    motif: 'frais_scolaires',
    reference: '',
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const onChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.montant || !form.telephone) {
      toast.error('Montant et téléphone requis');
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const data = await financeApi.initiateMobileMoney({
        operateur: form.operateur,
        montant: Number(form.montant),
        telephone: form.telephone.trim(),
        id_eleve: form.id_eleve || undefined,
        motif: form.motif || undefined,
        reference: form.reference || undefined,
      });
      setResult(data);
      if (data.ok) toast.success('Paiement Mobile Money initié');
      else toast.error(data.payload?.message || data.code || 'Échec initiation');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur Mobile Money');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Finance"
        title="Mobile Money"
        subtitle="Initier un paiement Orange Money, Moov, MTN ou Wave"
      />

      <form onSubmit={handleSubmit} className="card-premium mx-auto max-w-lg space-y-4 p-6">
        <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-or-cachet-clair text-or-cachet">
          <Smartphone className="h-5 w-5" strokeWidth={1.75} />
        </div>
        <FormField
          label="Opérateur"
          name="operateur"
          type="select"
          value={form.operateur}
          onChange={onChange}
          options={OPERATEURS}
        />
        <FormField
          label="Montant (FCFA)"
          name="montant"
          type="number"
          value={form.montant}
          onChange={onChange}
          required
        />
        <FormField
          label="Téléphone"
          name="telephone"
          value={form.telephone}
          onChange={onChange}
          placeholder="+226…"
          required
        />
        <FormField
          label="ID élève (optionnel)"
          name="id_eleve"
          value={form.id_eleve}
          onChange={onChange}
        />
        <FormField label="Motif" name="motif" value={form.motif} onChange={onChange} />
        <FormField
          label="Référence"
          name="reference"
          value={form.reference}
          onChange={onChange}
          placeholder="Auto si vide"
        />
        <button type="submit" className="btn-primary w-full" disabled={loading}>
          {loading ? 'Initiation…' : 'Initier le paiement'}
        </button>
      </form>

      {result && (
        <div className="card-premium mx-auto max-w-lg p-5 text-sm">
          <p className="font-display font-semibold text-encre">
            {result.ok ? 'Succès' : 'Échec'} — {result.code}
          </p>
          <pre className="mt-3 overflow-auto rounded-input bg-craie p-3 text-xs text-texte-secondaire">
            {JSON.stringify(result.payload || result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
