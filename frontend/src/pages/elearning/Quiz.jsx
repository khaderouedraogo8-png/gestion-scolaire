import { useCallback, useEffect, useState } from 'react';
import { elearningApi } from '../../services/api/elearning';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';

export default function Quiz() {
  const toast = useToast();
  const { isEnseignant, isAdmin } = useAuth();
  const canWrite = isEnseignant || isAdmin;
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    titre: '',
    id_classe: '',
    duree_minutes: '20',
    publie: false,
    questions_json: '[]',
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
        publie: form.publie,
        questions,
      });
      toast.success('Quiz créé');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="E-learning" title="Quiz" subtitle="Questionnaires et évaluations en ligne" />

      {canWrite && (
        <form onSubmit={create} className="card-premium grid gap-3 p-5 sm:grid-cols-2">
          <FormField label="Titre" name="titre" value={form.titre} onChange={(e) => setForm((f) => ({ ...f, titre: e.target.value }))} required />
          <FormField label="ID classe" name="id_classe" value={form.id_classe} onChange={(e) => setForm((f) => ({ ...f, id_classe: e.target.value }))} />
          <FormField label="Durée (min)" name="duree_minutes" value={form.duree_minutes} onChange={(e) => setForm((f) => ({ ...f, duree_minutes: e.target.value }))} />
          <FormField
            label="Questions (JSON)"
            name="questions_json"
            type="textarea"
            value={form.questions_json}
            onChange={(e) => setForm((f) => ({ ...f, questions_json: e.target.value }))}
            helpText='Ex. [{"q":"…","choices":["a","b"],"answer":0}]'
          />
          <button type="submit" className="btn-primary w-fit">Créer</button>
        </form>
      )}

      <Table
        columns={[
          { key: 'titre', header: 'Titre' },
          { key: 'duree_minutes', header: 'Durée', render: (r) => (r.duree_minutes != null ? `${r.duree_minutes} min` : '—') },
          { key: 'publie', header: 'Publié', render: (r) => (r.publie ? 'Oui' : 'Non') },
        ]}
        data={rows}
        loading={loading}
        emptyMessage="Aucun quiz."
      />
    </div>
  );
}
