import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { notesApi } from '../../services/api/notes';
import { useToast } from '../../components/Toast';

export default function SaisieNotes() {
  const { evaluationId } = useParams();
  const toast = useToast();

  const [evaluations, setEvaluations] = useState([]);
  const [selectedId, setSelectedId] = useState(evaluationId || '');
  const [evaluation, setEvaluation] = useState(null);
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

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

  return (
    <div className="space-y-6">
      <div>
        <Link to="/notes/evaluations" className="text-sm text-primary-600 hover:underline">
          ← Retour aux évaluations
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-slate-900">Saisie des notes</h1>
      </div>

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
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
        </div>
      ) : selectedId && evaluation ? (
        <>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="font-medium text-slate-900">{evaluation.libelle}</p>
              <p className="text-sm text-slate-500">
                {evaluation.matiere_nom} — {evaluation.classe_nom} — Trimestre{' '}
                {evaluation.trimestre_numero}
              </p>
            </div>
            <button type="button" onClick={handleSave} disabled={saving} className="btn-primary">
              {saving ? 'Enregistrement...' : 'Enregistrer les notes'}
            </button>
          </div>

          {notes.length === 0 ? (
            <div className="card text-center text-sm text-slate-500">
              Aucun élève inscrit dans cette classe
            </div>
          ) : (
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-600">
                      Élève
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-600 w-24">
                      Note /20
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold uppercase text-slate-600 w-20">
                      Absent
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-600">
                      Appréciation
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {notes.map((n) => (
                    <tr key={n.id_eleve}>
                      <td className="px-4 py-3 text-sm">
                        <p className="font-medium">
                          {n.prenom} {n.nom}
                        </p>
                        <p className="text-xs text-slate-500">{n.matricule}</p>
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
                          className="h-4 w-4 rounded border-slate-300 text-primary-600"
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
