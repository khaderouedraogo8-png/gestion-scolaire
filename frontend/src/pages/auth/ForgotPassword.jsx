import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { usersApi } from '../../services/api/users';
import AuthShell from '../../components/AuthShell';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function ForgotPassword() {
  const toast = useToast();
  const navigate = useNavigate();
  const [step, setStep] = useState('email');
  const [email, setEmail] = useState('');
  const [token, setToken] = useState('');
  const [hasDevToken, setHasDevToken] = useState(false);
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [infoMessage, setInfoMessage] = useState('');

  const handleRequest = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await usersApi.forgotPassword(email);
      const devToken = res.reset_token || '';
      setToken(devToken);
      setHasDevToken(Boolean(devToken));
      setInfoMessage(
        res.message ||
          'Si un compte existe pour cet email, les instructions de réinitialisation ont été envoyées.'
      );
      toast.success(res.message || 'Demande enregistrée');
      setStep('reset');
    } catch {
      toast.error("Impossible d'envoyer la demande. Vérifiez l'email et réessayez.");
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
      toast.error(err.response?.data?.message || 'Impossible de réinitialiser le mot de passe');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Mot de passe oublié"
      subtitle={
        step === 'email'
          ? 'Entrez votre email pour recevoir un lien de réinitialisation'
          : hasDevToken
            ? 'Définissez votre nouveau mot de passe'
            : 'Consultez votre boîte mail, puis saisissez le code reçu'
      }
      footer={
        <p className="text-xs text-texte-secondaire">
          © {new Date().getFullYear()} Gestion Scolaire — Tous droits réservés
        </p>
      }
    >
      {step === 'email' ? (
        <form onSubmit={handleRequest} className="space-y-4">
          <FormField
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? 'Envoi…' : 'Envoyer'}
          </button>
        </form>
      ) : (
        <form onSubmit={handleReset} className="space-y-4">
          {infoMessage && (
            <div className="rounded-input border border-bordure/80 bg-craie/60 px-4 py-3 text-sm text-encre">
              {infoMessage}
            </div>
          )}
          <FormField
            label={hasDevToken ? 'Jeton (mode développement)' : 'Code de réinitialisation'}
            value={token}
            onChange={(e) => setToken(e.target.value)}
            required
            helpText={
              hasDevToken
                ? 'Le jeton est prérempli car le serveur est en mode debug.'
                : 'Collez le code reçu par email (ou contactez l’administrateur).'
            }
          />
          <FormField
            label="Nouveau mot de passe"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button type="submit" disabled={loading || !token} className="btn-primary w-full">
            {loading ? 'Enregistrement…' : 'Réinitialiser'}
          </button>
          <button
            type="button"
            className="btn-ghost w-full text-sm"
            onClick={() => {
              setStep('email');
              setPassword('');
              setInfoMessage('');
            }}
          >
            Renvoyer une demande
          </button>
        </form>
      )}

      <Link to="/login" className="mt-6 block text-center text-sm text-or-cachet hover:underline">
        Retour à la connexion
      </Link>
    </AuthShell>
  );
}
