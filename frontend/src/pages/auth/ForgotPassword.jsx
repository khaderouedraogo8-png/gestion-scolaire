import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { usersApi } from '../../services/api/users';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function ForgotPassword() {
  const toast = useToast();
  const navigate = useNavigate();
  const [step, setStep] = useState('email');
  const [email, setEmail] = useState('');
  const [token, setToken] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleRequest = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await usersApi.forgotPassword(email);
      if (res.reset_token) setToken(res.reset_token);
      toast.success(res.message);
      setStep('reset');
    } catch {
      toast.error('Erreur lors de la demande');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await usersApi.resetPasswordWithToken(token, password);
      toast.success('Mot de passe mis à jour');
      navigate('/login');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-craie p-6">
      <div className="card w-full max-w-md space-y-6">
        <div>
          <h1 className="font-display text-xl font-medium text-encre">Mot de passe oublié</h1>
          <p className="page-subtitle">
            {step === 'email' ? 'Entrez votre email pour recevoir un lien' : 'Définissez votre nouveau mot de passe'}
          </p>
        </div>

        {step === 'email' ? (
          <form onSubmit={handleRequest} className="space-y-4">
            <FormField label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? 'Envoi...' : 'Envoyer'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleReset} className="space-y-4">
            <FormField label="Token de réinitialisation" value={token} onChange={(e) => setToken(e.target.value)} required />
            <FormField label="Nouveau mot de passe" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? 'Enregistrement...' : 'Réinitialiser'}
            </button>
          </form>
        )}

        <Link to="/login" className="block text-center text-sm text-or-cachet hover:underline">
          Retour à la connexion
        </Link>
      </div>
    </div>
  );
}
