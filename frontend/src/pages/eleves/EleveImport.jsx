import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { elevesApi } from '../../services/api/eleves';
import { configApi } from '../../services/api/config';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';
import { apiErrorMessage } from '../../utils/academicLabels';

export default function EleveImport() {
  const toast = useToast();
  const [annees, setAnnees] = useState([]);
  const [classes, setClasses] = useState([]);
  const [idAnnee, setIdAnnee] = useState('');
  const [idClasse, setIdClasse] = useState('');
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    const init = async () => {
      try {
        const [ans, cls] = await Promise.all([
          configApi.listAnnees(),
          configApi.listClasses(),
        ]);
        const anneeList = ans.items || ans || [];
        setAnnees(anneeList);
        setClasses(cls.items || cls || []);
        const active = anneeList.find((a) => a.est_active);
        if (active) setIdAnnee(String(active.id));
      } catch (err) {
        toast.error(apiErrorMessage(err, 'Impossible de charger les filtres.'));
      }
    };
    init();
  }, [toast]);

  const handlePreview = async (e) => {
    e.preventDefault();
    if (!file || !idAnnee) {
      toast.error('Sélectionnez une année et un fichier.');
      return;
    }
    setLoading(true);
    setPreview(null);
    try {
      const data = await elevesApi.importPreview(file, {
        id_annee: idAnnee,
        id_classe: idClasse || undefined,
      });
      setPreview(data);
      if (data.summary?.errors) {
        toast.warning(
          `${data.summary.ok} ligne(s) OK — ${data.summary.errors} erreur(s) à corriger`
        );
      } else {
        toast.success(`${data.summary?.ok || 0} ligne(s) prêtes à importer`);
      }
    } catch (err) {
      toast.error(apiErrorMessage(err, "Échec de l'analyse du fichier"));
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (!preview?.items?.length || !idAnnee) return;
    const okRows = preview.items.filter((r) => r.status === 'ok');
    if (!okRows.length) {
      toast.error('Aucune ligne valide à importer.');
      return;
    }
    setConfirming(true);
    try {
      const res = await elevesApi.importConfirm({
        id_annee: idAnnee,
        rows: okRows,
      });
      toast.success(`${res.imported} élève(s) importé(s)`);
      setPreview(null);
      setFile(null);
    } catch (err) {
      toast.error(apiErrorMessage(err, "Échec de l'import"));
    } finally {
      setConfirming(false);
    }
  };

  const downloadTemplate = async () => {
    try {
      const blob = await elevesApi.importTemplate();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'modele_import_eleves.xlsx';
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Téléchargement impossible'));
    }
  };

  return (
    <div className="space-y-8">
      <Link to="/eleves" className="text-sm text-or-cachet hover:underline">
        ← Retour aux élèves
      </Link>
      <PageHeader
        eyebrow="Élèves"
        title="Import Excel / CSV"
        subtitle="Analysez le fichier, corrigez les erreurs, puis confirmez l’import."
        actions={
          <button type="button" onClick={downloadTemplate} className="btn-secondary">
            Modèle Excel
          </button>
        }
      />

      <form onSubmit={handlePreview} className="card space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="label">Année scolaire</span>
            <select
              className="input"
              value={idAnnee}
              onChange={(e) => setIdAnnee(e.target.value)}
              required
            >
              <option value="">— Choisir —</option>
              {annees.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.libelle}
                  {a.est_active ? ' (active)' : ''}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="label">Classe par défaut (optionnel)</span>
            <select
              className="input"
              value={idClasse}
              onChange={(e) => setIdClasse(e.target.value)}
            >
              <option value="">— Depuis le fichier —</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.libelle || c.nom}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label className="block">
          <span className="label">Fichier (.xlsx ou .csv)</span>
          <input
            type="file"
            accept=".xlsx,.xlsm,.csv"
            className="input"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            required
          />
        </label>
        <p className="text-xs text-texte-secondaire">
          Colonnes : matricule (opt.), nom*, prenom*, sexe, date_naissance, lieu_naissance,
          adresse, classe*
        </p>
        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? 'Analyse…' : 'Analyser le fichier'}
        </button>
      </form>

      {preview && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-texte-secondaire">
              {preview.summary?.total} ligne(s) —{' '}
              <span className="text-feuille">{preview.summary?.ok} OK</span> —{' '}
              <span className="text-brique">{preview.summary?.errors} erreur(s)</span>
            </p>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={confirming || !preview.summary?.ok}
              className="btn-primary"
            >
              {confirming
                ? 'Import…'
                : `Importer ${preview.summary?.ok || 0} élève(s) valide(s)`}
            </button>
          </div>
          <div className="overflow-x-auto rounded-card border border-bordure bg-blanc">
            <table className="min-w-full text-sm">
              <thead className="bg-craie text-left text-xs uppercase text-texte-secondaire">
                <tr>
                  <th className="px-3 py-2">Ligne</th>
                  <th className="px-3 py-2">Statut</th>
                  <th className="px-3 py-2">Matricule</th>
                  <th className="px-3 py-2">Nom</th>
                  <th className="px-3 py-2">Classe</th>
                  <th className="px-3 py-2">Erreurs</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-bordure/50">
                {preview.items.map((row) => (
                  <tr key={`${row.line}-${row.data?.matricule || ''}`}>
                    <td className="px-3 py-2">{row.line}</td>
                    <td className="px-3 py-2">
                      {row.status === 'ok' ? (
                        <span className="badge-success">OK</span>
                      ) : (
                        <span className="badge-danger">Erreur</span>
                      )}
                    </td>
                    <td className="px-3 py-2">{row.data?.matricule || '—'}</td>
                    <td className="px-3 py-2">
                      {row.data?.prenom} {row.data?.nom}
                    </td>
                    <td className="px-3 py-2">{row.data?.classe_libelle || '—'}</td>
                    <td className="px-3 py-2 text-brique">
                      {(row.errors || []).join(' · ') || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
