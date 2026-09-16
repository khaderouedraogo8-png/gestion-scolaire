import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { notesApi } from '../../services/api/notes';
import { configApi } from '../../services/api/config';
import { gradingApi } from '../../services/api/grading';
import Table from '../../components/Table';
import { emptyIcons } from '../../utils/emptyIcons';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';

export default function EvaluationList() {
  const toast = useToast();
  const { isAdmin, isEnseignant } = useAuth();
  const canWrite = isAdmin || isEnseignant;

  const [evaluations, setEvaluations] = useState([]);
  const [classes, setClasses] = useState([]);
  const [trimestres, setTrimestres] = useState([]);
  const [matieres, setMatieres] = useState([]);
  const [evaluationTypes, setEvaluationTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [classeFilter, setClasseFilter] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    libelle: '',
    id_classe: '',
    id_matiere: '',
    id_trimestre: '',
    type_evaluation: 'devoir',
    date_evaluation: new Date().toISOString().slice(0, 10),
    coefficient: '1',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await notesApi.listEvaluations({
        id_classe: classeFilter || undefined,
      });
      setEvaluations(Array.isArray(data) ? data : data.items || []);
    } catch {
      toast.error('Erreur lors du chargement des évaluations');
    } finally {
      setLoading(false);
    }
  }, [classeFilter, toast]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const init = async () => {
      try {
        const [classesData, matieresData, anneesData, typesData] = await Promise.all([
          configApi.listClasses(),
          notesApi.listMatieres(),
          configApi.listAnnees(),
          gradingApi.listEvaluationTypes({ active_only: true }),
        ]);
        setClasses(classesData.items || classesData || []);
        setMatieres(matieresData.items || matieresData || []);
        const types = typesData.items || typesData || [];
        setEvaluationTypes(types);
        if (types.length && !types.some((t) => t.code === 'devoir')) {
          setForm((f) => ({ ...f, type_evaluation: types[0].code }));
        }
        const anneeList = anneesData.items || anneesData || [];
        const active = anneeList.find((a) => a.est_active);
        if (active) {
          const trims = await configApi.listTrimestres(active.id);
          const trimList = trims.items || trims || [];
          setTrimestres(trimList);
          if (trimList.length) {
            setForm((f) => ({ ...f, id_trimestre: String(trimList[0].id) }));
          }
        }
      } catch {
        /* ignore */
      }
    };
    init();
  }, []);

  const typeOptions =
    evaluationTypes.length > 0
      ? evaluationTypes.map((t) => ({ value: t.code, label: t.label || t.code }))
      : [];

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!typeOptions.length) {
      toast.error('Catalogue des types d’évaluation indisponible');
      return;
    }
    if (!form.type_evaluation) {
      toast.error('Sélectionnez un type d’évaluation');
      return;
    }
    setSaving(true);
    try {
      await notesApi.createEvaluation({
        libelle: form.libelle,
        id_classe: form.id_classe,
        id_matiere: form.id_matiere,
        id_trimestre: form.id_trimestre,
        type_evaluation: form.type_evaluation,
        date_evaluation: form.date_evaluation,
        coefficient: Number(form.coefficient),
      });
      toast.success('Évaluation créée');
      setModalOpen(false);
      setForm((f) => ({
        ...f,
        libelle: '',
        id_classe: '',
        id_matiere: '',
      }));
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur lors de la création');
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    {
      key: 'libelle',
      header: 'Évaluation',
      render: (r) => <span className="font-medium">{r.libelle || r.type_evaluation}</span>,
    },
    {
      key: 'type',
      header: 'Type',
      render: (r) => {
        const t = evaluationTypes.find((x) => x.code === r.type_evaluation);
        return t?.label || r.type_evaluation || '—';
      },
    },
    { key: 'matiere', header: 'Matière', render: (r) => r.matiere_nom || '—' },
    { key: 'classe', header: 'Classe', render: (r) => r.classe_nom || '—' },
    {
      key: 'trimestre',
      header: 'Trimestre',
      render: (r) => (r.trimestre_numero ? `T${r.trimestre_numero}` : '—'),
    },
    { key: 'date', header: 'Date', render: (r) => r.date_evaluation || '—' },
    {
      key: 'coef',
      header: 'Coef.',
      render: (r) => r.coefficient ?? '—',
    },
    {
      key: 'actions',
      header: '',
      render: (r) =>
        canWrite ? (
          <Link to={`/notes/saisie/${r.id}`} className="text-sm font-medium text-or-cachet">
            Saisir notes →
          </Link>
        ) : null,
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Notes & bulletins"
        title="Évaluations"
        subtitle="Gestion des évaluations et saisie des notes — types issus du catalogue école"
        actions={
          canWrite && (
            <button type="button" onClick={() => setModalOpen(true)} className="btn-primary">
              + Nouvelle évaluation
            </button>
          )
        }
      />

      <Table
        columns={columns}
        data={evaluations}
        loading={loading}
        filters={
          <select
            value={classeFilter}
            onChange={(e) => setClasseFilter(e.target.value)}
            className="input w-auto"
          >
            <option value="">Toutes les classes</option>
            {classes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.libelle || c.nom}
              </option>
            ))}
          </select>
        }
        emptyIcon={emptyIcons.evaluations}
        emptyMessage="Aucune évaluation pour l'instant — créez-en une pour commencer la saisie."
      />

      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Nouvelle évaluation"
        size="md"
        footer={
          <>
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary">
              Annuler
            </button>
            <button type="submit" form="eval-form" disabled={saving} className="btn-primary">
              {saving ? 'Création...' : 'Créer'}
            </button>
          </>
        }
      >
        <form id="eval-form" onSubmit={handleCreate} className="space-y-4">
          <FormField
            label="Libellé"
            name="libelle"
            value={form.libelle}
            onChange={(e) => setForm({ ...form, libelle: e.target.value })}
            required
            placeholder="Ex. Devoir n°1 — Algèbre"
          />
          <FormField
            label="Classe"
            name="id_classe"
            type="select"
            value={form.id_classe}
            onChange={(e) => setForm({ ...form, id_classe: e.target.value })}
            required
            options={classes.map((c) => ({
              value: String(c.id),
              label: c.libelle || c.nom,
            }))}
          />
          <FormField
            label="Matière"
            name="id_matiere"
            type="select"
            value={form.id_matiere}
            onChange={(e) => setForm({ ...form, id_matiere: e.target.value })}
            required
            options={matieres.map((m) => ({
              value: String(m.id),
              label: m.libelle || m.nom,
            }))}
          />
          <FormField
            label="Trimestre"
            name="id_trimestre"
            type="select"
            value={form.id_trimestre}
            onChange={(e) => setForm({ ...form, id_trimestre: e.target.value })}
            required
            options={trimestres.map((t) => ({
              value: String(t.id),
              label: t.label || `Trimestre ${t.numero}`,
            }))}
          />
          <FormField
            label="Type d'évaluation"
            name="type_evaluation"
            type="select"
            value={form.type_evaluation}
            onChange={(e) => setForm({ ...form, type_evaluation: e.target.value })}
            required
            options={typeOptions}
          />
          <p className="text-xs text-texte-secondaire">
            Les poids dans la moyenne matière viennent du Ruleset actif (pas de % hardcodés ici).
          </p>
          <div className="grid grid-cols-2 gap-4">
            <FormField
              label="Coefficient (legacy évaluation)"
              name="coefficient"
              type="number"
              value={form.coefficient}
              onChange={(e) => setForm({ ...form, coefficient: e.target.value })}
              min="0.5"
              max="5"
              step="0.5"
            />
            <FormField
              label="Date"
              name="date_evaluation"
              type="date"
              value={form.date_evaluation}
              onChange={(e) => setForm({ ...form, date_evaluation: e.target.value })}
              required
            />
          </div>
        </form>
      </Modal>
    </div>
  );
}
