import { useEffect, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AlertCircle, Loader2 } from 'lucide-react';
import useAuth from '../../hooks/useAuth';
import AuthShell from '../../components/AuthShell';
import FormField from '../../components/FormField';

export default function Login() {
  const { login, isAuthenticated, isLoading, error, clearError, user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState({});
  const [serverOk, setServerOk] = useState(null);

  useEffect(() => {
    fetch('/api/health')
      .then((r) => setServerOk(r.ok))
      .catch(() => setServerOk(false));
  }, []);

  const from = location.state?.from?.pathname || (user?.role === 'parent' ? '/parent' : '/dashboard');

  if (isAuthenticated) {
    return <Navigate to={user?.role === 'parent' ? '/parent' : from} replace />;
  }

  const validate = () => {
    const newErrors = {};
    if (!form.email.trim()) newErrors.email = "L'email est requis";
    else if (!/\S+@\S+\.\S+/.test(form.email)) newErrors.email = 'Email invalide';
    if (!form.password) newErrors.password = 'Le mot de passe est requis';
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
      const data = await login(form.email, form.password);
      if (data.doit_changer_mdp || data.user?.doit_changer_mdp) {
        navigate('/change-password', { replace: true });
      } else if (data.user?.role === 'parent') {
        navigate('/parent', { replace: true });
      } else {
        navigate(from === '/dashboard' && data.user?.role === 'parent' ? '/parent' : from, { replace: true });
      }
    } catch {
      /* error handled in store */
    }
  };

  return (
    <AuthShell
      title="Connexion"
      subtitle="Entrez vos identifiants pour accéder à votre espace"
      footer={
        <p className="text-xs text-texte-secondaire">
          © {new Date().getFullYear()} Gestion Scolaire — Tous droits réservés
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {serverOk === false && (
          <div className="auth-alert auth-alert-error">
            <AlertCircle className="h-4 w-4 shrink-0" strokeWidth={1.75} />
            <p>
              Le backend n&apos;est pas joignable. Ouvrez un terminal à la racine du projet et
              exécutez&nbsp;: <code className="font-mono text-xs">.\scripts\start-native.ps1</code>
            </p>
          </div>
        )}
        {error && (
          <div className="auth-alert auth-alert-error">
            <AlertCircle className="h-4 w-4 shrink-0" strokeWidth={1.75} />
            <p>{error}</p>
          </div>
        )}

        <FormField
          label="Adresse email"
          name="email"
          type="email"
          value={form.email}
          onChange={handleChange}
          error={errors.email}
          required
          placeholder="nom@etablissement.fr"
          autoComplete="email"
        />

        <FormField
          label="Mot de passe"
          name="password"
          type="password"
          value={form.password}
          onChange={handleChange}
          error={errors.password}
          required
          placeholder="••••••••"
          autoComplete="current-password"
        />

        <button type="submit" disabled={isLoading} className="btn-primary w-full py-3 text-[15px]">
          {isLoading ? (
            <span className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2} />
              Connexion…
            </span>
          ) : (
            'Se connecter'
          )}
        </button>

        <p className="text-center text-sm">
          <Link to="/forgot-password" className="font-medium text-or-cachet hover:underline">
            Mot de passe oublié ?
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}
