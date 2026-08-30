import { useCallback, useEffect, useState } from 'react';
import { emptyIcons } from '../../utils/emptyIcons';
import { financeApi } from '../../services/api/finance';
import { configApi } from '../../services/api/config';
import Table from '../../components/Table';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';

export default function FraisList() {
  const toast = useToast();
  const [frais, setFrais] = useState([]);
  const [niveaux, setNiveaux] = useState([]);
  const [annees, setAnnees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [echeanceModal, setEcheanceModal] = useState(null);
  const [form, setForm] = useState({
    id_niveau: '',
    id_annee: '',
    motif: 'Scolarité',
    montant_total: '',
  });
  const [echeanceForm, setEcheanceForm] = useState({
    libelle: '',
    montant: '',
    date_echeance: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [f, n, a] = await Promise.all([
        financeApi.listFrais(),
        configApi.listNiveaux(),
        configApi.listAnnees(),
      ]);
      setFrais(Array.isArray(f) ? f : f.items || []);
      setNiveaux(Array.isArray(n) ? n : n.items || []);
      const anneeList = Array.isArray(a) ? a : a.items || [];
      setAnnees(anneeList);
      const active = anneeList.find((x) => x.est_active);
      if (active && !form.id_annee) {
        setForm((prev) => ({ ...prev, id_annee: String(active.id) }));
      }
    } catch {
      toast.error('Erreur chargement frais');
    } finally {
      setLoading(false);
    }
  }, [toast, form.id_annee]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await financeApi.createFrais({
        ...form,
        montant_total: parseFloat(form.montant_total),
      });
      toast.success('Frais créé');
      setModalOpen(false);
      setForm((f) => ({ ...f, motif: 'Scolarité', montant_total: '' }));
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur création');
    }
  };

  const handleAddEcheance = async (e) => {
    e.preventDefault();
    try {
      await financeApi.createEcheance({
        id_frais: echeanceModal.id,
        libelle: echeanceForm.libelle,
        montant: parseFloat(echeanceForm.montant),
        date_echeance: echeanceForm.date_echeance,
      });
      toast.success('Échéance ajoutée');
      setEcheanceModal(null);
      setEcheanceForm({ libelle: '', montant: '', date_echeance: '' });
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur échéance');
    }
  };

  const columns = [
    { key: 'motif', header: 'Motif' },
    { key: 'niveau', header: 'Niveau', render: (r) => r.niveau_libelle || '—' },
    { key: 'annee', header: 'Année', render: (r) => r.annee_libelle || '—' },
    {
      key: 'montant_total',
      header: 'Montant (FCFA)',
      render: (r) => Number(r.montant_total).toLocaleString(),
    },
    {
      key: 'echeances',
      header: 'Échéances',
      render: (r) => (
        <div className="space-y-1">
          {(r.echeances || []).map((ec) => (
            <p key={ec.id} className="text-xs text-texte-secondaire">
              {ec.libelle || 'Tranche'} — {Number(ec.montant).toLocaleString()} F (
              {ec.date_echeance})
            </p>
          ))}
          <button
            type="button"
            onClick={() => setEcheanceModal(r)}
            className="text-xs text-or-cachet hover:underline"
          >
            + Ajouter échéance
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Finance"
        title="Frais scolaires"
        subtitle="Paramétrage par niveau et année scolaire"
        actions={
          <button type="button" className="btn-primary" onClick={() => setModalOpen(true)}>
            + Nouveau frais
          </button>
        }
      />
      <Table columns={columns} data={frais} loading={loading} emptyIcon={emptyIcons.finance} emptyMessage="Aucun frais configuré pour l'instant" />

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Nouveau frais">
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField
            label="Motif"
            value={form.motif}
            onChange={(e) => setForm({ ...form, motif: e.target.value })}
            required
          />
          <FormField
            label="Montant total"
            type="number"
            value={form.montant_total}
            onChange={(e) => setForm({ ...form, montant_total: e.target.value })}
            required
          />
          <FormField
            label="Niveau"
            name="id_niveau"
            type="select"
            value={form.id_niveau}
            onChange={(e) => setForm({ ...form, id_niveau: e.target.value })}
            required
            options={niveaux.map((n) => ({ value: String(n.id), label: n.libelle }))}
          />
          <FormField
            label="Année scolaire"
            name="id_annee"
            type="select"
            value={form.id_annee}
            onChange={(e) => setForm({ ...form, id_annee: e.target.value })}
            required
            options={annees.map((a) => ({ value: String(a.id), label: a.libelle }))}
          />
          <button type="submit" className="btn-primary w-full">
            Enregistrer
          </button>
        </form>
      </Modal>

      <Modal
        isOpen={Boolean(echeanceModal)}
        onClose={() => setEcheanceModal(null)}
        title={`Échéance — ${echeanceModal?.motif || ''}`}
      >
        <form onSubmit={handleAddEcheance} className="space-y-4">
          <FormField
            label="Libellé"
            value={echeanceForm.libelle}
            onChange={(e) => setEcheanceForm({ ...echeanceForm, libelle: e.target.value })}
            placeholder="Ex. 1ère tranche"
          />
          <FormField
            label="Montant (FCFA)"
            type="number"
            value={echeanceForm.montant}
            onChange={(e) => setEcheanceForm({ ...echeanceForm, montant: e.target.value })}
            required
          />
          <FormField
            label="Date d'échéance"
            type="date"
            value={echeanceForm.date_echeance}
            onChange={(e) => setEcheanceForm({ ...echeanceForm, date_echeance: e.target.value })}
            required
          />
          <button type="submit" className="btn-primary w-full">
            Ajouter
          </button>
        </form>
      </Modal>
    </div>
  );
}
