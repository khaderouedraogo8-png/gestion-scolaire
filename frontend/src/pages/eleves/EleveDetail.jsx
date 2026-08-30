import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { GraduationCap, Users, FolderOpen, HeartPulse } from 'lucide-react';
import { elevesApi } from '../../services/api/eleves';
import SealMedallion from '../../components/SealMedallion';
import DetailHeader from '../../components/DetailHeader';
import TabBar from '../../components/TabBar';
import EmptyState from '../../components/EmptyState';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';

function InfoRow({ label, value }) {
  return (
    <div className="flex flex-col gap-1 border-b border-bordure/50 py-3 sm:flex-row sm:justify-between">
      <span className="page-subtitle">{label}</span>
      <span className="text-sm font-medium text-encre">{value || '—'}</span>
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
      toast.error('Impossible de charger la fiche élève. Réessayez.');
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
      <div className="flex flex-col items-center justify-center gap-4 py-32">
        <div className="loading-ring" />
        <p className="text-sm text-texte-secondaire">Chargement de la fiche…</p>
      </div>
    );
  }

  if (!eleve) {
    return (
      <div className="card-premium mx-auto max-w-md text-center">
        <EmptyState icon={GraduationCap} title="Élève introuvable" message="Cette fiche n'existe pas ou a été supprimée." />
        <Link to="/eleves" className="btn-primary mt-6 inline-flex">
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
    <div className="space-y-8">
      <DetailHeader
        eyebrow={eleve.matricule}
        title={`${eleve.prenom} ${eleve.nom}`}
        subtitle={
          <>
            {eleve.classe_nom || 'Classe non assignée'}
            {eleve.est_boursier && <span className="ml-2 badge-info">Boursier</span>}
          </>
        }
        media={
          <div className="relative flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-card border border-or-cachet/30 bg-or-cachet-clair">
            {photoPreview ? (
              <img src={photoPreview} alt="" className="h-full w-full object-cover" />
            ) : (
              <SealMedallion size="md" />
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
                  className="absolute inset-0 flex items-end justify-center bg-encre/60 text-xs text-craie opacity-0 transition-opacity hover:opacity-100"
                  disabled={uploadingPhoto}
                >
                  {uploadingPhoto ? '…' : 'Photo'}
                </button>
              </>
            )}
          </div>
        }
        actions={
          <>
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
          </>
        }
      />

      <TabBar tabs={tabs} active={tab} onChange={setTab} />

      {tab === 'identite' && (
        <div className="card-premium">
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
        <div className="card-premium">
          {inscriptions.length === 0 ? (
            <EmptyState icon={GraduationCap} message="Aucune inscription enregistrée pour l'instant." />
          ) : (
            <div className="space-y-3">
              {inscriptions.map((inscr) => (
                <div key={inscr.id} className="rounded-lg border border-bordure p-4">
                  <div className="flex justify-between">
                    <p className="font-medium">{inscr.annee_libelle || inscr.annee?.libelle}</p>
                    <span className="badge-success">{inscr.statut}</span>
                  </div>
                  <p className="mt-1 page-subtitle">
                    Classe : {inscr.classe_nom || inscr.classe?.libelle || '—'}
                  </p>
                  {inscr.est_boursier && (
                    <p className="mt-1 text-xs text-or-cachet">Élève boursier</p>
                  )}
                  <p className="text-xs text-texte-secondaire/70">Inscrit le {inscr.date_inscription}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'parents' && (
        <div className="card-premium">
          {parents.length === 0 ? (
            <EmptyState icon={Users} message="Aucun parent ou tuteur enregistré pour l'instant." />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {parents.map((p) => (
                <div key={p.id} className="rounded-lg border border-bordure p-4">
                  <p className="font-medium">
                    {p.prenom} {p.nom}
                    {p.tuteur_legal && (
                      <span className="ml-2 text-xs text-or-cachet">Tuteur légal</span>
                    )}
                  </p>
                  <p className="page-subtitle">{p.lien_parente || '—'}</p>
                  <p className="mt-2 text-sm">{p.telephone}</p>
                  <p className="text-sm">{p.email}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'documents' && (
        <div className="card-premium space-y-4">
          {canWrite && (
            <div className="flex items-center gap-3">
              <input ref={fileRef} type="file" onChange={handleUpload} className="text-sm" />
              {uploading && <span className="page-subtitle">Upload...</span>}
            </div>
          )}
          {documents.length === 0 ? (
            <EmptyState icon={FolderOpen} message="Aucun document joint pour l'instant." />
          ) : (
            <ul className="divide-y divide-bordure/50">
              {documents.map((doc, i) => (
                <li key={i} className="flex items-center justify-between py-3">
                  <div>
                    <p className="font-medium text-encre">{doc.type || 'Document'}</p>
                    <p className="text-xs text-texte-secondaire">{doc.date_upload}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {tab === 'medical' && canViewMedical && (
        <div className="card-premium space-y-4">
          <div className="flex items-center gap-2 text-xs text-texte-secondaire">
            <HeartPulse className="h-4 w-4 text-or-cachet" strokeWidth={1.75} />
            Données chiffrées — accès réservé admin / directeur / secrétariat
          </div>
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
