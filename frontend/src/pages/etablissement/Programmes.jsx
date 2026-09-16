import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { GraduationCap } from 'lucide-react';
import { configApi } from '../../services/api/config';
import Table from '../../components/Table';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import PageHeader from '../../components/PageHeader';
import Badge from '../../components/Badge';
import ConfirmDialog from '../../components/ConfirmDialog';
import StructureAcademiqueNav from '../../components/StructureAcademiqueNav';
import { useToast } from '../../components/Toast';
import {
  ACTIVE_FILTER_OPTIONS,
  PERIOD_TYPE_OPTIONS,
  PROGRAM_TYPE_OPTIONS,
  apiErrorMessage,
  asList,
  isGeneralProgram,
  periodTypeLabel,
  programTypeLabel,
} from '../../utils/academicLabels';

const EMPTY_FORM = {
  code: '',
  name: '',
  description: '',
  program_type: 'general',
  period_type_default: 'trimestre',
};

export default function Programmes() {
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;
  const navigate = useNavigate();

  const [programs, setPrograms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [confirmTarget, setConfirmTarget] = useState(null);
  const [deactivating, setDeactivating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const params = {};
      if (search.trim()) params.search = search.trim();
      if (activeFilter === 'true' || activeFilter === 'false') {
        params.is_active = activeFilter;
      }
      const data = await configApi.listPrograms(params);
      setPrograms(asList(data));
    } catch (err) {
      const msg = apiErrorMessage(err, 'Impossible de charger les programmes.');
      setLoadError(msg);
      toastRef.current.error(msg);
    } finally {
      setLoading(false);
    }
  }, [search, activeFilter]);

  useEffect(() => {
    const t = setTimeout(load, search ? 250 : 0);
    return () => clearTimeout(t);
  }, [load, search]);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setFieldErrors({});
    setModalOpen(true);
  };

  const openEdit = (program) => {
    setEditing(program);
    setForm({
      code: program.code || '',
      name: program.name || '',
      description: program.description || '',
      program_type: program.program_type || 'general',
      period_type_default: program.period_type_default || 'trimestre',
    });
    setFieldErrors({});
    setModalOpen(true);
  };

  const validate = () => {
    const errors = {};
    if (!form.code.trim()) errors.code = 'Le code est obligatoire.';
    if (!form.name.trim()) errors.name = 'Le nom est obligatoire.';
    if (!form.program_type) errors.program_type = 'Le type est obligatoire.';
    if (!form.period_type_default) {
      errors.period_type_default = 'Le type de période par défaut est obligatoire.';
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setSaving(true);
    try {
      const payload = {
        code: form.code.trim().toUpperCase(),
        name: form.name.trim(),
        description: form.description.trim() || null,
        program_type: form.program_type,
        period_type_default: form.period_type_default,
      };
      if (editing) {
        await configApi.updateProgram(editing.id, payload);
        toast.success('Programme mis à jour');
      } else {
        await configApi.createProgram(payload);
        toast.success('Programme créé');
      }
      setModalOpen(false);
      load();
    } catch (err) {
      toast.error(apiErrorMessage(err, "Erreur lors de l'enregistrement"));
    } finally {
      setSaving(false);
    }
  };

  const handleDeactivate = async () => {
    if (!confirmTarget) return;
    setDeactivating(true);
    try {
      await configApi.deactivateProgram(confirmTarget.id);
      toast.success(`Programme « ${confirmTarget.name} » désactivé`);
      setConfirmTarget(null);
      load();
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Impossible de désactiver ce programme'));
    } finally {
      setDeactivating(false);
    }
  };

  const columns = useMemo(
    () => [
      {
        key: 'code',
        header: 'Code',
        render: (r) => (
          <div className="flex items-center gap-2">
            <span className="font-medium tabular-nums">{r.code}</span>
            {isGeneralProgram(r) && (
              <Badge variant="info" className="!normal-case">
                Historique
              </Badge>
            )}
          </div>
        ),
      },
      {
        key: 'name',
        header: 'Nom',
        render: (r) => (
          <div>
            <p className="font-medium text-encre">{r.name}</p>
            {r.description && (
              <p className="mt-0.5 max-w-xs truncate text-xs text-texte-secondaire">
                {r.description}
              </p>
            )}
          </div>
        ),
      },
      {
        key: 'program_type',
        header: 'Type',
        render: (r) => programTypeLabel(r.program_type),
      },
      {
        key: 'period_type_default',
        header: 'Périodes (défaut)',
        render: (r) => periodTypeLabel(r.period_type_default),
      },
      {
        key: 'counts',
        header: 'Structure',
        render: (r) => (
          <span className="text-texte-secondaire">
            {typeof r.levels_count === 'number' ? `${r.levels_count} niv.` : '—'}
            {' · '}
            {typeof r.classes_count === 'number' ? `${r.classes_count} cl.` : '—'}
          </span>
        ),
      },
      {
        key: 'status',
        header: 'Statut',
        render: (r) =>
          r.is_active ? (
            <Badge variant="success">Actif</Badge>
          ) : (
            <Badge variant="neutral">Inactif</Badge>
          ),
      },
      {
        key: 'actions',
        header: '',
        align: 'right',
        render: (r) => (
          <div className="flex justify-end gap-3" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className="text-sm font-medium text-or-cachet hover:underline"
              onClick={() => openEdit(r)}
            >
              Modifier
            </button>
            {r.is_active && !isGeneralProgram(r) && (
              <button
                type="button"
                className="text-sm font-medium text-brique hover:underline"
                onClick={() => setConfirmTarget(r)}
              >
                Désactiver
              </button>
            )}
          </div>
        ),
      },
    ],
    []
  );

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Structure académique"
        title="Programmes / Filières"
        subtitle="Organisez les parcours de l’établissement : général, technique, professionnel…"
        actions={
          <button type="button" className="btn-primary" onClick={openCreate}>
            + Nouveau programme
          </button>
        }
      />

      <StructureAcademiqueNav />

      {loadError && !loading && programs.length === 0 ? (
        <div
          role="alert"
          className="rounded-card border border-brique/30 bg-brique-clair px-4 py-6 text-center"
        >
          <p className="text-sm text-brique">{loadError}</p>
          <button type="button" className="btn-secondary mt-4" onClick={load}>
            Réessayer
          </button>
        </div>
      ) : (
        <Table
          columns={columns}
          data={programs}
          loading={loading}
          searchable
          searchPlaceholder="Rechercher un programme…"
          onSearch={setSearch}
          onRowClick={(r) => navigate(`/etablissement/programmes/${r.id}`)}
          filters={
            <select
              className="input w-auto"
              value={activeFilter}
              onChange={(e) => setActiveFilter(e.target.value)}
              aria-label="Filtrer par statut"
            >
              {ACTIVE_FILTER_OPTIONS.map((o) => (
                <option key={o.value || 'all'} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          }
          emptyIcon={GraduationCap}
          emptyMessage="Aucun programme pour cette école. Créez le premier (ex. Technique, Professionnel) — le programme GENERAL historique est créé automatiquement."
        />
      )}

      <Modal
        isOpen={modalOpen}
        onClose={() => !saving && setModalOpen(false)}
        title={editing ? 'Modifier le programme' : 'Nouveau programme'}
        size="lg"
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setModalOpen(false)}
              disabled={saving}
            >
              Annuler
            </button>
            <button type="submit" form="program-form" className="btn-primary" disabled={saving}>
              {saving ? 'Enregistrement…' : editing ? 'Enregistrer' : 'Créer'}
            </button>
          </>
        }
      >
        <form id="program-form" onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
          <FormField
            label="Code"
            name="code"
            value={form.code}
            onChange={(e) => setForm({ ...form, code: e.target.value })}
            required
            disabled={editing && isGeneralProgram(editing)}
            error={fieldErrors.code}
            helpText={
              editing && isGeneralProgram(editing)
                ? 'Le code GENERAL (compatibilité historique) ne peut pas être modifié.'
                : 'Ex. TECH, PRO — unique dans l’école.'
            }
            placeholder="TECH"
          />
          <FormField
            label="Nom"
            name="name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
            error={fieldErrors.name}
            placeholder="Enseignement technique"
          />
          <FormField
            label="Type"
            name="program_type"
            type="select"
            value={form.program_type}
            onChange={(e) => setForm({ ...form, program_type: e.target.value })}
            required
            options={PROGRAM_TYPE_OPTIONS}
            error={fieldErrors.program_type}
          />
          <FormField
            label="Type de période par défaut"
            name="period_type_default"
            type="select"
            value={form.period_type_default}
            onChange={(e) => setForm({ ...form, period_type_default: e.target.value })}
            required
            options={PERIOD_TYPE_OPTIONS}
            error={fieldErrors.period_type_default}
            helpText="Suggestion UX pour les nouvelles périodes — n’impose pas le calcul des notes."
          />
          <div className="sm:col-span-2">
            <FormField
              label="Description"
              name="description"
              type="textarea"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={3}
              placeholder="Optionnel"
            />
          </div>
          {editing && (
            <p className="sm:col-span-2 text-xs text-texte-secondaire">
              <Link
                to={`/etablissement/programmes/${editing.id}`}
                className="text-or-cachet hover:underline"
              >
                Ouvrir la fiche détaillée
              </Link>
            </p>
          )}
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={Boolean(confirmTarget)}
        onClose={() => !deactivating && setConfirmTarget(null)}
        onConfirm={handleDeactivate}
        confirming={deactivating}
        danger
        title="Désactiver le programme ?"
        confirmLabel="Désactiver"
        message={
          confirmTarget
            ? `Le programme « ${confirmTarget.name} » (${confirmTarget.code}) sera désactivé. Les données liées restent disponibles, mais le programme ne pourra plus être utilisé pour de nouvelles structures.`
            : ''
        }
      />
    </div>
  );
}
