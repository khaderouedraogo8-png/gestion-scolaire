import { useState } from 'react';
import { documentsApi } from '../../services/api/documents';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function VerifierQR() {
  const toast = useToast();
  const [qrData, setQrData] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleVerify = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    try {
      const data = await documentsApi.verifierQr(qrData.trim());
      setResult(data);
      if (data.valide) toast.success('QR code valide');
    } catch (err) {
      setResult({ valide: false, message: err.response?.data?.message || 'QR invalide' });
      toast.error('QR code invalide ou falsifié');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <div>
        <h1 className="page-title">Vérifier un QR code</h1>
        <p className="page-subtitle">Contrôle d'authenticité des cartes scolaires</p>
      </div>
      <form onSubmit={handleVerify} className="card space-y-4">
        <FormField
          label="Données QR (JSON scanné)"
          name="qr_data"
          type="textarea"
          value={qrData}
          onChange={(e) => setQrData(e.target.value)}
          rows={5}
          placeholder='{"matricule":"2025M-001",...}'
          required
        />
        <button type="submit" className="btn-primary w-full" disabled={loading}>
          {loading ? 'Vérification...' : 'Vérifier'}
        </button>
      </form>
      {result && (
        <div className={`card ${result.valide ? 'border-feuille/30 bg-feuille-clair' : 'border-brique/30 bg-brique-clair'}`}>
          {result.valide ? (
            <div className="space-y-2 text-sm">
              <p className="font-semibold text-feuille">Carte authentique</p>
              <p>
                {result.data?.prenom} {result.data?.nom} — {result.data?.matricule}
              </p>
              <p className="text-texte-secondaire">Année : {result.data?.annee}</p>
            </div>
          ) : (
            <p className="text-sm text-brique">{result.message || 'QR code invalide'}</p>
          )}
        </div>
      )}
    </div>
  );
}
