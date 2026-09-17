import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { comptabiliteApi } from '../../services/api/comptabilite';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function ComptabiliteEcritures() {
  const toast = useToast();
  const [rows, setRows] = useState([]);
  const [balance, setBalance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    date_ecriture: new Date().toISOString().slice(0, 10),
    libelle: '',
    compte_debit: '',
    compte_credit: '',
    montant: '',
    reference: '',
    journal: 'OD',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [e, b] = await Promise.all([
        comptabiliteApi.listEcritures(),
        comptabiliteApi.getBalance(),
      ]);
      setRows(Array.isArray(e) ? e : []);
      setBalance(b);
    } catch {
      toast.error('Impossible de charger les écritures');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const create = async (e) => {
    e.preventDefault();
    try {
      await comptabiliteApi.createEcriture({
        ...form,
        montant: String(form.montant),
        reference: form.reference || null,
      });
      toast.success('Écriture saisie');
      setForm((f) => ({ ...f, libelle: '', compte_debit: '', compte_credit: '', montant: '', reference: '' }));
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="SYSCOHADA"
        title="Écritures comptables"
        subtitle="Journal des écritures et balance"
        actions={
          <div className="flex flex-wrap gap-2">
            <Link to="/finance/syscohada" className="btn-secondary">
              Plan comptable
            </Link>
            <Link to="/finance/paie" className="btn-secondary">
              Paie
            </Link>
          </div>
        }
      />

      <form onSubmit={create} className="card-premium grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-3">
        <FormField label="Date" name="date_ecriture" type="date" value={form.date_ecriture} onChange={(e) => setForm((f) => ({ ...f, date_ecriture: e.target.value }))} required />
        <FormField label="Libellé" name="libelle" value={form.libelle} onChange={(e) => setForm((f) => ({ ...f, libelle: e.target.value }))} required />
        <FormField label="Compte débit" name="compte_debit" value={form.compte_debit} onChange={(e) => setForm((f) => ({ ...f, compte_debit: e.target.value }))} required />
        <FormField label="Compte crédit" name="compte_credit" value={form.compte_credit} onChange={(e) => setForm((f) => ({ ...f, compte_credit: e.target.value }))} required />
        <FormField label="Montant" name="montant" value={form.montant} onChange={(e) => setForm((f) => ({ ...f, montant: e.target.value }))} required />
        <FormField label="Référence" name="reference" value={form.reference} onChange={(e) => setForm((f) => ({ ...f, reference: e.target.value }))} />
        <button type="submit" className="btn-primary w-fit">Saisir</button>
      </form>

      <Table
        columns={[
          { key: 'date_ecriture', header: 'Date' },
          { key: 'libelle', header: 'Libellé' },
          { key: 'compte_debit', header: 'Débit' },
          { key: 'compte_credit', header: 'Crédit' },
          {
            key: 'montant',
            header: 'Montant',
            render: (r) => `${Number(r.montant).toLocaleString('fr-FR')} FCFA`,
          },
        ]}
        data={rows}
        loading={loading}
        emptyMessage="Aucune écriture."
      />

      {balance && (
        <div className="card-premium p-5">
          <h3 className="section-title mb-3 !text-base">Balance (aperçu)</h3>
          <pre className="max-h-64 overflow-auto rounded-input bg-craie p-3 text-xs text-texte-secondaire">
            {JSON.stringify(balance, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
