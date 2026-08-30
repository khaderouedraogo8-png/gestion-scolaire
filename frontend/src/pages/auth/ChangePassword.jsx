import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, Loader2 } from 'lucide-react';
import useAuth from '../../hooks/useAuth';
import AuthShell from '../../components/AuthShell';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function ChangePassword() {
  const { changePassword, isLoading, error, clearError, user } = useAuth();
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
    else if (form.newPassword.length < 8) newErrors.newPassword = 'Minimum 8 caractères';
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
      navigate(user?.role === 'parent' ? '/parent' : '/dashboard');
    } catch {
      /* handled in store */
    }
  };

  return (
    <AuthShell
      title="Changement de mot de passe"
      subtitle="Pour des raisons de sécurité, vous devez définir un nouveau mot de passe"
      footer={
        <p className="text-xs text-texte-secondaire">
          © {new Date().getFullYear()} Gestion Scolaire — Tous droits réservés
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {error && (
          <div className="auth-alert auth-alert-error">
            <AlertCircle className="h-4 w-4 shrink-0" strokeWidth={1.75} />
            <p>{error}</p>
          </div>
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
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2} />
              Enregistrement...
            </span>
          ) : (
            'Enregistrer le mot de passe'
          )}
        </button>
      </form>
    </AuthShell>
  );
}
