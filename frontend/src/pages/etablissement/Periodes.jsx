import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Calendar } from 'lucide-react';
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
  PERIOD_TYPE_OPTIONS,
  apiErrorMessage,
  asList,
  periodTypeLabel,
} from '../../utils/academicLabels';

const EMPTY_FORM = {
  id_annee: '',
  id_program: '',
  sequence: '1',
  code: '',
  label: '',
  period_type: 'trimestre',
  date_debut: '',
  date_fin: '',
  is_active: true,
};

export default function Periodes() {
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;
  const [searchParams, setSearchParams] = useSearchParams();

  const [annees, setAnnees] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [anneeId, setAnneeId] = useState(searchParams.get('annee') || '');
  const [programId, setProgramId] = useState(searchParams.get('program') || '');
  const [periodes, setPeriodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [confirmTarget, setConfirmTarget] = useState(null);
  const [deactivating, setDeactivating] = useState(false);

  useEffect(() => {
    const init = async () => {
      try {
        const [ans, progs] = await Promise.all([
          configApi.listAnnees(),
          configApi.listPrograms({ is_active: true }),
        ]);
        const anneeList = asList(ans);
        const progList = asList(progs);
        setAnnees(anneeList);
        setPrograms(progList);
        setAnneeId((prev) => {
          if (prev) return prev;
          const active = anneeList.find((a) => a.est_active) || anneeList[0];
          return active ? String(active.id) : '';
        });
        setProgramId((prev) => {
          if (prev) return prev;
          return progList[0] ? String(progList[0].id) : '';
        });
      } catch (err) {
        toastRef.current.error(apiErrorMessage(err, 'Impossible de charger les filtres.'));
      }
    };
    init();
  }, []);

  useEffect(() => {
    const next = {};
    if (anneeId) next.annee = anneeId;
    if (programId) next.program = programId;
    setSearchParams(next, { replace: true });
  }, [anneeId, programId, setSearchParams]);

  const load = useCallback(async () => {
    if (!anneeId || !programId) {
      setPeriodes([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setLoadError(null);
    try {
      const data = await configApi.listPeriodes({
        id_annee: anneeId,
        id_program: programId,
      });
      setPeriodes(asList(data));
    } catch (err) {
      const msg = apiErrorMessage(err, 'Impossible de charger les périodes.');
      setLoadError(msg);
      toastRef.current.error(msg);
    } finally {
      setLoading(false);
    }
  }, [anneeId, programId]);

  useEffect(() => {
    load();
  }, [load]);

  const selectedProgram = useMemo(
    () => programs.find((p) => String(p.id) === String(programId)),
    [programs, programId]
  );

  const openCreate = () => {
    setEditing(null);
    const nextSeq =
      periodes.reduce((max, p) => Math.max(max, Number(p.sequence) || 0), 0) + 1;
    const pType = selectedProgram?.period_type_default || 'trimestre';
    setForm({
      ...EMPTY_FORM,
      id_annee: anneeId,
      id_program: programId,
      sequence: String(nextSeq),
      period_type: pType,
      code: '',
      label: '',
      is_active: true,
    });
    setFieldErrors({});
    setModalOpen(true);
  };

  const openEdit = (period) => {
    setEditing(period);
    setForm({
      id_annee: String(period.id_annee || anneeId),
      id_program: String(period.id_program || programId),
      sequence: String(period.sequence || 1),
      code: period.code || '',
      label: period.label || '',
      period_type: period.period_type || 'trimestre',
      date_debut: period.date_debut || '',
      date_fin: period.date_fin || '',
      is_active: period.is_active !== false,
    });
    setFieldErrors({});
    setModalOpen(true);
  };

  const validate = () => {
    const errors = {};
    if (!form.id_annee) errors.id_annee = 'Année scolaire obligatoire.';
    if (!form.id_program) errors.id_program = 'Programme obligatoire.';
    if (!form.sequence || Number(form.sequence) < 1) {
      errors.sequence = 'La séquence doit être un entier ≥ 1.';
    }
    if (!form.code.trim()) errors.code = 'Le code est obligatoire.';
    if (!form.label.trim()) errors.label = 'Le libellé est obligatoire.';
    if (!form.period_type) errors.period_type = 'Le type est obligatoire.';
    if (!form.date_debut) errors.date_debut = 'Date de début obligatoire.';
    if (!form.date_fin) errors.date_fin = 'Date de fin obligatoire.';
    if (form.date_debut && form.date_fin && form.date_debut > form.date_fin) {
      errors.date_fin = 'La date de fin doit être postérieure ou égale à la date de début.';
    }
    const dupSeq = periodes.some(
      (p) =>
        Number(p.sequence) === Number(form.sequence) &&
        (!editing || String(p.id) !== String(editing.id))
    );
    if (dupSeq) {
      errors.sequence = 'Une période avec cette séquence existe déjà pour ce programme.';
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
        id_annee: form.id_annee,
        id_program: form.id_program,
        sequence: Number(form.sequence),
        code: form.code.trim().toUpperCase(),
        label: form.label.trim(),
        period_type: form.period_type,
        date_debut: form.date_debut,
        date_fin: form.date_fin,
        is_active: Boolean(form.is_active),
      };
      if (editing) {
        await configApi.updatePeriode(editing.id, payload);
        toast.success('Période mise à jour');
      } else {
        await configApi.createPeriode(payload);
        toast.success('Période créée');
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
      await configApi.deactivatePeriode(confirmTarget.id);
      toast.success('Période désactivée');
      setConfirmTarget(null);
      load();
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Impossible de désactiver cette période'));
    } finally {
      setDeactivating(false);
    }
  };

  const columns = [
    {
      key: 'sequence',
      header: 'Séquence',
      render: (r) => <span className="tabular-nums font-medium">{r.sequence}</span>,
    },
    {
      key: 'label',
      header: 'Libellé',
      render: (r) => (
        <div>
          <p className="font-medium">{r.label}</p>
          <p className="text-xs text-texte-secondaire">{r.code}</p>
        </div>
      ),
    },
    {
      key: 'period_type',
      header: 'Type',
      render: (r) => periodTypeLabel(r.period_type),
    },
    { key: 'date_debut', header: 'Début' },
    { key: 'date_fin', header: 'Fin' },
    {
      key: 'status',
      header: 'Statut',
      render: (r) =>
        r.is_active !== false ? (
          <Badge variant="success">Active</Badge>
        ) : (
          <Badge variant="neutral">Inactive</Badge>
        ),
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (r) => (
        <div className="flex justify-end gap-3">
          <button
            type="button"
            className="text-sm font-medium text-or-cachet hover:underline"
            onClick={() => openEdit(r)}
          >
            Modifier
          </button>
          {r.is_active !== false && (
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
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Structure académique"
        title="Périodes académiques"
        subtitle="Trimestres, semestres, périodes personnalisées ou annuelles — sans limite artificielle à 3."
        actions={
          <button
            type="button"
            className="btn-primary"
            onClick={openCreate}
            disabled={!anneeId || !programId}
          >
            + Nouvelle période
          </button>
        }
      />

      <StructureAcademiqueNav />

      <div className="flex flex-col gap-3 rounded-card border border-bordure bg-blanc p-4 sm:flex-row sm:items-end">
        <div className="flex-1">
          <FormField
            label="Année scolaire"
            name="filter_annee"
            type="select"
            value={anneeId}
            onChange={(e) => setAnneeId(e.target.value)}
            options={annees.map((a) => ({
              value: String(a.id),
              label: `${a.libelle}${a.est_active ? ' (active)' : ''}`,
            }))}
            required
          />
        </div>
        <div className="flex-1">
          <FormField
            label="Programme"
            name="filter_program"
            type="select"
            value={programId}
            onChange={(e) => setProgramId(e.target.value)}
            options={programs.map((p) => ({
              value: String(p.id),
              label: `${p.name} (${p.code})`,
            }))}
            required
          />
        </div>
      </div>

      <p className="text-xs text-texte-secondaire">
        L’écran legacy{' '}
        <Link to="/config/trimestres" className="text-or-cachet hover:underline">
          Trimestres
        </Link>{' '}
        reste disponible et utilise les mêmes données — cette page est l’interface canonique.
      </p>

      {loadError && !loading && periodes.length === 0 ? (
        <div role="alert" className="rounded-card border border-brique/30 bg-brique-clair px-4 py-6 text-center">
          <p className="text-sm text-brique">{loadError}</p>
          <button type="button" className="btn-secondary mt-4" onClick={load}>
            Réessayer
          </button>
        </div>
      ) : (
        <Table
          columns={columns}
          data={periodes}
          loading={loading}
          emptyIcon={Calendar}
          emptyMessage={
            !anneeId || !programId
              ? 'Sélectionnez une année scolaire et un programme.'
              : 'Aucune période pour cette combinaison. Ajoutez un trimestre, un semestre ou une période personnalisée.'
          }
        />
      )}

      <Modal
        isOpen={modalOpen}
        onClose={() => !saving && setModalOpen(false)}
        title={editing ? 'Modifier la période' : 'Nouvelle période'}
        size="lg"
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
            <button type="submit" form="periode-form" className="btn-primary" disabled={saving}>
              {saving ? 'Enregistrement…' : editing ? 'Enregistrer' : 'Créer'}
            </button>
          </>
        }
      >
        <form id="periode-form" onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
          <FormField
            label="Année scolaire"
            name="id_annee"
            type="select"
            value={form.id_annee}
            onChange={(e) => setForm({ ...form, id_annee: e.target.value })}
            options={annees.map((a) => ({ value: String(a.id), label: a.libelle }))}
            required
            error={fieldErrors.id_annee}
          />
          <FormField
            label="Programme"
            name="id_program"
            type="select"
            value={form.id_program}
            onChange={(e) => setForm({ ...form, id_program: e.target.value })}
            options={programs.map((p) => ({
              value: String(p.id),
              label: `${p.name} (${p.code})`,
            }))}
            required
            error={fieldErrors.id_program}
          />
          <FormField
            label="Séquence"
            name="sequence"
            type="number"
            min="1"
            value={form.sequence}
            onChange={(e) => setForm({ ...form, sequence: e.target.value })}
            required
            error={fieldErrors.sequence}
            helpText="Ordre dans l’année (1, 2, 3… sans limite à 3)."
          />
          <FormField
            label="Type"
            name="period_type"
            type="select"
            value={form.period_type}
            onChange={(e) => setForm({ ...form, period_type: e.target.value })}
            options={PERIOD_TYPE_OPTIONS}
            required
            error={fieldErrors.period_type}
          />
          <FormField
            label="Code"
            name="code"
            value={form.code}
            onChange={(e) => setForm({ ...form, code: e.target.value })}
            required
            error={fieldErrors.code}
            placeholder="T1, S1, P4…"
          />
          <FormField
            label="Libellé"
            name="label"
            value={form.label}
            onChange={(e) => setForm({ ...form, label: e.target.value })}
            required
            error={fieldErrors.label}
            placeholder="Trimestre 1, Semestre 2…"
          />
          <FormField
            label="Date début"
            name="date_debut"
            type="date"
            value={form.date_debut}
            onChange={(e) => setForm({ ...form, date_debut: e.target.value })}
            required
            error={fieldErrors.date_debut}
          />
          <FormField
            label="Date fin"
            name="date_fin"
            type="date"
            value={form.date_fin}
            onChange={(e) => setForm({ ...form, date_fin: e.target.value })}
            required
            error={fieldErrors.date_fin}
          />
          <FormField
            label="Période active"
            name="is_active"
            type="checkbox"
            value={form.is_active}
            onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
          />
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={Boolean(confirmTarget)}
        onClose={() => !deactivating && setConfirmTarget(null)}
        onConfirm={handleDeactivate}
        confirming={deactivating}
        danger
        title="Désactiver la période ?"
        confirmLabel="Désactiver"
        message={
          confirmTarget
            ? `La période « ${confirmTarget.label} » (séquence ${confirmTarget.sequence}) sera désactivée.`
            : ''
        }
      />
    </div>
  );
}
