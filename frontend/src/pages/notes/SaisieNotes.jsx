import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { notesApi } from '../../services/api/notes';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';
import Badge from '../../components/Badge';

export default function SaisieNotes() {
  const { evaluationId } = useParams();
  const toast = useToast();

  const [evaluations, setEvaluations] = useState([]);
  const [selectedId, setSelectedId] = useState(evaluationId || '');
  const [evaluation, setEvaluation] = useState(null);
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [closing, setClosing] = useState(false);

  useEffect(() => {
    notesApi
      .listEvaluations()
      .then((data) => setEvaluations(Array.isArray(data) ? data : data.items || []))
      .catch(() => toast.error('Erreur lors du chargement'));
  }, [toast]);

  useEffect(() => {
    if (!selectedId) {
      setLoading(false);
      return;
    }
    const loadNotes = async () => {
      setLoading(true);
      try {
        const data = await notesApi.getNotesGrid(selectedId);
        setEvaluation(data.evaluation);
        setNotes(data.notes || []);
      } catch {
        toast.error('Erreur lors du chargement des notes');
        setNotes([]);
      } finally {
        setLoading(false);
      }
    };
    loadNotes();
  }, [selectedId, toast]);

  const updateNote = (eleveId, field, value) => {
    setNotes((prev) =>
      prev.map((n) => (n.id_eleve === eleveId ? { ...n, [field]: value } : n))
    );
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await notesApi.saveNotes(selectedId, notes);
      toast.success('Notes enregistrées — moyennes recalculées');
    } catch (err) {
      toast.error(err.response?.data?.message || "Erreur lors de l'enregistrement");
    } finally {
      setSaving(false);
    }
  };

  const handleCloturer = async () => {
    setClosing(true);
    try {
      const updated = await notesApi.cloturerEvaluation(selectedId);
      setEvaluation(updated);
      toast.success('Saisie clôturée — notes visibles par les parents');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur lors de la clôture');
    } finally {
      setClosing(false);
    }
  };

  const handleRouvrir = async () => {
    setClosing(true);
    try {
      const updated = await notesApi.rouvrirEvaluation(selectedId);
      setEvaluation(updated);
      toast.success('Évaluation rouverte pour correction');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    } finally {
      setClosing(false);
    }
  };

  return (
    <div className="space-y-8">
      <Link to="/notes/evaluations" className="text-sm text-or-cachet hover:underline">
        ← Retour aux évaluations
      </Link>
      <PageHeader eyebrow="Notes & bulletins" title="Saisie des notes" />

      <div className="card">
        <label className="label">Sélectionner une évaluation</label>
        <select
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
          className="input max-w-lg"
        >
          <option value="">— Choisir —</option>
          {evaluations.map((ev) => (
            <option key={ev.id} value={ev.id}>
              {ev.libelle || ev.type_evaluation} — {ev.matiere_nom} ({ev.classe_nom})
            </option>
          ))}
        </select>
      </div>

      {loading && selectedId ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-or-cachet-clair border-t-or-cachet" />
        </div>
      ) : selectedId && evaluation ? (
        <>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="font-medium text-encre">{evaluation.libelle}</p>
              <p className="page-subtitle">
                {evaluation.matiere_nom} — {evaluation.classe_nom} — Trimestre{' '}
                {evaluation.trimestre_numero}
              </p>
              <p className="mt-1">
                {evaluation.statut_saisie === 'cloturee' ? (
                  <Badge variant="success">Saisie clôturée</Badge>
                ) : (
                  <Badge variant="warning">Saisie en cours</Badge>
                )}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={handleSave} disabled={saving || evaluation.statut_saisie === 'cloturee'} className="btn-primary">
                {saving ? 'Enregistrement...' : 'Enregistrer les notes'}
              </button>
              {evaluation.statut_saisie === 'cloturee' ? (
                <button type="button" onClick={handleRouvrir} disabled={closing} className="btn-secondary">
                  Rouvrir la saisie
                </button>
              ) : (
                <button type="button" onClick={handleCloturer} disabled={closing} className="btn-secondary">
                  {closing ? 'Clôture...' : 'Clôturer et publier'}
                </button>
              )}
            </div>
          </div>

          {notes.length === 0 ? (
            <div className="card text-center page-subtitle">
              Aucun élève inscrit dans cette classe pour l'instant
            </div>
          ) : (
            <div className="overflow-hidden rounded-card border border-bordure bg-blanc">
              <table className="min-w-full divide-y divide-bordure">
                <thead className="bg-craie">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-texte-secondaire">
                      Élève
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-texte-secondaire w-24">
                      Note /20
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold uppercase text-texte-secondaire w-20">
                      Absent
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-texte-secondaire">
                      Appréciation
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-bordure/50">
                  {notes.map((n) => (
                    <tr key={n.id_eleve}>
                      <td className="px-4 py-3 text-sm">
                        <p className="font-medium">
                          {n.prenom} {n.nom}
                        </p>
                        <p className="text-xs text-texte-secondaire">{n.matricule}</p>
                      </td>
                      <td className="px-4 py-3">
                        <input
                          type="number"
                          min="0"
                          max="20"
                          step="0.25"
                          value={n.valeur_note ?? ''}
                          disabled={n.absent}
                          onChange={(e) =>
                            updateNote(n.id_eleve, 'valeur_note', e.target.value)
                          }
                          className="input w-20 text-center"
                        />
                      </td>
                      <td className="px-4 py-3 text-center">
                        <input
                          type="checkbox"
                          checked={Boolean(n.absent)}
                          onChange={(e) => {
                            updateNote(n.id_eleve, 'absent', e.target.checked);
                            if (e.target.checked) {
                              updateNote(n.id_eleve, 'valeur_note', null);
                            }
                          }}
                          className="h-4 w-4 rounded border-bordure text-or-cachet"
                        />
                      </td>
                      <td className="px-4 py-3">
                        <input
                          type="text"
                          value={n.appreciation || ''}
                          onChange={(e) =>
                            updateNote(n.id_eleve, 'appreciation', e.target.value)
                          }
                          className="input"
                          placeholder="Commentaire..."
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}
