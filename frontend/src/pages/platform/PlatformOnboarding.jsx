import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { platformApi } from '../../services/api/platform';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

const initial = {
  name: '',
  code: '',
  email: '',
  phone: '',
  city: '',
  country: 'Burkina Faso',
  admin_nom: '',
  admin_prenom: '',
  admin_email: '',
  admin_password: '',
};

export default function PlatformOnboarding() {
  const toast = useToast();
  const navigate = useNavigate();
  const [form, setForm] = useState(initial);
  const [saving, setSaving] = useState(false);

  const onChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  };

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        ...form,
        email: form.email || null,
        phone: form.phone || null,
        city: form.city || null,
        country: form.country || null,
      };
      const data = await platformApi.onboardSchool(payload);
      toast.success(`École ${data.school.code} créée avec admin ${data.admin.email}`);
      navigate('/platform/schools');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Échec de l’onboarding');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Onboarding école"
        subtitle="Création atomique : école + établissement + premier administrateur"
      />

      <form onSubmit={submit} className="mx-auto max-w-2xl space-y-6">
        <section className="space-y-4">
          <h2 className="text-lg font-semibold text-encre">École</h2>
          <FormField label="Nom" name="name" required value={form.name} onChange={onChange} />
          <FormField
            label="Code"
            name="code"
            required
            value={form.code}
            onChange={onChange}
            helpText="Unique, ex. LYCEE-OUAGA-01"
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              label="Email"
              name="email"
              type="email"
              value={form.email}
              onChange={onChange}
            />
            <FormField label="Téléphone" name="phone" value={form.phone} onChange={onChange} />
            <FormField label="Ville" name="city" value={form.city} onChange={onChange} />
            <FormField label="Pays" name="country" value={form.country} onChange={onChange} />
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="text-lg font-semibold text-encre">Premier administrateur</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              label="Nom"
              name="admin_nom"
              required
              value={form.admin_nom}
              onChange={onChange}
            />
            <FormField
              label="Prénom"
              name="admin_prenom"
              required
              value={form.admin_prenom}
              onChange={onChange}
            />
          </div>
          <FormField
            label="Email admin"
            name="admin_email"
            type="email"
            required
            value={form.admin_email}
            onChange={onChange}
          />
          <FormField
            label="Mot de passe temporaire"
            name="admin_password"
            type="password"
            required
            value={form.admin_password}
            onChange={onChange}
          />
        </section>

        <div className="flex gap-3">
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? 'Création…' : 'Créer l’école'}
          </button>
          <button type="button" className="btn-secondary" onClick={() => navigate(-1)}>
            Annuler
          </button>
        </div>
      </form>
    </div>
  );
}
