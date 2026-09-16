import { useCallback, useEffect, useState } from 'react';
import { gradingApi } from '../../services/api/grading';
import PageHeader from '../../components/PageHeader';
import Table from '../../components/Table';
import FormField from '../../components/FormField';
import Modal from '../../components/Modal';
import { useToast } from '../../components/Toast';
import { apiErrorMessage } from '../../utils/academicLabels';
import useAuth from '../../hooks/useAuth';
import { emptyIcons } from '../../utils/emptyIcons';

export default function EvaluationTypes() {
  const toast = useToast();
  const { isAdmin } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAll, setShowAll] = useState(true);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState({ code: '', label: '' });
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await gradingApi.listEvaluationTypes({ active_only: !showAll });
      setItems(data.items || data || []);
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Impossible de charger les types.'));
    } finally {
      setLoading(false);
    }
  }, [showAll, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await gradingApi.createEvaluationType(form);
      toast.success('Type créé');
      setModal(false);
      setForm({ code: '', label: '' });
      load();
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Création impossible'));
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (row) => {
    try {
      if (row.is_active) {
        await gradingApi.deactivateEvaluationType(row.id);
        toast.success(`${row.code} désactivé`);
      } else {
        await gradingApi.activateEvaluationType(row.id);
        toast.success(`${row.code} activé`);
      }
      load();
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Action impossible'));
    }
  };

  const columns = [
    { key: 'code', header: 'Code', render: (r) => r.code },
    { key: 'label', header: 'Libellé', render: (r) => r.label },
    {
      key: 'system',
      header: 'Système',
      render: (r) => (r.is_system ? 'Oui' : 'Non'),
    },
    {
      key: 'active',
      header: 'Actif',
      render: (r) =>
        r.is_active ? (
          <span className="badge-success">Actif</span>
        ) : (
          <span className="badge-neutral">Inactif</span>
        ),
    },
    {
      key: 'actions',
      header: '',
      render: (r) =>
        isAdmin ? (
          <button
            type="button"
            className="text-xs text-or-cachet hover:underline"
            onClick={() => toggleActive(r)}
          >
            {r.is_active ? 'Désactiver' : 'Activer'}
          </button>
        ) : null,
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Configuration"
        title="Types d’évaluation"
        subtitle="Catalogue utilisé pour créer des évaluations et composer les Rulesets."
        actions={
          isAdmin && (
            <button type="button" className="btn-primary" onClick={() => setModal(true)}>
              + Type personnalisé
            </button>
          )
        }
      />

      <Table
        columns={columns}
        data={items}
        loading={loading}
        emptyIcon={emptyIcons.config}
        emptyMessage="Aucun type d’évaluation"
        filters={
          <label className="flex items-center gap-2 text-sm text-texte-secondaire">
            <input
              type="checkbox"
              checked={showAll}
              onChange={(e) => setShowAll(e.target.checked)}
            />
            Afficher les inactifs
          </label>
        }
      />

      <Modal
        isOpen={modal}
        onClose={() => setModal(false)}
        title="Nouveau type d’évaluation"
        footer={
          <>
            <button type="button" className="btn-secondary" onClick={() => setModal(false)}>
              Annuler
            </button>
            <button type="submit" form="etype-form" className="btn-primary" disabled={saving}>
              {saving ? 'Création…' : 'Créer'}
            </button>
          </>
        }
      >
        <form id="etype-form" onSubmit={handleCreate} className="space-y-4">
          <FormField
            label="Code"
            name="code"
            value={form.code}
            onChange={(e) => setForm({ ...form, code: e.target.value })}
            required
            helpText="Ex. quiz — 2 à 20 caractères (a-z, 0-9, _)"
          />
          <FormField
            label="Libellé"
            name="label"
            value={form.label}
            onChange={(e) => setForm({ ...form, label: e.target.value })}
            required
          />
        </form>
      </Modal>
    </div>
  );
}
