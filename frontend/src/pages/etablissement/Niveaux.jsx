import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Layers } from 'lucide-react';
import { configApi } from '../../services/api/config';
import Table from '../../components/Table';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import PageHeader from '../../components/PageHeader';
import StructureAcademiqueNav from '../../components/StructureAcademiqueNav';
import { useToast } from '../../components/Toast';
import {
  apiErrorMessage,
  asList,
  formatNiveauWithProgram,
} from '../../utils/academicLabels';

const EMPTY_FORM = {
  libelle: '',
  ordre: '',
  cycle: 'premier',
  id_program: '',
};

export default function Niveaux() {
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;

  const [niveaux, setNiveaux] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [programFilter, setProgramFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState({});
  const [saving, setSaving] = useState(false);

  const programById = useMemo(() => {
    const map = {};
    programs.forEach((p) => {
      map[String(p.id)] = p;
    });
    return map;
  }, [programs]);

  useEffect(() => {
    configApi
      .listPrograms({ is_active: true })
      .then((data) => setPrograms(asList(data)))
      .catch((err) => {
        toastRef.current.error(apiErrorMessage(err, 'Impossible de charger les programmes.'));
      });
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const params = {};
      if (programFilter) params.id_program = programFilter;
      const data = await configApi.listNiveaux(params);
      setNiveaux(asList(data));
    } catch (err) {
      const msg = apiErrorMessage(err, 'Impossible de charger les niveaux.');
      setLoadError(msg);
      toastRef.current.error(msg);
    } finally {
      setLoading(false);
    }
  }, [programFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setEditing(null);
    setForm({
      ...EMPTY_FORM,
      id_program: programFilter || (programs[0] ? String(programs[0].id) : ''),
    });
    setFieldErrors({});
    setModalOpen(true);
  };

  const openEdit = (niveau) => {
    setEditing(niveau);
    setForm({
      libelle: niveau.libelle || '',
      ordre: niveau.ordre != null ? String(niveau.ordre) : '',
      cycle: niveau.cycle || 'premier',
      id_program: niveau.id_program ? String(niveau.id_program) : '',
    });
    setFieldErrors({});
    setModalOpen(true);
  };

  const validate = () => {
    const errors = {};
    if (!form.libelle.trim()) errors.libelle = 'Le libellé est obligatoire.';
    if (!form.id_program) errors.id_program = 'Le programme est obligatoire.';
    if (form.ordre !== '' && Number.isNaN(Number(form.ordre))) {
      errors.ordre = 'Ordre invalide.';
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
        libelle: form.libelle.trim(),
        cycle: form.cycle,
        id_program: form.id_program,
        ordre: form.ordre === '' ? null : Number(form.ordre),
      };
      if (editing) {
        await configApi.updateNiveau(editing.id, payload);
        toast.success('Niveau mis à jour');
      } else {
        await configApi.createNiveau(payload);
        toast.success('Niveau créé');
      }
      setModalOpen(false);
      load();
    } catch (err) {
      toast.error(apiErrorMessage(err, "Erreur lors de l'enregistrement"));
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    {
      key: 'ordre',
      header: 'Ordre',
      render: (r) => r.ordre ?? '—',
    },
    {
      key: 'libelle',
      header: 'Niveau',
      render: (r) => (
        <span className="font-medium text-encre">
          {formatNiveauWithProgram(r, programById)}
        </span>
      ),
    },
    {
      key: 'program',
      header: 'Programme',
      render: (r) => {
        const p = programById[String(r.id_program)];
        return p ? (
          <span>
            {p.name}{' '}
            <span className="text-xs text-texte-secondaire">({p.code})</span>
          </span>
        ) : (
          '—'
        );
      },
    },
    {
      key: 'cycle',
      header: 'Cycle',
      render: (r) => (r.cycle === 'second' ? 'Second cycle' : 'Premier cycle'),
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (r) => (
        <button
          type="button"
          className="text-sm font-medium text-or-cachet hover:underline"
          onClick={() => openEdit(r)}
        >
          Modifier
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Structure académique"
        title="Niveaux d’étude"
        subtitle="Un même libellé (ex. 2nde) peut exister dans plusieurs programmes — le contexte filière est toujours visible."
        actions={
          <button type="button" className="btn-primary" onClick={openCreate}>
            + Nouveau niveau
          </button>
        }
      />

      <StructureAcademiqueNav />

      {loadError && !loading && niveaux.length === 0 ? (
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
          data={niveaux}
          loading={loading}
          emptyIcon={Layers}
          emptyMessage="Aucun niveau pour ce filtre. Créez un niveau rattaché à un programme."
          filters={
            <select
              className="input w-auto"
              value={programFilter}
              onChange={(e) => setProgramFilter(e.target.value)}
              aria-label="Filtrer par programme"
            >
              <option value="">Tous les programmes</option>
              {programs.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.code})
                </option>
              ))}
            </select>
          }
        />
      )}

      <Modal
        isOpen={modalOpen}
        onClose={() => !saving && setModalOpen(false)}
        title={editing ? 'Modifier le niveau' : 'Nouveau niveau'}
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
            <button type="submit" form="niveau-form" className="btn-primary" disabled={saving}>
              {saving ? 'Enregistrement…' : editing ? 'Enregistrer' : 'Créer'}
            </button>
          </>
        }
      >
        <form id="niveau-form" onSubmit={handleSubmit} className="space-y-4">
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
            helpText="Le niveau appartient à un programme — deux « 2nde » peuvent coexister."
          />
          <FormField
            label="Libellé"
            name="libelle"
            value={form.libelle}
            onChange={(e) => setForm({ ...form, libelle: e.target.value })}
            required
            error={fieldErrors.libelle}
            placeholder="Ex. 2nde"
          />
          <FormField
            label="Ordre"
            name="ordre"
            type="number"
            value={form.ordre}
            onChange={(e) => setForm({ ...form, ordre: e.target.value })}
            error={fieldErrors.ordre}
          />
          <FormField
            label="Cycle"
            name="cycle"
            type="select"
            value={form.cycle}
            onChange={(e) => setForm({ ...form, cycle: e.target.value })}
            options={[
              { value: 'premier', label: 'Premier cycle' },
              { value: 'second', label: 'Second cycle' },
            ]}
          />
        </form>
      </Modal>
    </div>
  );
}
