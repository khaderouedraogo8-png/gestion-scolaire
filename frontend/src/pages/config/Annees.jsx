import { useCallback, useEffect, useRef, useState } from 'react';
import { configApi } from '../../services/api/config';
import Table from '../../components/Table';
import { emptyIcons } from '../../utils/emptyIcons';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';

export default function Annees() {
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;

  const [annees, setAnnees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    libelle: '',
    date_debut: '',
    date_fin: '',
    est_active: false,
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await configApi.listAnnees();
      setAnnees(data.items || data || []);
    } catch {
      toastRef.current.error('Impossible de charger les années. Réessayez.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await configApi.createAnnee(form);
      toast.success('Année scolaire créée');
      setModalOpen(false);
      setForm({ libelle: '', date_debut: '', date_fin: '', est_active: false });
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur lors de la création');
    } finally {
      setSaving(false);
    }
  };

  const handleActivate = async (annee) => {
    try {
      await configApi.setAnneeActive(annee.id, annee);
      toast.success(`Année ${annee.libelle} activée`);
      load();
    } catch {
      toast.error('Erreur lors de l\'activation');
    }
  };

  const columns = [
    {
      key: 'libelle',
      header: 'Libellé',
      render: (r) => (
        <div className="flex items-center gap-2">
          <span className="font-medium">{r.libelle}</span>
          {r.est_active && <span className="badge-success">Active</span>}
        </div>
      ),
    },
    { key: 'debut', header: 'Début', render: (r) => r.date_debut || '—' },
    { key: 'fin', header: 'Fin', render: (r) => r.date_fin || '—' },
    {
      key: 'actions',
      header: '',
      render: (r) =>
        !r.est_active ? (
          <button
            type="button"
            onClick={() => handleActivate(r)}
            className="text-sm font-medium text-or-cachet hover:text-or-cachet/80"
          >
            Activer
          </button>
        ) : null,
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Configuration"
        title="Années scolaires"
        subtitle="Gestion des périodes scolaires"
        actions={
          <button type="button" onClick={() => setModalOpen(true)} className="btn-primary">
            + Nouvelle année
          </button>
        }
      />

      <Table
        columns={columns}
        data={annees}
        loading={loading}
        emptyIcon={emptyIcons.annees}
        emptyMessage="Aucune année scolaire pour l'instant — créez-en une via le bouton ci-dessus."
      />

      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Nouvelle année scolaire"
        footer={
          <>
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary">
              Annuler
            </button>
            <button type="submit" form="annee-form" disabled={saving} className="btn-primary">
              {saving ? 'Création...' : 'Créer'}
            </button>
          </>
        }
      >
        <form id="annee-form" onSubmit={handleCreate} className="space-y-4">
          <FormField
            label="Libellé"
            name="libelle"
            value={form.libelle}
            onChange={(e) => setForm({ ...form, libelle: e.target.value })}
            required
            placeholder="Ex. 2025-2026"
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              label="Date de début"
              name="date_debut"
              type="date"
              value={form.date_debut}
              onChange={(e) => setForm({ ...form, date_debut: e.target.value })}
              required
            />
            <FormField
              label="Date de fin"
              name="date_fin"
              type="date"
              value={form.date_fin}
              onChange={(e) => setForm({ ...form, date_fin: e.target.value })}
              required
            />
          </div>
          <FormField
            label="Définir comme année active"
            name="est_active"
            type="checkbox"
            value={form.est_active}
            onChange={(e) => setForm({ ...form, est_active: e.target.checked })}
          />
        </form>
      </Modal>
    </div>
  );
}
