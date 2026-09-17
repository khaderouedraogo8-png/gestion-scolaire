import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { AlertCircle, Loader2 } from 'lucide-react';
import AuthShell from '../../components/AuthShell';
import FormField from '../../components/FormField';
import { authApi } from '../../services/api/auth';
import { setAccessToken, useAuthStore } from '../../store/authStore';
import { schoolsApi } from '../../services/api/schools';
import { homePathForRole } from '../../utils/homePath';
import useAuth from '../../hooks/useAuth';

export default function OtpLogin() {
  const { isAuthenticated, user } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState('request');
  const [form, setForm] = useState({
    destinataire: '',
    school_code: '',
    canal: 'sms',
    code: '',
  });
  const [challengeId, setChallengeId] = useState(null);
  const [debugCode, setDebugCode] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (isAuthenticated) {
    return <Navigate to={homePathForRole(user?.role)} replace />;
  }

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setError('');
  };

  const requestOtp = async (e) => {
    e.preventDefault();
    if (!form.destinataire.trim()) {
      setError('Indiquez votre téléphone ou email');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await authApi.requestOtp({
        destinataire: form.destinataire.trim(),
        canal: form.canal,
        purpose: 'login_parent',
        school_code: form.school_code.trim() || undefined,
      });
      setChallengeId(data.challenge_id || null);
      setDebugCode(data.debug_code || null);
      setStep('verify');
    } catch (err) {
      setError(err.response?.data?.message || 'Impossible d’envoyer le code');
    } finally {
      setLoading(false);
    }
  };

  const verifyOtp = async (e) => {
    e.preventDefault();
    if (!form.code.trim()) {
      setError('Saisissez le code reçu');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await authApi.verifyOtp({
        destinataire: form.destinataire.trim(),
        code: form.code.trim(),
        purpose: 'login_parent',
        challenge_id: challengeId || undefined,
      });
      if (data.access_token && data.user) {
        setAccessToken(data.access_token);
        let currentSchool = null;
        try {
          currentSchool = await schoolsApi.getCurrent();
        } catch {
          /* ignore */
        }
        useAuthStore.setState({
          user: data.user,
          currentSchool,
          actingSchoolId: null,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
        navigate(homePathForRole(data.user.role), { replace: true });
      } else {
        setError(data.message || 'Code valide mais aucun compte parent lié');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Code invalide');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Connexion parent (OTP)"
      subtitle="Recevez un code par SMS, email ou WhatsApp"
      footer={
        <p className="text-sm text-texte-secondaire">
          <Link to="/login" className="font-medium text-or-cachet hover:underline">
            Connexion classique
          </Link>
        </p>
      }
    >
      {error && (
        <div className="auth-alert auth-alert-error mb-5">
          <AlertCircle className="h-4 w-4 shrink-0" strokeWidth={1.75} />
          <p>{error}</p>
        </div>
      )}

      {step === 'request' ? (
        <form onSubmit={requestOtp} className="space-y-5">
          <FormField
            label="Téléphone ou email"
            name="destinataire"
            value={form.destinataire}
            onChange={handleChange}
            required
            placeholder="+226… ou parent@email.com"
          />
          <FormField
            label="Code établissement (optionnel)"
            name="school_code"
            value={form.school_code}
            onChange={handleChange}
            placeholder="Ex. ECOLE01"
          />
          <FormField
            label="Canal"
            name="canal"
            type="select"
            value={form.canal}
            onChange={handleChange}
            options={[
              { value: 'sms', label: 'SMS' },
              { value: 'email', label: 'Email' },
              { value: 'whatsapp', label: 'WhatsApp' },
            ]}
          />
          <button type="submit" disabled={loading} className="btn-primary w-full py-2.5">
            {loading ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Envoi…
              </span>
            ) : (
              'Recevoir le code'
            )}
          </button>
        </form>
      ) : (
        <form onSubmit={verifyOtp} className="space-y-5">
          <p className="text-sm text-texte-secondaire">
            Code envoyé à <strong className="text-encre">{form.destinataire}</strong>
          </p>
          {debugCode && (
            <p className="rounded-input bg-craie px-3 py-2 text-xs text-texte-secondaire">
              Mode debug — code : <strong className="font-mono text-encre">{debugCode}</strong>
            </p>
          )}
          <FormField
            label="Code à 6 chiffres"
            name="code"
            value={form.code}
            onChange={handleChange}
            required
            placeholder="000000"
            autoComplete="one-time-code"
          />
          <button type="submit" disabled={loading} className="btn-primary w-full py-2.5">
            {loading ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Vérification…
              </span>
            ) : (
              'Valider'
            )}
          </button>
          <button
            type="button"
            className="btn-ghost w-full"
            onClick={() => {
              setStep('request');
              setForm((f) => ({ ...f, code: '' }));
            }}
          >
            Modifier le destinataire
          </button>
        </form>
      )}
    </AuthShell>
  );
}
