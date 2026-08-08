import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import useAuth from '../../hooks/useAuth';
import FormField from '../../components/FormField';
import SealMedallion from '../../components/SealMedallion';

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
    <div className="flex min-h-screen">
      <div className="hidden w-1/2 flex-col justify-center bg-encre p-12 lg:flex">
        <div className="max-w-md">
          <SealMedallion size="lg" className="mb-8" />
          <h1 className="font-display text-3xl font-medium text-craie">Gestion Scolaire</h1>
          <p className="mt-4 text-lg text-craie/70">
            Plateforme complète de gestion pour votre établissement scolaire : élèves, notes,
            finances, absences et bien plus.
          </p>
        </div>
      </div>

      <div className="flex flex-1 items-center justify-center bg-craie p-6">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center lg:text-left">
            <h2 className="page-title">Connexion</h2>
            <p className="page-subtitle mt-2">
              Entrez vos identifiants pour accéder à votre espace
            </p>
          </div>

          <form onSubmit={handleSubmit} className="card space-y-5">
            {error && (
              <div className="rounded-input border border-brique bg-brique-clair px-4 py-3 text-sm text-brique">
                {error}
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

            <button type="submit" disabled={isLoading} className="btn-primary w-full py-2.5">
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-craie/30 border-t-craie" />
                  Connexion...
                </span>
              ) : (
                'Se connecter'
              )}
            </button>

            <p className="text-center text-sm">
              <Link to="/forgot-password" className="text-or-cachet hover:underline">
                Mot de passe oublié ?
              </Link>
            </p>
          </form>

          <p className="mt-6 text-center text-xs text-texte-secondaire">
            © {new Date().getFullYear()} Gestion Scolaire — Tous droits réservés
          </p>
        </div>
      </div>
    </div>
  );
}
