import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Scale } from 'lucide-react';
import { gradingApi } from '../../services/api/grading';
import { configApi } from '../../services/api/config';
import { notesApi } from '../../services/api/notes';
import Table from '../../components/Table';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import PageHeader from '../../components/PageHeader';
import Badge from '../../components/Badge';
import { useToast } from '../../components/Toast';
import { useAuth } from '../../hooks/useAuth';
import { apiErrorMessage, asList } from '../../utils/academicLabels';
import {
  ENGINE_MISSING_POLICY_INFO,
  EVALUATION_CONTEXT_OPTIONS,
  ROUNDING_MODE_OPTIONS,
  RULESET_STATUS,
  RULESET_STATUS_OPTIONS,
  formatScaleMax,
  formatWeight,
  rulesetStatusBadgeVariant,
  rulesetStatusLabel,
  sumWeights,
  weightsAreValid,
} from '../../utils/gradingLabels';
import { emptyIcons } from '../../utils/emptyIcons';

const EMPTY_CREATE = {
  code: '',
  name: '',
  description: '',
  academic_year_id: '',
  program_id: '',
  level_id: '',
  subject_id: '',
  scale_max: '20.00',
  rounding_mode: 'half_up',
  rounding_precision: '2',
};

const EMPTY_COMPONENT = {
  code: '',
  label: '',
  evaluation_type_id: '',
  evaluation_context: 'normal',
  weight: '',
  sequence: '1',
  is_required: true,
};

function extractItems(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.items)) return payload.items;
  return [];
}

function formatDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('fr-FR', {
      dateStyle: 'short',
      timeStyle: 'short',
    });
  } catch {
    return iso;
  }
}

export default function GradingRulesets() {
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;
  const navigate = useNavigate();
  const { hasAnyRole } = useAuth();
  const canManage = hasAnyRole(['administrateur', 'directeur', 'super_admin']);

  const [items, setItems] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, per_page: 25, total: 0, pages: 0 });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [yearFilter, setYearFilter] = useState('');
  const [programFilter, setProgramFilter] = useState('');
  const [page, setPage] = useState(1);

  const [annees, setAnnees] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [niveaux, setNiveaux] = useState([]);
  const [matieres, setMatieres] = useState([]);
  const [evalTypes, setEvalTypes] = useState([]);

  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_CREATE);
  const [draftComponents, setDraftComponents] = useState([{ ...EMPTY_COMPONENT }]);
  const [fieldErrors, setFieldErrors] = useState({});
  const [saving, setSaving] = useState(false);

  const yearOptions = useMemo(
    () =>
      asList(annees).map((a) => ({
        value: a.id,
        label: a.libelle || a.label || String(a.id),
      })),
    [annees]
  );
  const programOptions = useMemo(
    () =>
      asList(programs)
        .filter((p) => p.is_active !== false)
        .map((p) => ({ value: p.id, label: `${p.code} — ${p.name}` })),
    [programs]
  );
  const niveauOptions = useMemo(
    () =>
      asList(niveaux).map((n) => ({
        value: n.id,
        label: n.libelle || n.name || String(n.id),
      })),
    [niveaux]
  );
  const matiereOptions = useMemo(
    () =>
      asList(matieres).map((m) => ({
        value: m.id,
        label: m.libelle || m.name || m.code || String(m.id),
      })),
    [matieres]
  );
  const evalTypeOptions = useMemo(
    () =>
      asList(evalTypes).map((t) => ({
        value: t.id,
        label: `${t.label || t.code} (${t.code})`,
      })),
    [evalTypes]
  );

  const loadRefs = useCallback(async () => {
    try {
      const [a, p, n, m, et] = await Promise.all([
        configApi.listAnnees(),
        configApi.listPrograms({ is_active: true }),
        configApi.listNiveaux(),
        notesApi.listMatieres(),
        gradingApi.listEvaluationTypes({ active_only: true }),
      ]);
      setAnnees(asList(a?.items ?? a));
      setPrograms(asList(p));
      setNiveaux(asList(n?.items ?? n));
      setMatieres(asList(m));
      setEvalTypes(extractItems(et));
    } catch (err) {
      toastRef.current.error(apiErrorMessage(err, 'Impossible de charger les référentiels.'));
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const params = { page, per_page: 25 };
      if (statusFilter) params.status = statusFilter;
      if (yearFilter) params.academic_year_id = yearFilter;
      if (programFilter) params.program_id = programFilter;
      const data = await gradingApi.listRulesets(params);
      setItems(extractItems(data));
      setPagination({
        page: data?.page || data?.pagination?.page || page,
        per_page: data?.per_page || data?.pagination?.per_page || 25,
        total: data?.total || data?.pagination?.total || 0,
        pages: data?.pages || data?.pagination?.pages || 0,
      });
    } catch (err) {
      const msg = apiErrorMessage(err, 'Impossible de charger les règles de notation.');
      setLoadError(msg);
      toastRef.current.error(msg);
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, yearFilter, programFilter]);

  useEffect(() => {
    loadRefs();
  }, [loadRefs]);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setForm(EMPTY_CREATE);
    setDraftComponents([{ ...EMPTY_COMPONENT, sequence: '1' }]);
    setFieldErrors({});
    setModalOpen(true);
  };

  const setField = (name, value) => {
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const updateDraftComponent = (index, patch) => {
    setDraftComponents((prev) => prev.map((c, i) => (i === index ? { ...c, ...patch } : c)));
  };

  const addDraftComponent = () => {
    setDraftComponents((prev) => [
      ...prev,
      { ...EMPTY_COMPONENT, sequence: String(prev.length + 1) },
    ]);
  };

  const removeDraftComponent = (index) => {
    setDraftComponents((prev) => prev.filter((_, i) => i !== index));
  };

  const weightsTotal = sumWeights(draftComponents);
  const weightsOk = weightsAreValid(draftComponents);

  const validateCreate = () => {
    const errors = {};
    if (!form.code.trim()) errors.code = 'Le code est obligatoire.';
    if (!form.name.trim()) errors.name = 'Le nom est obligatoire.';
    if (!form.academic_year_id) errors.academic_year_id = "L'année scolaire est obligatoire.";
    if (!form.scale_max || Number(form.scale_max) <= 0) {
      errors.scale_max = "L'échelle maximale doit être > 0.";
    }
    if (draftComponents.length === 0) {
      errors.components = 'Ajoutez au moins une composante (ex. Devoir / Composition).';
    }
    draftComponents.forEach((c, i) => {
      if (!c.code.trim()) errors[`comp_code_${i}`] = 'Code obligatoire.';
      if (!c.label.trim()) errors[`comp_label_${i}`] = 'Libellé obligatoire.';
      if (!c.evaluation_type_id) errors[`comp_type_${i}`] = "Type d'évaluation obligatoire.";
      const w = Number(c.weight);
      if (!Number.isFinite(w) || w <= 0 || w > 100) {
        errors[`comp_weight_${i}`] = 'Poids invalide (0 < poids ≤ 100).';
      }
    });
    if (draftComponents.length > 0 && !weightsOk) {
      errors.weights = `La somme des poids doit être 100 % (actuellement ${weightsTotal.toFixed(2)} %).`;
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!canManage) return;
    if (!validateCreate()) return;
    setSaving(true);
    try {
      const payload = {
        code: form.code.trim().toUpperCase(),
        name: form.name.trim(),
        description: form.description.trim() || null,
        academic_year_id: form.academic_year_id,
        program_id: form.program_id || null,
        level_id: form.level_id || null,
        subject_id: form.subject_id || null,
        scale_max: form.scale_max,
        rounding_mode: form.rounding_mode,
        rounding_precision: Number(form.rounding_precision),
        components: draftComponents.map((c, i) => ({
          code: c.code.trim().toUpperCase(),
          label: c.label.trim(),
          evaluation_type_id: c.evaluation_type_id,
          evaluation_context: c.evaluation_context || 'normal',
          weight: String(c.weight),
          sequence: Number(c.sequence) || i + 1,
          is_required: Boolean(c.is_required),
        })),
      };
      const created = await gradingApi.createRuleset(payload);
      toast.success('Règle de notation créée (brouillon).');
      setModalOpen(false);
      navigate(`/config/regles-notation/${created.id}`);
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Création impossible.'));
    } finally {
      setSaving(false);
    }
  };

  const yearLabel = (id) => yearOptions.find((o) => String(o.value) === String(id))?.label || '—';
  const programLabel = (id) =>
    id ? programOptions.find((o) => String(o.value) === String(id))?.label || id : 'Tous programmes';
  const subjectLabel = (id) =>
    id ? matiereOptions.find((o) => String(o.value) === String(id))?.label || id : 'Toutes matières';

  const columns = [
    {
      key: 'name',
      header: 'Nom',
      render: (r) => (
        <div>
          <Link
            to={`/config/regles-notation/${r.id}`}
            className="font-medium text-encre hover:underline"
          >
            {r.name}
          </Link>
          <div className="text-xs text-texte-secondaire">{r.code}</div>
        </div>
      ),
    },
    {
      key: 'scope',
      header: 'Contexte',
      render: (r) => (
        <div className="text-sm text-encre/80">
          <div>{yearLabel(r.academic_year_id)}</div>
          <div className="text-xs text-texte-secondaire">
            {programLabel(r.program_id)} · {subjectLabel(r.subject_id)}
          </div>
        </div>
      ),
    },
    {
      key: 'version',
      header: 'Version',
      align: 'right',
      render: (r) => <span className="tabular-nums">v{r.version}</span>,
    },
    {
      key: 'status',
      header: 'Statut',
      render: (r) => (
        <Badge variant={rulesetStatusBadgeVariant(r.status)}>
          {rulesetStatusLabel(r.status)}
        </Badge>
      ),
    },
    {
      key: 'scale',
      header: 'Échelle',
      render: (r) => formatScaleMax(r.scale_max),
    },
    {
      key: 'created_at',
      header: 'Création',
      render: (r) => formatDate(r.created_at),
    },
    {
      key: 'updated_at',
      header: 'Modification',
      render: (r) => formatDate(r.updated_at),
    },
    {
      key: 'actions',
      header: '',
      render: (r) => (
        <Link to={`/config/regles-notation/${r.id}`} className="btn-ghost text-sm">
          Ouvrir
        </Link>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Configuration"
        title="Règles de notation"
        subtitle="Configurez les pondérations d'évaluation (poids ≠ coefficients matière). Le calcul reste côté serveur."
        actions={
          canManage ? (
            <button type="button" className="btn-primary" onClick={openCreate}>
              <Plus className="mr-1.5 inline h-4 w-4" aria-hidden />
              Nouveau ruleset
            </button>
          ) : null
        }
      />

      <section
        className="rounded-card border border-bordure bg-craie/40 p-4 text-sm text-encre/80"
        aria-labelledby="missing-policy-title"
      >
        <h2 id="missing-policy-title" className="mb-2 flex items-center gap-2 font-medium text-encre">
          <Scale className="h-4 w-4" aria-hidden />
          Politique des notes manquantes (moteur de calcul)
        </h2>
        <ul className="space-y-2">
          {ENGINE_MISSING_POLICY_INFO.map((info) => (
            <li key={info.id}>
              <strong>{info.name}</strong>
              <span className="text-texte-secondaire"> — {info.effect}. </span>
              {info.description}
            </li>
          ))}
        </ul>
        <p className="mt-2 text-xs text-texte-secondaire">
          Non configurable via l&apos;API actuelle. Affichage : « — » = aucune note (missing) ;
          « 0 » = zéro explicite. Ne jamais confondre.
        </p>
      </section>

      {loadError ? (
        <div className="rounded-card border border-brique/40 bg-brique/5 p-4 text-sm" role="alert">
          <p>{loadError}</p>
          <button type="button" className="btn-secondary mt-2" onClick={load}>
            Réessayer
          </button>
        </div>
      ) : (
        <Table
          columns={columns}
          data={items}
          loading={loading}
          emptyIcon={emptyIcons.coefficients}
          emptyMessage="Aucun ruleset configuré. Créez un brouillon pour définir les pondérations."
          filters={
            <>
              <select
                aria-label="Filtrer par statut"
                value={statusFilter}
                onChange={(e) => {
                  setPage(1);
                  setStatusFilter(e.target.value);
                }}
                className="input w-auto"
              >
                {RULESET_STATUS_OPTIONS.map((o) => (
                  <option key={o.value || 'all'} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
              <select
                aria-label="Filtrer par année scolaire"
                value={yearFilter}
                onChange={(e) => {
                  setPage(1);
                  setYearFilter(e.target.value);
                }}
                className="input w-auto"
              >
                <option value="">Toutes les années</option>
                {yearOptions.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
              <select
                aria-label="Filtrer par programme"
                value={programFilter}
                onChange={(e) => {
                  setPage(1);
                  setProgramFilter(e.target.value);
                }}
                className="input w-auto"
              >
                <option value="">Tous les programmes</option>
                {programOptions.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </>
          }
          pagination={
            pagination.pages > 1
              ? {
                  page: pagination.page,
                  perPage: pagination.per_page,
                  total: pagination.total,
                  totalPages: pagination.pages,
                  onPageChange: setPage,
                }
              : null
          }
        />
      )}

      <Modal
        isOpen={modalOpen}
        onClose={() => !saving && setModalOpen(false)}
        title="Nouveau ruleset (brouillon)"
        size="xl"
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              disabled={saving}
              onClick={() => setModalOpen(false)}
            >
              Annuler
            </button>
            <button
              type="submit"
              form="grading-ruleset-create"
              className="btn-primary"
              disabled={saving || !canManage}
            >
              {saving ? 'Enregistrement…' : 'Créer le brouillon'}
            </button>
          </>
        }
      >
        <form id="grading-ruleset-create" className="space-y-4" onSubmit={handleCreate} noValidate>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField
              label="Code"
              name="code"
              required
              value={form.code}
              onChange={(e) => setField('code', e.target.value)}
              error={fieldErrors.code}
              placeholder="LDC-GEN"
            />
            <FormField
              label="Nom"
              name="name"
              required
              value={form.name}
              onChange={(e) => setField('name', e.target.value)}
              error={fieldErrors.name}
              placeholder="Pondération générale"
            />
          </div>
          <FormField
            label="Description"
            name="description"
            type="textarea"
            value={form.description}
            onChange={(e) => setField('description', e.target.value)}
            rows={2}
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField
              label="Année scolaire"
              name="academic_year_id"
              type="select"
              required
              value={form.academic_year_id}
              onChange={(e) => setField('academic_year_id', e.target.value)}
              options={yearOptions}
              error={fieldErrors.academic_year_id}
            />
            <FormField
              label="Programme (optionnel)"
              name="program_id"
              type="select"
              value={form.program_id}
              onChange={(e) => setField('program_id', e.target.value)}
              options={programOptions}
              helpText="Vide = tous les programmes (wildcard)."
            />
            <FormField
              label="Niveau (optionnel)"
              name="level_id"
              type="select"
              value={form.level_id}
              onChange={(e) => setField('level_id', e.target.value)}
              options={niveauOptions}
              helpText="Exige un programme si renseigné."
            />
            <FormField
              label="Matière (optionnel)"
              name="subject_id"
              type="select"
              value={form.subject_id}
              onChange={(e) => setField('subject_id', e.target.value)}
              options={matiereOptions}
            />
          </div>
          <p className="text-xs text-texte-secondaire">
            Classe et période ne sont pas des axes de ruleset en V1 (non stockés).
          </p>
          <div className="grid gap-3 sm:grid-cols-3">
            <FormField
              label="Échelle maximale"
              name="scale_max"
              type="number"
              required
              value={form.scale_max}
              onChange={(e) => setField('scale_max', e.target.value)}
              error={fieldErrors.scale_max}
              helpText="Ex. 20 ou 100 — pas de /20 implicite."
              step="0.01"
              min="0.01"
            />
            <FormField
              label="Mode d'arrondi"
              name="rounding_mode"
              type="select"
              value={form.rounding_mode}
              onChange={(e) => setField('rounding_mode', e.target.value)}
              options={ROUNDING_MODE_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
            />
            <FormField
              label="Précision d'arrondi (décimales)"
              name="rounding_precision"
              type="number"
              value={form.rounding_precision}
              onChange={(e) => setField('rounding_precision', e.target.value)}
              min="0"
              max="6"
            />
          </div>

          <div className="space-y-3 border-t border-bordure pt-4">
            <div className="flex items-center justify-between gap-2">
              <h3 className="font-medium">Composantes d&apos;évaluation</h3>
              <button type="button" className="btn-ghost text-sm" onClick={addDraftComponent}>
                + Ajouter
              </button>
            </div>
            <p className="text-xs text-texte-secondaire">
              Les poids sont des pourcentages de la moyenne matière — distincts des coefficients
              matière.
            </p>
            {fieldErrors.components && (
              <p className="text-sm text-brique" role="alert">
                {fieldErrors.components}
              </p>
            )}
            {draftComponents.map((c, index) => (
              <div
                key={`draft-comp-${index}`}
                className="grid gap-2 rounded-lg border border-bordure/80 p-3 sm:grid-cols-2 lg:grid-cols-3"
              >
                <FormField
                  label="Code"
                  name={`comp_code_${index}`}
                  value={c.code}
                  onChange={(e) => updateDraftComponent(index, { code: e.target.value })}
                  error={fieldErrors[`comp_code_${index}`]}
                />
                <FormField
                  label="Libellé"
                  name={`comp_label_${index}`}
                  value={c.label}
                  onChange={(e) => updateDraftComponent(index, { label: e.target.value })}
                  error={fieldErrors[`comp_label_${index}`]}
                />
                <FormField
                  label="Type d'évaluation"
                  name={`comp_type_${index}`}
                  type="select"
                  value={c.evaluation_type_id}
                  onChange={(e) =>
                    updateDraftComponent(index, { evaluation_type_id: e.target.value })
                  }
                  options={evalTypeOptions}
                  error={fieldErrors[`comp_type_${index}`]}
                />
                <FormField
                  label="Contexte"
                  name={`comp_ctx_${index}`}
                  type="select"
                  value={c.evaluation_context}
                  onChange={(e) =>
                    updateDraftComponent(index, { evaluation_context: e.target.value })
                  }
                  options={EVALUATION_CONTEXT_OPTIONS}
                />
                <FormField
                  label="Poids (%)"
                  name={`comp_weight_${index}`}
                  type="number"
                  value={c.weight}
                  onChange={(e) => updateDraftComponent(index, { weight: e.target.value })}
                  error={fieldErrors[`comp_weight_${index}`]}
                  step="0.01"
                  min="0.01"
                  max="100"
                />
                <FormField
                  label="Ordre"
                  name={`comp_seq_${index}`}
                  type="number"
                  value={c.sequence}
                  onChange={(e) => updateDraftComponent(index, { sequence: e.target.value })}
                  min="1"
                />
                <div className="flex flex-wrap items-center gap-3 sm:col-span-2 lg:col-span-3">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={Boolean(c.is_required)}
                      onChange={(e) =>
                        updateDraftComponent(index, { is_required: e.target.checked })
                      }
                    />
                    Composante obligatoire
                  </label>
                  {draftComponents.length > 1 && (
                    <button
                      type="button"
                      className="btn-ghost text-sm text-brique"
                      onClick={() => removeDraftComponent(index)}
                    >
                      Retirer
                    </button>
                  )}
                </div>
              </div>
            ))}
            <p
              className={`text-sm font-medium ${weightsOk ? 'text-vert' : 'text-brique'}`}
              role="status"
            >
              Total des poids : {formatWeight(weightsTotal)}
              {weightsOk ? ' — configuration valide' : ' — doit égaler 100 %'}
            </p>
            {fieldErrors.weights && (
              <p className="text-sm text-brique" role="alert">
                {fieldErrors.weights}
              </p>
            )}
          </div>

          <div className="rounded-lg bg-craie/50 p-3 text-sm" aria-live="polite">
            <p className="font-medium">Aperçu (informatif — aucun calcul)</p>
            <dl className="mt-2 grid gap-1 sm:grid-cols-2">
              <div>
                <dt className="text-texte-secondaire">Ruleset</dt>
                <dd>
                  {form.name || '—'} ({form.code || '—'})
                </dd>
              </div>
              <div>
                <dt className="text-texte-secondaire">Statut</dt>
                <dd>{rulesetStatusLabel(RULESET_STATUS.DRAFT)}</dd>
              </div>
              <div>
                <dt className="text-texte-secondaire">Échelle</dt>
                <dd>{formatScaleMax(form.scale_max)}</dd>
              </div>
              <div>
                <dt className="text-texte-secondaire">Arrondi</dt>
                <dd>
                  {form.rounding_precision} déc. · {form.rounding_mode}
                </dd>
              </div>
            </dl>
            <ul className="mt-2 list-disc pl-5">
              {draftComponents.map((c, i) => (
                <li key={`preview-${i}`}>
                  {c.label || c.code || `Composante ${i + 1}`} — {formatWeight(c.weight)}
                </li>
              ))}
            </ul>
          </div>
        </form>
      </Modal>
    </div>
  );
}
