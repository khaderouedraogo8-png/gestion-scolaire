import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuth from '../../hooks/useAuth';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function ChangePassword() {
  const { changePassword, isLoading, error, clearError } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [form, setForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [errors, setErrors] = useState({});

  const validate = () => {
    const newErrors = {};
    if (!form.currentPassword) newErrors.currentPassword = 'Mot de passe actuel requis';
    if (!form.newPassword) newErrors.newPassword = 'Nouveau mot de passe requis';
    else if (form.newPassword.length < 8)
      newErrors.newPassword = 'Minimum 8 caractères';
    if (form.newPassword !== form.confirmPassword)
      newErrors.confirmPassword = 'Les mots de passe ne correspondent pas';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' }));
    if (error) clearError();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    try {
      await changePassword(form.currentPassword, form.newPassword);
      toast.success('Mot de passe modifié avec succès');
      navigate('/dashboard');
    } catch {
      /* handled in store */
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold text-slate-900">Changement de mot de passe</h1>
          <p className="mt-2 text-sm text-slate-600">
            Pour des raisons de sécurité, vous devez définir un nouveau mot de passe
          </p>
        </div>

        <form onSubmit={handleSubmit} className="card space-y-5">
          {error && (
            <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
          )}

          <FormField
            label="Mot de passe actuel"
            name="currentPassword"
            type="password"
            value={form.currentPassword}
            onChange={handleChange}
            error={errors.currentPassword}
            required
          />

          <FormField
            label="Nouveau mot de passe"
            name="newPassword"
            type="password"
            value={form.newPassword}
            onChange={handleChange}
            error={errors.newPassword}
            required
            helpText="Minimum 8 caractères"
          />

          <FormField
            label="Confirmer le mot de passe"
            name="confirmPassword"
            type="password"
            value={form.confirmPassword}
            onChange={handleChange}
            error={errors.confirmPassword}
            required
          />

          <button type="submit" disabled={isLoading} className="btn-primary w-full">
            {isLoading ? 'Enregistrement...' : 'Enregistrer le mot de passe'}
          </button>
        </form>
      </div>
    </div>
  );
}
