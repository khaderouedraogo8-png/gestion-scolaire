import { useCallback, useEffect, useMemo, useState } from 'react';
import { emptyIcons } from '../../utils/emptyIcons';
import { financeApi } from '../../services/api/finance';
import { configApi } from '../../services/api/config';
import Table from '../../components/Table';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';

const TRANCHE_OPTIONS = [
  { value: '1', label: '1 (paiement unique)' },
  { value: '3', label: '3 tranches' },
  { value: '4', label: '4 tranches' },
  { value: '6', label: '6 tranches' },
];

function addMonths(date, months) {
  const d = new Date(date);
  d.setMonth(d.getMonth() + months);
  return d.toISOString().slice(0, 10);
}

function buildEcheancesPreview(montantTotal, nombreTranches) {
  const montant = parseFloat(montantTotal);
  const n = parseInt(nombreTranches, 10);
  if (!montant || n <= 1) return [];

  const base = Math.floor(montant / n);
  const remainder = Math.round((montant - base * n) * 100) / 100;
  const today = new Date();

  return Array.from({ length: n }, (_, i) => ({
    libelle: `${i + 1}${i === 0 ? 'ère' : 'e'} tranche`,
    montant: i === n - 1 ? base + remainder : base,
    date_echeance: addMonths(today, i),
  }));
}

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
    nombre_tranches: '1',
  });
  const [echeanceForm, setEcheanceForm] = useState({
    libelle: '',
    montant: '',
    date_echeance: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const previewEcheances = useMemo(
    () => buildEcheancesPreview(form.montant_total, form.nombre_tranches),
    [form.montant_total, form.nombre_tranches]
  );

  const previewSum = useMemo(
    () => previewEcheances.reduce((s, e) => s + Number(e.montant || 0), 0),
    [previewEcheances]
  );

  const montantTotal = parseFloat(form.montant_total) || 0;
  const echeancesBalanced =
    previewEcheances.length === 0 ||
    Math.abs(previewSum - montantTotal) < 0.02;

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
    if (!echeancesBalanced) {
      toast.error('La somme des échéances doit correspondre au montant total.');
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        id_niveau: form.id_niveau,
        id_annee: form.id_annee,
        motif: form.motif,
        montant_total: parseFloat(form.montant_total),
      };

      if (previewEcheances.length > 0) {
        await financeApi.createFraisWithEcheances({
          ...payload,
          echeances: previewEcheances,
        });
        toast.success(`Frais créé avec ${previewEcheances.length} échéance(s)`);
      } else {
        await financeApi.createFrais(payload);
        toast.success('Frais créé');
      }

      setModalOpen(false);
      setForm((f) => ({
        ...f,
        motif: 'Scolarité',
        montant_total: '',
        nombre_tranches: '1',
      }));
      load();
    } catch (err) {
      if (previewEcheances.length > 0) {
        try {
          const created = await financeApi.createFrais({
            id_niveau: form.id_niveau,
            id_annee: form.id_annee,
            motif: form.motif,
            montant_total: parseFloat(form.montant_total),
          });
          const fraisId = created.id;
          for (const ec of previewEcheances) {
            await financeApi.createEcheance({
              id_frais: fraisId,
              ...ec,
            });
          }
          toast.success(`Frais créé avec ${previewEcheances.length} échéance(s)`);
          setModalOpen(false);
          setForm((f) => ({
            ...f,
            motif: 'Scolarité',
            montant_total: '',
            nombre_tranches: '1',
          }));
          load();
          return;
        } catch {
          // fall through to original error
        }
      }
      toast.error(err.response?.data?.message || 'Erreur création');
    } finally {
      setSubmitting(false);
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

  const echeanceSumForFrais = (r) =>
    (r.echeances || []).reduce((s, ec) => s + Number(ec.montant || 0), 0);

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
      render: (r) => {
        const sum = echeanceSumForFrais(r);
        const balanced = Math.abs(sum - Number(r.montant_total)) < 0.02;
        return (
          <div className="space-y-1">
            {(r.echeances || []).map((ec) => (
              <p key={ec.id} className="text-xs text-texte-secondaire">
                {ec.libelle || 'Tranche'} — {Number(ec.montant).toLocaleString()} F (
                {ec.date_echeance})
              </p>
            ))}
            {(r.echeances || []).length > 0 && !balanced && (
              <p className="text-xs text-brique">
                Somme échéances ({sum.toLocaleString()} F) ≠ montant total
              </p>
            )}
            <button
              type="button"
              onClick={() => setEcheanceModal(r)}
              className="text-xs text-or-cachet hover:underline"
            >
              + Ajouter échéance
            </button>
          </div>
        );
      },
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
      <Table
        columns={columns}
        data={frais}
        loading={loading}
        emptyIcon={emptyIcons.finance}
        emptyTitle="Aucun frais configuré"
        emptyMessage="Définissez les montants et échéanciers par niveau pour l'année en cours."
        emptyAction={
          <button type="button" className="btn-primary" onClick={() => setModalOpen(true)}>
            Configurer les frais
          </button>
        }
      />

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
            label="Nombre de tranches"
            name="nombre_tranches"
            type="select"
            value={form.nombre_tranches}
            onChange={(e) => setForm({ ...form, nombre_tranches: e.target.value })}
            options={TRANCHE_OPTIONS}
          />
          {previewEcheances.length > 0 && (
            <div className="rounded-lg border border-bordure bg-craie/40 p-3 space-y-2">
              <p className="text-xs font-medium text-encre">Échéancier prévisionnel</p>
              {previewEcheances.map((ec, i) => (
                <div key={i} className="flex justify-between text-xs text-texte-secondaire">
                  <span>{ec.libelle} — {ec.date_echeance}</span>
                  <span className="tabular-nums">{Number(ec.montant).toLocaleString()} FCFA</span>
                </div>
              ))}
              <p
                className={`text-xs ${echeancesBalanced ? 'text-feuille' : 'text-brique'}`}
              >
                Total échéances : {previewSum.toLocaleString()} FCFA
                {echeancesBalanced ? ' ✓' : ` (attendu : ${montantTotal.toLocaleString()} FCFA)`}
              </p>
            </div>
          )}
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
          <button
            type="submit"
            className="btn-primary w-full"
            disabled={submitting || !echeancesBalanced}
          >
            {submitting ? 'Enregistrement…' : 'Enregistrer'}
          </button>
        </form>
      </Modal>

      <Modal
        isOpen={Boolean(echeanceModal)}
        onClose={() => setEcheanceModal(null)}
        title={`Échéance — ${echeanceModal?.motif || ''}`}
      >
        {echeanceModal && (
          <p className="mb-3 text-xs text-texte-secondaire">
            Montant total : {Number(echeanceModal.montant_total).toLocaleString()} FCFA — déjà
            planifié : {echeanceSumForFrais(echeanceModal).toLocaleString()} FCFA
          </p>
        )}
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
