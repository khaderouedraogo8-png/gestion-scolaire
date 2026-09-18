import { useCallback, useEffect, useState } from 'react';
import { elearningApi } from '../../services/api/elearning';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';

/** Exemple questions JSON pour l’aide UI. */
const SAMPLE_Q = '[{"q":"2+2 ?","choices":["3","4","5"],"answer":1,"points":1}]';

export default function Quiz() {
  const toast = useToast();
  const { isEnseignant, isAdmin, user } = useAuth();
  const canWrite = isEnseignant || isAdmin;
  const isEleve = user?.role === 'eleve';
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [form, setForm] = useState({
    titre: '',
    id_classe: '',
    duree_minutes: '20',
    note_max: '20',
    tentatives_max: '3',
    publie: true,
    questions_json: SAMPLE_Q,
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await elearningApi.listQuiz();
      setRows(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Impossible de charger les quiz');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const create = async (e) => {
    e.preventDefault();
    let questions = [];
    try {
      questions = JSON.parse(form.questions_json || '[]');
    } catch {
      toast.error('JSON questions invalide');
      return;
    }
    try {
      await elearningApi.createQuiz({
        titre: form.titre,
        id_classe: form.id_classe || null,
        duree_minutes: Number(form.duree_minutes) || null,
        note_max: form.note_max || '20',
        tentatives_max: Number(form.tentatives_max) || 3,
        publie: form.publie,
        questions,
      });
      toast.success('Quiz créé');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const openPasser = async (id) => {
    try {
      const quiz = await elearningApi.getQuiz(id);
      setActive(quiz);
      setAnswers({});
      setResult(null);
    } catch {
      toast.error('Quiz introuvable');
    }
  };

  const submitPasser = async () => {
    if (!active) return;
    const qs = Array.isArray(active.questions) ? active.questions : [];
    const reponses = qs.map((_, i) => (answers[i] != null ? Number(answers[i]) : null));
    try {
      const res = await elearningApi.passerQuiz(active.id, { reponses });
      setResult(res);
      toast.success(`Note : ${res.note}/${active.note_max || 20}`);
    } catch (err) {
      toast.error(err.response?.data?.message || 'Échec soumission');
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="E-learning" title="Quiz" subtitle="QCM corrigés automatiquement" />

      {canWrite && (
        <form onSubmit={create} className="card-premium grid gap-3 p-5 sm:grid-cols-2">
          <FormField
            label="Titre"
            name="titre"
            value={form.titre}
            onChange={(e) => setForm((f) => ({ ...f, titre: e.target.value }))}
            required
          />
          <FormField
            label="ID classe"
            name="id_classe"
            value={form.id_classe}
            onChange={(e) => setForm((f) => ({ ...f, id_classe: e.target.value }))}
          />
          <FormField
            label="Durée (min)"
            name="duree_minutes"
            value={form.duree_minutes}
            onChange={(e) => setForm((f) => ({ ...f, duree_minutes: e.target.value }))}
          />
          <FormField
            label="Tentatives max"
            name="tentatives_max"
            value={form.tentatives_max}
            onChange={(e) => setForm((f) => ({ ...f, tentatives_max: e.target.value }))}
          />
          <FormField
            label="Questions (JSON)"
            name="questions_json"
            type="textarea"
            value={form.questions_json}
            onChange={(e) => setForm((f) => ({ ...f, questions_json: e.target.value }))}
            helpText='Ex. [{"q":"…","choices":["a","b"],"answer":0,"points":1}]'
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.publie}
              onChange={(e) => setForm((f) => ({ ...f, publie: e.target.checked }))}
            />
            Publier immédiatement
          </label>
          <button type="submit" className="btn-primary w-fit">
            Créer
          </button>
        </form>
      )}

      <Table
        columns={[
          { key: 'titre', header: 'Titre' },
          {
            key: 'duree_minutes',
            header: 'Durée',
            render: (r) => (r.duree_minutes != null ? `${r.duree_minutes} min` : '—'),
          },
          { key: 'publie', header: 'Publié', render: (r) => (r.publie ? 'Oui' : 'Non') },
          {
            key: 'actions',
            header: '',
            render: (r) =>
              (isEleve || canWrite) && r.publie ? (
                <button type="button" className="btn-secondary text-xs" onClick={() => openPasser(r.id)}>
                  Passer
                </button>
              ) : null,
          },
        ]}
        data={rows}
        loading={loading}
        emptyMessage="Aucun quiz."
      />

      {active && (
        <div className="card-premium space-y-4 p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="font-display text-lg font-semibold text-encre">{active.titre}</h2>
              <p className="text-sm text-encre/60">
                {Array.isArray(active.questions) ? active.questions.length : 0} questions · note /{' '}
                {active.note_max || 20}
              </p>
            </div>
            <button type="button" className="btn-ghost text-sm" onClick={() => setActive(null)}>
              Fermer
            </button>
          </div>
          {(active.questions || []).map((q, i) => (
            <fieldset key={i} className="space-y-2 border-t border-bordure/40 pt-3">
              <legend className="font-medium text-encre">
                {i + 1}. {q.q}
              </legend>
              <div className="flex flex-col gap-1">
                {(q.choices || []).map((c, ci) => (
                  <label key={ci} className="flex items-center gap-2 text-sm">
                    <input
                      type="radio"
                      name={`q-${i}`}
                      checked={answers[i] === ci}
                      onChange={() => setAnswers((a) => ({ ...a, [i]: ci }))}
                    />
                    {c}
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
          {!result ? (
            <button type="button" className="btn-primary" onClick={submitPasser}>
              Soumettre
            </button>
          ) : (
            <p className="rounded-lg bg-parchemin/60 p-3 text-sm">
              Score {result.nb_correctes}/{result.nb_questions} — note{' '}
              <strong>
                {result.note}/{active.note_max || 20}
              </strong>
              {result.tentatives_restantes != null && (
                <> · {result.tentatives_restantes} tentative(s) restante(s)</>
              )}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
