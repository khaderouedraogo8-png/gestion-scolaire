import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Plus } from 'lucide-react';
import { gradingApi } from '../../services/api/grading';
import { configApi } from '../../services/api/config';
import { notesApi } from '../../services/api/notes';
import DetailHeader from '../../components/DetailHeader';
import Breadcrumb from '../../components/Breadcrumb';
import Badge from '../../components/Badge';
import FormField from '../../components/FormField';
import Modal from '../../components/Modal';
import ConfirmDialog from '../../components/ConfirmDialog';
import { useToast } from '../../components/Toast';
import { useAuth } from '../../hooks/useAuth';
import { apiErrorMessage, asList } from '../../utils/academicLabels';
import {
  ENGINE_MISSING_POLICY_INFO,
  EVALUATION_CONTEXT_OPTIONS,
  ROUNDING_MODE_OPTIONS,
  RULESET_STATUS,
  evaluationContextLabel,
  formatScaleMax,
  formatWeight,
  roundingModeLabel,
  rulesetStatusBadgeVariant,
  rulesetStatusLabel,
  sumWeights,
  weightsAreValid,
} from '../../utils/gradingLabels';

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

/** Affiche missing comme — jamais comme 0. */
export function displayGradeValue(value) {
  if (value === null || value === undefined || value === '') return '—';
  return String(value);
}

export default function GradingRulesetDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;
  const { hasAnyRole } = useAuth();
  const canManage = hasAnyRole(['administrateur', 'directeur', 'super_admin']);

  const [ruleset, setRuleset] = useState(null);
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [unauthorized, setUnauthorized] = useState(false);

  const [annees, setAnnees] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [niveaux, setNiveaux] = useState([]);
  const [matieres, setMatieres] = useState([]);
  const [evalTypes, setEvalTypes] = useState([]);

  const [metaForm, setMetaForm] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});

  const [compModal, setCompModal] = useState(false);
  const [editingComp, setEditingComp] = useState(null);
  const [compForm, setCompForm] = useState(EMPTY_COMPONENT);
  const [compErrors, setCompErrors] = useState({});
  const [compSaving, setCompSaving] = useState(false);

  const [activateOpen, setActivateOpen] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [deleteCompTarget, setDeleteCompTarget] = useState(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [forkBusy, setForkBusy] = useState(false);

  const isDraft = ruleset?.status === RULESET_STATUS.DRAFT;
  const isActive = ruleset?.status === RULESET_STATUS.ACTIVE;
  const editable = Boolean(canManage && isDraft);

  const yearLabel = useMemo(() => {
    const a = asList(annees).find((x) => String(x.id) === String(ruleset?.academic_year_id));
    return a?.libelle || a?.label || ruleset?.academic_year_id || '—';
  }, [annees, ruleset]);

  const programLabel = useMemo(() => {
    if (!ruleset?.program_id) return 'Tous programmes';
    const p = asList(programs).find((x) => String(x.id) === String(ruleset.program_id));
    return p ? `${p.code} — ${p.name}` : ruleset.program_id;
  }, [programs, ruleset]);

  const levelLabel = useMemo(() => {
    if (!ruleset?.level_id) return 'Tous niveaux';
    const n = asList(niveaux).find((x) => String(x.id) === String(ruleset.level_id));
    return n?.libelle || n?.name || ruleset.level_id;
  }, [niveaux, ruleset]);

  const subjectLabel = useMemo(() => {
    if (!ruleset?.subject_id) return 'Toutes matières';
    const m = asList(matieres).find((x) => String(x.id) === String(ruleset.subject_id));
    return m?.libelle || m?.name || ruleset.subject_id;
  }, [matieres, ruleset]);

  const evalTypeOptions = useMemo(
    () =>
      extractItems(evalTypes).map((t) => ({
        value: t.id,
        label: `${t.label || t.code} (${t.code})`,
      })),
    [evalTypes]
  );

  const components = ruleset?.components || [];
  const weightsTotal = sumWeights(components);
  const weightsOk = weightsAreValid(components);

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

  const loadVersions = useCallback(async (code) => {
    if (!code) {
      setVersions([]);
      return;
    }
    try {
      const data = await gradingApi.listRulesets({ per_page: 100 });
      const all = extractItems(data).filter((r) => r.code === code);
      all.sort((a, b) => Number(b.version) - Number(a.version));
      setVersions(all);
    } catch {
      setVersions([]);
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    setUnauthorized(false);
    try {
      const data = await gradingApi.getRuleset(id);
      setRuleset(data);
      setMetaForm({
        name: data.name || '',
        description: data.description || '',
        academic_year_id: data.academic_year_id || '',
        program_id: data.program_id || '',
        level_id: data.level_id || '',
        subject_id: data.subject_id || '',
        scale_max: data.scale_max != null ? String(data.scale_max) : '20.00',
        rounding_mode: data.rounding_mode || 'half_up',
        rounding_precision: String(data.rounding_precision ?? 2),
      });
      setDirty(false);
      setFieldErrors({});
      await loadVersions(data.code);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 403) {
        setUnauthorized(true);
        setLoadError(apiErrorMessage(err, 'Accès non autorisé.'));
      } else if (status === 404) {
        setLoadError(apiErrorMessage(err, 'Ruleset introuvable.'));
      } else {
        setLoadError(apiErrorMessage(err, 'Impossible de charger le ruleset.'));
      }
      setRuleset(null);
    } finally {
      setLoading(false);
    }
  }, [id, loadVersions]);

  useEffect(() => {
    loadRefs();
  }, [loadRefs]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!dirty) return undefined;
    const onBeforeUnload = (e) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', onBeforeUnload);
    return () => window.removeEventListener('beforeunload', onBeforeUnload);
  }, [dirty]);

  const setMeta = (name, value) => {
    setMetaForm((prev) => ({ ...prev, [name]: value }));
    setDirty(true);
  };

  const saveMeta = async (e) => {
    e.preventDefault();
    if (!editable || !metaForm) return;
    const errors = {};
    if (!metaForm.name.trim()) errors.name = 'Le nom est obligatoire.';
    if (!metaForm.academic_year_id) errors.academic_year_id = "L'année scolaire est obligatoire.";
    if (!metaForm.scale_max || Number(metaForm.scale_max) <= 0) {
      errors.scale_max = "L'échelle maximale doit être > 0.";
    }
    setFieldErrors(errors);
    if (Object.keys(errors).length) return;

    setSaving(true);
    try {
      const updated = await gradingApi.updateRuleset(id, {
        name: metaForm.name.trim(),
        description: metaForm.description.trim() || null,
        academic_year_id: metaForm.academic_year_id,
        program_id: metaForm.program_id || null,
        level_id: metaForm.level_id || null,
        subject_id: metaForm.subject_id || null,
        scale_max: metaForm.scale_max,
        rounding_mode: metaForm.rounding_mode,
        rounding_precision: Number(metaForm.rounding_precision),
      });
      setRuleset(updated);
      setDirty(false);
      toast.success('Ruleset enregistré.');
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Enregistrement impossible.'));
    } finally {
      setSaving(false);
    }
  };

  const openAddComponent = () => {
    setEditingComp(null);
    setCompForm({
      ...EMPTY_COMPONENT,
      sequence: String((components?.length || 0) + 1),
    });
    setCompErrors({});
    setCompModal(true);
  };

  const openEditComponent = (comp) => {
    setEditingComp(comp);
    setCompForm({
      code: comp.code || '',
      label: comp.label || '',
      evaluation_type_id: comp.evaluation_type_id || '',
      evaluation_context: comp.evaluation_context || 'normal',
      weight: comp.weight != null ? String(comp.weight) : '',
      sequence: String(comp.sequence ?? 1),
      is_required: Boolean(comp.is_required),
    });
    setCompErrors({});
    setCompModal(true);
  };

  const validateComp = () => {
    const errors = {};
    if (!compForm.code.trim()) errors.code = 'Code obligatoire.';
    if (!compForm.label.trim()) errors.label = 'Libellé obligatoire.';
    if (!compForm.evaluation_type_id) errors.evaluation_type_id = 'Type obligatoire.';
    const w = Number(compForm.weight);
    if (!Number.isFinite(w) || w <= 0 || w > 100) {
      errors.weight = 'Poids invalide (0 < poids ≤ 100).';
    }
    setCompErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const saveComponent = async (e) => {
    e.preventDefault();
    if (!editable) return;
    if (!validateComp()) return;
    setCompSaving(true);
    const payload = {
      code: compForm.code.trim().toUpperCase(),
      label: compForm.label.trim(),
      evaluation_type_id: compForm.evaluation_type_id,
      evaluation_context: compForm.evaluation_context || 'normal',
      weight: String(compForm.weight),
      sequence: Number(compForm.sequence) || 1,
      is_required: Boolean(compForm.is_required),
    };
    try {
      if (editingComp) {
        await gradingApi.updateComponent(id, editingComp.id, payload);
        toast.success('Composante mise à jour.');
      } else {
        await gradingApi.addComponent(id, payload);
        toast.success('Composante ajoutée.');
      }
      setCompModal(false);
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Impossible d’enregistrer la composante.'));
    } finally {
      setCompSaving(false);
    }
  };

  const confirmDeleteComponent = async () => {
    if (!deleteCompTarget) return;
    setActionBusy(true);
    try {
      await gradingApi.deleteComponent(id, deleteCompTarget.id);
      toast.success('Composante supprimée.');
      setDeleteCompTarget(null);
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Suppression impossible.'));
    } finally {
      setActionBusy(false);
    }
  };

  const confirmActivate = async () => {
    setActionBusy(true);
    try {
      const updated = await gradingApi.activateRuleset(id);
      setRuleset(updated);
      setActivateOpen(false);
      toast.success('Version activée pour ce contexte.');
      await loadVersions(updated.code);
    } catch (err) {
      toast.error(apiErrorMessage(err, "Impossible d'activer ce ruleset."));
    } finally {
      setActionBusy(false);
    }
  };

  const confirmArchive = async () => {
    setActionBusy(true);
    try {
      const updated = await gradingApi.archiveRuleset(id);
      setRuleset(updated);
      setArchiveOpen(false);
      toast.success('Ruleset archivé.');
      await loadVersions(updated.code);
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Archivage impossible.'));
    } finally {
      setActionBusy(false);
    }
  };

  /** Nouvelle version DRAFT via POST create (même code) — workflow API Step 3. */
  const createNewVersion = async () => {
    if (!canManage || !ruleset) return;
    if (dirty) {
      toast.error('Enregistrez ou annulez vos modifications avant de créer une nouvelle version.');
      return;
    }
    setForkBusy(true);
    try {
      const payload = {
        code: ruleset.code,
        name: ruleset.name,
        description: ruleset.description,
        academic_year_id: ruleset.academic_year_id,
        program_id: ruleset.program_id,
        level_id: ruleset.level_id,
        subject_id: ruleset.subject_id,
        scale_max: ruleset.scale_max,
        rounding_mode: ruleset.rounding_mode,
        rounding_precision: ruleset.rounding_precision,
        components: (ruleset.components || []).map((c, i) => ({
          code: c.code,
          label: c.label,
          evaluation_type_id: c.evaluation_type_id,
          evaluation_context: c.evaluation_context || 'normal',
          weight: String(c.weight),
          sequence: c.sequence ?? i + 1,
          is_required: Boolean(c.is_required),
        })),
      };
      const created = await gradingApi.createRuleset(payload);
      toast.success(`Brouillon v${created.version} créé.`);
      navigate(`/config/regles-notation/${created.id}`);
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Création de version impossible.'));
    } finally {
      setForkBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 p-8 text-sm text-texte-secondaire">
        <div className="loading-ring h-5 w-5" />
        Chargement du ruleset…
      </div>
    );
  }

  if (unauthorized) {
    return (
      <div className="space-y-4 p-6 text-center" role="alert">
        <p className="text-lg font-semibold text-encre">Accès non autorisé</p>
        <p className="page-subtitle">{loadError}</p>
        <Link to="/config/regles-notation" className="btn-secondary inline-flex">
          Retour à la liste
        </Link>
      </div>
    );
  }

  if (loadError || !ruleset || !metaForm) {
    return (
      <div className="space-y-4 p-6" role="alert">
        <p className="text-sm text-brique">{loadError || 'Ruleset introuvable.'}</p>
        <Link to="/config/regles-notation" className="btn-secondary inline-flex">
          Retour à la liste
        </Link>
      </div>
    );
  }

  const yearOptions = asList(annees).map((a) => ({
    value: a.id,
    label: a.libelle || a.label || String(a.id),
  }));
  const programOptions = asList(programs)
    .filter((p) => p.is_active !== false)
    .map((p) => ({ value: p.id, label: `${p.code} — ${p.name}` }));
  const niveauOptions = asList(niveaux).map((n) => ({
    value: n.id,
    label: n.libelle || n.name || String(n.id),
  }));
  const matiereOptions = asList(matieres).map((m) => ({
    value: m.id,
    label: m.libelle || m.name || m.code || String(m.id),
  }));

  return (
    <div className="space-y-6">
      <DetailHeader
        breadcrumb={
          <Breadcrumb
            items={[
              { label: 'Configuration', to: '/config/etablissement' },
              { label: 'Règles de notation', to: '/config/regles-notation' },
              { label: ruleset.code },
            ]}
          />
        }
        eyebrow="Ruleset de notation"
        title={ruleset.name}
        subtitle={
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={rulesetStatusBadgeVariant(ruleset.status)}>
              {rulesetStatusLabel(ruleset.status)}
            </Badge>
            <span className="text-sm text-texte-secondaire">
              {ruleset.code} · v{ruleset.version}
            </span>
            {isActive && (
              <span className="text-sm font-medium text-vert">Version active pour ce contexte</span>
            )}
          </div>
        }
        actions={
          <div className="flex flex-wrap gap-2">
            <Link to="/config/regles-notation" className="btn-secondary inline-flex items-center gap-1">
              <ArrowLeft className="h-4 w-4" aria-hidden />
              Liste
            </Link>
            {canManage && isDraft && (
              <button type="button" className="btn-primary" onClick={() => setActivateOpen(true)}>
                Activer
              </button>
            )}
            {canManage && (isDraft || isActive) && (
              <button type="button" className="btn-secondary" onClick={() => setArchiveOpen(true)}>
                Archiver
              </button>
            )}
            {canManage && !isDraft && (
              <button
                type="button"
                className="btn-primary"
                disabled={forkBusy}
                onClick={createNewVersion}
              >
                {forkBusy ? 'Création…' : 'Nouvelle version (brouillon)'}
              </button>
            )}
          </div>
        }
      />

      {!editable && (
        <p className="rounded-card border border-bordure bg-craie/40 px-4 py-3 text-sm text-texte-secondaire">
          {isActive
            ? 'Cette version ACTIVE est immuable. Créez une nouvelle version brouillon pour modifier les règles.'
            : 'Cette version archivée est en lecture seule.'}
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <form onSubmit={saveMeta} className="space-y-4 rounded-card border border-bordure bg-blanc p-4 lg:col-span-2">
          <h2 className="font-medium">Configuration</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField
              label="Nom"
              name="name"
              required
              value={metaForm.name}
              onChange={(e) => setMeta('name', e.target.value)}
              error={fieldErrors.name}
              disabled={!editable}
            />
            <FormField
              label="Année scolaire"
              name="academic_year_id"
              type="select"
              required
              value={metaForm.academic_year_id}
              onChange={(e) => setMeta('academic_year_id', e.target.value)}
              options={yearOptions}
              error={fieldErrors.academic_year_id}
              disabled={!editable}
            />
            <FormField
              label="Programme"
              name="program_id"
              type="select"
              value={metaForm.program_id}
              onChange={(e) => setMeta('program_id', e.target.value)}
              options={programOptions}
              disabled={!editable}
            />
            <FormField
              label="Niveau"
              name="level_id"
              type="select"
              value={metaForm.level_id}
              onChange={(e) => setMeta('level_id', e.target.value)}
              options={niveauOptions}
              disabled={!editable}
            />
            <FormField
              label="Matière"
              name="subject_id"
              type="select"
              value={metaForm.subject_id}
              onChange={(e) => setMeta('subject_id', e.target.value)}
              options={matiereOptions}
              disabled={!editable}
            />
            <FormField
              label="Échelle maximale"
              name="scale_max"
              type="number"
              required
              value={metaForm.scale_max}
              onChange={(e) => setMeta('scale_max', e.target.value)}
              error={fieldErrors.scale_max}
              disabled={!editable}
              step="0.01"
              min="0.01"
              helpText={formatScaleMax(metaForm.scale_max)}
            />
            <FormField
              label="Mode d'arrondi"
              name="rounding_mode"
              type="select"
              value={metaForm.rounding_mode}
              onChange={(e) => setMeta('rounding_mode', e.target.value)}
              options={ROUNDING_MODE_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
              disabled={!editable}
            />
            <FormField
              label="Précision d'arrondi"
              name="rounding_precision"
              type="number"
              value={metaForm.rounding_precision}
              onChange={(e) => setMeta('rounding_precision', e.target.value)}
              disabled={!editable}
              min="0"
              max="6"
            />
          </div>
          <FormField
            label="Description"
            name="description"
            type="textarea"
            value={metaForm.description}
            onChange={(e) => setMeta('description', e.target.value)}
            disabled={!editable}
            rows={2}
          />
          {editable && (
            <div className="flex justify-end gap-2">
              <button
                type="button"
                className="btn-secondary"
                disabled={saving || !dirty}
                onClick={() => load()}
              >
                Annuler
              </button>
              <button type="submit" className="btn-primary" disabled={saving || !dirty}>
                {saving ? 'Enregistrement…' : 'Enregistrer'}
              </button>
            </div>
          )}
        </form>

        <aside className="space-y-4">
          <div className="rounded-card border border-bordure bg-blanc p-4 text-sm">
            <h2 className="mb-2 font-medium">Aperçu (informatif)</h2>
            <dl className="space-y-2">
              <div>
                <dt className="text-texte-secondaire">Programme</dt>
                <dd>{programLabel}</dd>
              </div>
              <div>
                <dt className="text-texte-secondaire">Niveau</dt>
                <dd>{levelLabel}</dd>
              </div>
              <div>
                <dt className="text-texte-secondaire">Année</dt>
                <dd>{yearLabel}</dd>
              </div>
              <div>
                <dt className="text-texte-secondaire">Matière</dt>
                <dd>{subjectLabel}</dd>
              </div>
              <div>
                <dt className="text-texte-secondaire">Échelle</dt>
                <dd>{formatScaleMax(ruleset.scale_max)}</dd>
              </div>
              <div>
                <dt className="text-texte-secondaire">Arrondi</dt>
                <dd>
                  {ruleset.rounding_precision} déc. · {roundingModeLabel(ruleset.rounding_mode)}
                </dd>
              </div>
              <div>
                <dt className="text-texte-secondaire">Évaluations</dt>
                <dd>
                  <ul className="mt-1 list-disc pl-4">
                    {components.map((c) => (
                      <li key={c.id}>
                        {c.label} — {formatWeight(c.weight)}
                      </li>
                    ))}
                  </ul>
                </dd>
              </div>
            </dl>
            <p className="mt-3 text-xs text-texte-secondaire">
              Mis à jour : {formatDate(ruleset.updated_at)} · Créé : {formatDate(ruleset.created_at)}
            </p>
          </div>

          <div className="rounded-card border border-bordure bg-craie/40 p-4 text-sm">
            <h2 className="mb-2 font-medium">Notes manquantes (moteur)</h2>
            <ul className="space-y-2">
              {ENGINE_MISSING_POLICY_INFO.map((info) => (
                <li key={info.id}>
                  <strong>{info.name}</strong>
                  <span className="text-texte-secondaire"> — {info.effect}</span>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-texte-secondaire">
              Exemple d&apos;affichage : note manquante = {displayGradeValue(null)} ; zéro explicite ={' '}
              {displayGradeValue(0)}.
            </p>
          </div>
        </aside>
      </div>

      <section className="space-y-3 rounded-card border border-bordure bg-blanc p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="font-medium">Composantes d&apos;évaluation</h2>
            <p className="text-xs text-texte-secondaire">
              Poids = part de la moyenne matière (≠ coefficient matière).
            </p>
          </div>
          {editable && (
            <button type="button" className="btn-primary" onClick={openAddComponent}>
              <Plus className="mr-1 inline h-4 w-4" aria-hidden />
              Ajouter
            </button>
          )}
        </div>

        <p
          className={`text-sm font-medium ${weightsOk ? 'text-vert' : 'text-brique'}`}
          role="status"
        >
          Total des poids : {formatWeight(weightsTotal)}
          {components.length === 0
            ? ' — aucune composante'
            : weightsOk
              ? ' — configuration valide'
              : ' — doit égaler 100 % pour l’activation'}
        </p>

        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-bordure text-left text-texte-secondaire">
                <th className="px-2 py-2">Ordre</th>
                <th className="px-2 py-2">Code</th>
                <th className="px-2 py-2">Libellé</th>
                <th className="px-2 py-2">Type</th>
                <th className="px-2 py-2">Contexte</th>
                <th className="px-2 py-2 text-right">Poids</th>
                <th className="px-2 py-2">Obligatoire</th>
                {editable && <th className="px-2 py-2">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {components.length === 0 ? (
                <tr>
                  <td colSpan={editable ? 8 : 7} className="px-2 py-6 text-texte-secondaire">
                    Aucune composante.
                  </td>
                </tr>
              ) : (
                components.map((c) => (
                  <tr key={c.id} className="border-b border-bordure/60">
                    <td className="px-2 py-2 tabular-nums">{c.sequence}</td>
                    <td className="px-2 py-2">{c.code}</td>
                    <td className="px-2 py-2">{c.label}</td>
                    <td className="px-2 py-2">
                      {c.evaluation_type?.label || c.evaluation_type?.code || c.evaluation_type_id}
                    </td>
                    <td className="px-2 py-2">{evaluationContextLabel(c.evaluation_context)}</td>
                    <td className="px-2 py-2 text-right tabular-nums">{formatWeight(c.weight)}</td>
                    <td className="px-2 py-2">{c.is_required ? 'Oui' : 'Non'}</td>
                    {editable && (
                      <td className="px-2 py-2">
                        <div className="flex gap-2">
                          <button
                            type="button"
                            className="btn-ghost text-sm"
                            onClick={() => openEditComponent(c)}
                          >
                            Modifier
                          </button>
                          <button
                            type="button"
                            className="btn-ghost text-sm text-brique"
                            onClick={() => setDeleteCompTarget(c)}
                          >
                            Supprimer
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="space-y-3 rounded-card border border-bordure bg-blanc p-4">
        <h2 className="font-medium">Historique des versions</h2>
        <p className="text-xs text-texte-secondaire">
          Versions partageant le code <strong>{ruleset.code}</strong> (lecture seule pour les
          versions non brouillon).
        </p>
        {versions.length === 0 ? (
          <p className="text-sm text-texte-secondaire">Aucune autre version listée.</p>
        ) : (
          <ul className="divide-y divide-bordure/60">
            {versions.map((v) => (
              <li key={v.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium tabular-nums">v{v.version}</span>
                  <Badge variant={rulesetStatusBadgeVariant(v.status)}>
                    {rulesetStatusLabel(v.status)}
                  </Badge>
                  <span className="text-texte-secondaire">{formatDate(v.created_at)}</span>
                  {String(v.id) === String(ruleset.id) && (
                    <span className="text-xs text-or-cachet">version courante</span>
                  )}
                </div>
                {String(v.id) !== String(ruleset.id) && (
                  <Link to={`/config/regles-notation/${v.id}`} className="btn-ghost text-sm">
                    Consulter
                  </Link>
                )}
              </li>
            ))}
          </ul>
        )}

        {versions.length >= 2 && (
          <div className="mt-4 rounded-lg bg-craie/50 p-3 text-sm">
            <h3 className="font-medium">Comparaison simple (informative)</h3>
            <div className="mt-2 grid gap-3 sm:grid-cols-2">
              {versions.slice(0, 2).map((v) => (
                <div key={`cmp-${v.id}`}>
                  <p className="font-medium">
                    v{v.version} — {rulesetStatusLabel(v.status)}
                  </p>
                  {String(v.id) === String(ruleset.id) ? (
                    <ul className="list-disc pl-4">
                      {components.map((c) => (
                        <li key={c.id}>
                          {c.label} {formatWeight(c.weight)}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-texte-secondaire">
                      Ouvrir la version pour voir le détail des composantes.
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      <Modal
        isOpen={compModal}
        onClose={() => !compSaving && setCompModal(false)}
        title={editingComp ? 'Modifier la composante' : 'Nouvelle composante'}
        size="lg"
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              disabled={compSaving}
              onClick={() => setCompModal(false)}
            >
              Annuler
            </button>
            <button
              type="submit"
              form="grading-component-form"
              className="btn-primary"
              disabled={compSaving}
            >
              {compSaving ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          </>
        }
      >
        <form id="grading-component-form" className="grid gap-3 sm:grid-cols-2" onSubmit={saveComponent}>
          <FormField
            label="Code"
            name="comp_code"
            required
            value={compForm.code}
            onChange={(e) => setCompForm({ ...compForm, code: e.target.value })}
            error={compErrors.code}
          />
          <FormField
            label="Libellé"
            name="comp_label"
            required
            value={compForm.label}
            onChange={(e) => setCompForm({ ...compForm, label: e.target.value })}
            error={compErrors.label}
          />
          <FormField
            label="Type d'évaluation"
            name="comp_type"
            type="select"
            required
            value={compForm.evaluation_type_id}
            onChange={(e) => setCompForm({ ...compForm, evaluation_type_id: e.target.value })}
            options={evalTypeOptions}
            error={compErrors.evaluation_type_id}
          />
          <FormField
            label="Contexte"
            name="comp_ctx"
            type="select"
            value={compForm.evaluation_context}
            onChange={(e) => setCompForm({ ...compForm, evaluation_context: e.target.value })}
            options={EVALUATION_CONTEXT_OPTIONS}
          />
          <FormField
            label="Poids (%)"
            name="comp_weight"
            type="number"
            required
            value={compForm.weight}
            onChange={(e) => setCompForm({ ...compForm, weight: e.target.value })}
            error={compErrors.weight}
            step="0.01"
            min="0.01"
            max="100"
          />
          <FormField
            label="Ordre"
            name="comp_seq"
            type="number"
            value={compForm.sequence}
            onChange={(e) => setCompForm({ ...compForm, sequence: e.target.value })}
            min="1"
          />
          <label className="flex items-center gap-2 text-sm sm:col-span-2">
            <input
              type="checkbox"
              checked={Boolean(compForm.is_required)}
              onChange={(e) => setCompForm({ ...compForm, is_required: e.target.checked })}
            />
            Composante obligatoire
          </label>
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={activateOpen}
        onClose={() => setActivateOpen(false)}
        onConfirm={confirmActivate}
        title="Activer cette version ?"
        message="Cette version deviendra la version active pour son contexte académique. L’ancienne version active du même code sera archivée."
        confirmLabel="Activer"
        confirming={actionBusy}
      />

      <ConfirmDialog
        isOpen={archiveOpen}
        onClose={() => setArchiveOpen(false)}
        onConfirm={confirmArchive}
        title="Archiver ce ruleset ?"
        message="Le ruleset ne sera plus utilisable pour de nouveaux calculs. Cette action est intentionnelle."
        confirmLabel="Archiver"
        confirming={actionBusy}
        danger
      />

      <ConfirmDialog
        isOpen={Boolean(deleteCompTarget)}
        onClose={() => setDeleteCompTarget(null)}
        onConfirm={confirmDeleteComponent}
        title="Supprimer la composante ?"
        message={
          deleteCompTarget
            ? `Supprimer « ${deleteCompTarget.label} » (${formatWeight(deleteCompTarget.weight)}) ?`
            : ''
        }
        confirmLabel="Supprimer"
        confirming={actionBusy}
        danger
      />
    </div>
  );
}
