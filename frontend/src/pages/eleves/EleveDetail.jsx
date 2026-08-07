import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { elevesApi } from '../../services/api/eleves';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';

function InfoRow({ label, value }) {
  return (
    <div className="flex flex-col gap-1 border-b border-slate-100 py-3 sm:flex-row sm:justify-between">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="text-sm font-medium text-slate-900">{value || '—'}</span>
    </div>
  );
}

export default function EleveDetail() {
  const { id } = useParams();
  const toast = useToast();
  const fileRef = useRef(null);
  const photoRef = useRef(null);
  const { isAdmin, isSecretariat, isParent } = useAuth();
  const canWrite = isAdmin || isSecretariat;
  const canViewMedical = isAdmin || isSecretariat;

  const [eleve, setEleve] = useState(null);
  const [inscriptions, setInscriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [medicalNotes, setMedicalNotes] = useState('');
  const [savingMedical, setSavingMedical] = useState(false);
  const [tab, setTab] = useState('identite');

  const load = async () => {
    setLoading(true);
    try {
      const eleveData = await elevesApi.get(id);
      setEleve(eleveData);
      setMedicalNotes(eleveData.notes_medicales || '');
      if (eleveData.photo_url) {
        try {
          const blob = await elevesApi.getPhotoBlob(id);
          setPhotoPreview(URL.createObjectURL(blob));
        } catch {
          setPhotoPreview(null);
        }
      } else {
        setPhotoPreview(null);
      }
      try {
        const inscrData = await elevesApi.getInscriptions(id);
        setInscriptions(inscrData.items || inscrData || []);
      } catch {
        setInscriptions([]);
      }
    } catch {
      toast.error('Erreur lors du chargement de la fiche élève');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    return () => {
      if (photoPreview) URL.revokeObjectURL(photoPreview);
    };
  }, [id]);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await elevesApi.uploadDocument(id, file);
      toast.success('Document ajouté');
      await load();
    } catch {
      toast.error("Erreur lors de l'upload");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const handlePhotoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingPhoto(true);
    try {
      await elevesApi.uploadPhoto(id, file);
      toast.success('Photo mise à jour');
      await load();
    } catch {
      toast.error("Erreur lors de l'upload photo");
    } finally {
      setUploadingPhoto(false);
      if (photoRef.current) photoRef.current.value = '';
    }
  };

  const handleSaveMedical = async () => {
    setSavingMedical(true);
    try {
      await elevesApi.update(id, { notes_medicales: medicalNotes });
      toast.success('Notes médicales enregistrées');
    } catch {
      toast.error('Erreur enregistrement notes médicales');
    } finally {
      setSavingMedical(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      </div>
    );
  }

  if (!eleve) {
    return (
      <div className="card text-center">
        <p className="text-slate-600">Élève introuvable</p>
        <Link to="/eleves" className="btn-primary mt-4 inline-flex">
          Retour à la liste
        </Link>
      </div>
    );
  }

  const parents = eleve.parents || [];
  const documents = eleve.pieces_justificatives || [];

  const tabs = [
    { id: 'identite', label: 'Identité' },
    { id: 'inscriptions', label: 'Inscriptions' },
    { id: 'parents', label: 'Parents / Tuteurs' },
    { id: 'documents', label: 'Documents' },
  ];
  if (canViewMedical) {
    tabs.push({ id: 'medical', label: 'Notes médicales' });
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-4">
          <div className="relative flex h-20 w-20 items-center justify-center rounded-2xl bg-primary-100 text-3xl overflow-hidden">
            {photoPreview ? (
              <img src={photoPreview} alt="" className="h-full w-full object-cover" />
            ) : (
              '👨‍🎓'
            )}
            {canWrite && (
              <>
                <input
                  ref={photoRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handlePhotoUpload}
                />
                <button
                  type="button"
                  onClick={() => photoRef.current?.click()}
                  className="absolute inset-0 flex items-end justify-center bg-black/40 text-xs text-white opacity-0 hover:opacity-100 transition-opacity"
                  disabled={uploadingPhoto}
                >
                  {uploadingPhoto ? '…' : 'Photo'}
                </button>
              </>
            )}
          </div>
          <div>
            <p className="font-mono text-sm text-primary-600">{eleve.matricule}</p>
            <h1 className="text-2xl font-bold text-slate-900">
              {eleve.prenom} {eleve.nom}
            </h1>
            <p className="text-sm text-slate-500">
              {eleve.classe_nom || 'Classe non assignée'}
              {eleve.est_boursier && <span className="ml-2 badge-info">Boursier</span>}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to={isParent ? '/parent' : '/eleves'} className="btn-secondary">
            ← Retour
          </Link>
          {canWrite && (
            <>
              <Link to={`/eleves/${id}/modifier`} className="btn-secondary">
                Modifier
              </Link>
              <Link to={`/eleves/${id}/inscription`} className="btn-primary">
                Réinscrire
              </Link>
            </>
          )}
        </div>
      </div>

      <div className="border-b border-slate-200">
        <nav className="flex gap-4 overflow-x-auto">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`whitespace-nowrap border-b-2 px-1 py-3 text-sm font-medium transition-colors ${
                tab === t.id
                  ? 'border-primary-600 text-primary-700'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {tab === 'identite' && (
        <div className="card">
          <InfoRow label="Date de naissance" value={eleve.date_naissance} />
          <InfoRow label="Lieu de naissance" value={eleve.lieu_naissance} />
          <InfoRow
            label="Sexe"
            value={eleve.sexe === 'M' ? 'Masculin' : eleve.sexe === 'F' ? 'Féminin' : eleve.sexe}
          />
          <InfoRow label="Adresse" value={eleve.adresse} />
          <InfoRow label="Statut" value={eleve.statut} />
        </div>
      )}

      {tab === 'inscriptions' && (
        <div className="card">
          {inscriptions.length === 0 ? (
            <p className="text-sm text-slate-500">Aucune inscription enregistrée</p>
          ) : (
            <div className="space-y-3">
              {inscriptions.map((inscr) => (
                <div key={inscr.id} className="rounded-lg border border-slate-200 p-4">
                  <div className="flex justify-between">
                    <p className="font-medium">{inscr.annee_libelle || inscr.annee?.libelle}</p>
                    <span className="badge-success">{inscr.statut}</span>
                  </div>
                  <p className="mt-1 text-sm text-slate-500">
                    Classe : {inscr.classe_nom || inscr.classe?.libelle || '—'}
                  </p>
                  {inscr.est_boursier && (
                    <p className="mt-1 text-xs text-blue-600">Élève boursier</p>
                  )}
                  <p className="text-xs text-slate-400">Inscrit le {inscr.date_inscription}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'parents' && (
        <div className="card">
          {parents.length === 0 ? (
            <p className="text-sm text-slate-500">Aucun parent/tuteur enregistré</p>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {parents.map((p) => (
                <div key={p.id} className="rounded-lg border border-slate-200 p-4">
                  <p className="font-medium">
                    {p.prenom} {p.nom}
                    {p.tuteur_legal && (
                      <span className="ml-2 text-xs text-primary-600">Tuteur légal</span>
                    )}
                  </p>
                  <p className="text-sm text-slate-500">{p.lien_parente || '—'}</p>
                  <p className="mt-2 text-sm">{p.telephone}</p>
                  <p className="text-sm">{p.email}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'documents' && (
        <div className="card space-y-4">
          {canWrite && (
            <div className="flex items-center gap-3">
              <input ref={fileRef} type="file" onChange={handleUpload} className="text-sm" />
              {uploading && <span className="text-sm text-slate-500">Upload...</span>}
            </div>
          )}
          {documents.length === 0 ? (
            <p className="text-sm text-slate-500">Aucun document joint</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {documents.map((doc, i) => (
                <li key={i} className="flex items-center justify-between py-3">
                  <div>
                    <p className="font-medium text-slate-900">{doc.type || 'Document'}</p>
                    <p className="text-xs text-slate-500">{doc.date_upload}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {tab === 'medical' && canViewMedical && (
        <div className="card space-y-4">
          <p className="text-xs text-slate-500">
            Données chiffrées — accès réservé admin / directeur / secrétariat
          </p>
          <textarea
            className="input min-h-[120px] w-full"
            value={medicalNotes}
            onChange={(e) => setMedicalNotes(e.target.value)}
            placeholder="Allergies, traitements, informations médicales…"
            readOnly={!canWrite}
          />
          {canWrite && (
            <button
              type="button"
              onClick={handleSaveMedical}
              disabled={savingMedical}
              className="btn-primary"
            >
              {savingMedical ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
