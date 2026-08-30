import { useEffect, useRef, useState } from 'react';
import { configApi } from '../../services/api/config';
import FormField from '../../components/FormField';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';

const EMPTY_FORM = {
  nom: '',
  sigle: '',
  adresse: '',
  telephone: '',
  email: '',
  type_etablissement: '',
  pays: '',
  ville: '',
  format_matricule: '{ANNEE}M-{SEQ}',
  devise: 'XOF',
};

export default function Etablissement() {
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;

  const [form, setForm] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [exists, setExists] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const data = await configApi.getEtablissement();
        setForm({
          nom: data.nom || '',
          sigle: data.sigle || '',
          adresse: data.adresse || '',
          telephone: data.telephone || '',
          email: data.email || '',
          type_etablissement: data.type_etablissement || '',
          pays: data.pays || '',
          ville: data.ville || '',
          format_matricule: data.format_matricule || '{ANNEE}M-{SEQ}',
          devise: data.devise || 'XOF',
        });
        setExists(true);
      } catch (err) {
        if (err.response?.status === 404) {
          setExists(false);
        } else {
          toastRef.current.error('Impossible de charger l\'établissement. Réessayez.');
        }
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (exists) {
        await configApi.updateEtablissement(form);
        toast.success('Établissement mis à jour');
      } else {
        await configApi.createEtablissement(form);
        setExists(true);
        toast.success('Établissement configuré');
      }
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur lors de l\'enregistrement');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-or-cachet-clair border-t-or-cachet" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <PageHeader
        eyebrow="Configuration"
        title="Établissement"
        subtitle={exists ? 'Paramètres généraux de l\'établissement' : 'Configuration initiale de l\'établissement'}
      />

      <form onSubmit={handleSubmit} className="card space-y-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Nom de l'établissement" name="nom" value={form.nom} onChange={handleChange} required />
          <FormField label="Sigle" name="sigle" value={form.sigle} onChange={handleChange} />
          <FormField
            label="Type"
            name="type_etablissement"
            type="select"
            value={form.type_etablissement}
            onChange={handleChange}
            options={[
              { value: 'primaire', label: 'Primaire' },
              { value: 'college', label: 'Collège' },
              { value: 'lycee', label: 'Lycée' },
              { value: 'mixte', label: 'Mixte' },
            ]}
          />
          <FormField label="Devise" name="devise" value={form.devise} onChange={handleChange} />
        </div>

        <FormField label="Adresse" name="adresse" type="textarea" value={form.adresse} onChange={handleChange} rows={2} />

        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Ville" name="ville" value={form.ville} onChange={handleChange} />
          <FormField label="Pays" name="pays" value={form.pays} onChange={handleChange} />
          <FormField label="Téléphone" name="telephone" value={form.telephone} onChange={handleChange} />
          <FormField label="Email" name="email" type="email" value={form.email} onChange={handleChange} />
        </div>

        <FormField
          label="Format matricule"
          name="format_matricule"
          value={form.format_matricule}
          onChange={handleChange}
          helpText="Variables : {ANNEE}, {SEQ}"
        />

        <div className="flex justify-end">
          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? 'Enregistrement...' : exists ? 'Enregistrer les modifications' : 'Créer l\'établissement'}
          </button>
        </div>
      </form>
    </div>
  );
}
