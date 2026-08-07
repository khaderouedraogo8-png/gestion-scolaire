import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import useAuth from '../../hooks/useAuth';
import FormField from '../../components/FormField';

export default function Login() {
  const { login, isAuthenticated, isLoading, error, clearError, user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState({});

  const from = location.state?.from?.pathname || (user?.role === 'parent' ? '/parent' : '/dashboard');

  if (isAuthenticated) {
    return <Navigate to={user?.role === 'parent' ? '/parent' : from} replace />;
  }

  const validate = () => {
    const newErrors = {};
    if (!form.email.trim()) newErrors.email = 'L\'email est requis';
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
    <div className="flex min-h-screen">
      <div className="hidden w-1/2 bg-gradient-to-br from-primary-700 via-primary-600 to-primary-800 lg:flex lg:flex-col lg:justify-center lg:p-12">
        <div className="max-w-md">
          <div className="mb-8 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/20 text-2xl font-bold text-white">
            GS
          </div>
          <h1 className="text-3xl font-bold text-white">Gestion Scolaire</h1>
          <p className="mt-4 text-lg text-primary-100">
            Plateforme complète de gestion pour votre établissement scolaire : élèves, notes,
            finances, absences et bien plus.
          </p>
        </div>
      </div>

      <div className="flex flex-1 items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center lg:text-left">
            <h2 className="text-2xl font-bold text-slate-900">Connexion</h2>
            <p className="mt-2 text-sm text-slate-600">
              Entrez vos identifiants pour accéder à votre espace
            </p>
          </div>

          <form onSubmit={handleSubmit} className="card space-y-5">
            {error && (
              <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
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

            <button type="submit" disabled={isLoading} className="btn-primary w-full py-2.5">
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Connexion...
                </span>
              ) : (
                'Se connecter'
              )}
            </button>

            <p className="text-center text-sm">
              <Link to="/forgot-password" className="text-primary-600 hover:underline">
                Mot de passe oublié ?
              </Link>
            </p>
          </form>

          <p className="mt-6 text-center text-xs text-slate-500">
            © {new Date().getFullYear()} Gestion Scolaire — Tous droits réservés
          </p>
        </div>
      </div>
    </div>
  );
}
