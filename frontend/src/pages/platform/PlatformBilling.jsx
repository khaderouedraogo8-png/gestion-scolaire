import { useCallback, useEffect, useState } from 'react';
import { platformApi } from '../../services/api/platform';
import PageHeader from '../../components/PageHeader';
import Table from '../../components/Table';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

function formatXof(n) {
  if (n == null || n === '') return '—';
  return `${Number(n).toLocaleString('fr-FR')} XOF`;
}

export default function PlatformBilling() {
  const toast = useToast();
  const [ops, setOps] = useState(null);
  const [subs, setSubs] = useState([]);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState('');
  const [planCode, setPlanCode] = useState('starter');
  const [invoices, setInvoices] = useState([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [opsData, subsData, plansData] = await Promise.all([
        platformApi.billingOps(),
        platformApi.listSubscriptions(),
        platformApi.listPlans(),
      ]);
      setOps(opsData);
      setSubs(Array.isArray(subsData) ? subsData : []);
      setPlans(Array.isArray(plansData) ? plansData : []);
    } catch {
      toast.error('Impossible de charger la facturation SaaS');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const loadInvoices = async (schoolId) => {
    setSelected(schoolId);
    try {
      const data = await platformApi.listInvoices(schoolId);
      setInvoices(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Factures introuvables');
    }
  };

  const assign = async () => {
    if (!selected) {
      toast.error('Sélectionnez une école');
      return;
    }
    try {
      await platformApi.assignPlan(selected, { plan_code: planCode, start_active: false });
      toast.success('Plan assigné');
      load();
      loadInvoices(selected);
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur assignation');
    }
  };

  const issue = async () => {
    if (!selected) return;
    try {
      await platformApi.issueInvoice(selected, {});
      toast.success('Facture émise');
      loadInvoices(selected);
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur facture');
    }
  };

  const pay = async (invoiceId) => {
    try {
      await platformApi.payInvoice(invoiceId, { external_ref: `MANUAL-${Date.now()}` });
      toast.success('Paiement enregistré — école réactivée si besoin');
      loadInvoices(selected);
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur paiement');
    }
  };

  const expire = async () => {
    try {
      const stats = await platformApi.expireSubscriptions();
      toast.success(`Expirations : ${stats.past_due} past_due, ${stats.suspended} suspendues`);
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur expiration');
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Plateforme"
        title="Facturation SaaS"
        subtitle="Plans, abonnements, factures et suspension pour non-paiement"
      />

      {ops && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="card-premium p-4">
            <p className="text-xs uppercase tracking-wide text-encre/50">Écoles</p>
            <p className="font-display text-2xl font-semibold text-encre">
              {ops.schools_active}/{ops.schools_total}
            </p>
            <p className="text-sm text-encre/60">actives</p>
          </div>
          <div className="card-premium p-4">
            <p className="text-xs uppercase tracking-wide text-encre/50">Impayés</p>
            <p className="font-display text-2xl font-semibold text-encre">{ops.overdue_count}</p>
            <p className="text-sm text-encre/60">past_due / suspended</p>
          </div>
          <div className="card-premium p-4">
            <p className="text-xs uppercase tracking-wide text-encre/50">MRR</p>
            <p className="font-display text-2xl font-semibold text-encre">{formatXof(ops.mrr_xof)}</p>
            <p className="text-sm text-encre/60">abonnements actifs</p>
          </div>
          <div className="card-premium flex flex-col justify-center gap-2 p-4">
            <button type="button" className="btn-secondary" onClick={expire}>
              Lancer expirations
            </button>
            <button type="button" className="btn-ghost text-sm" onClick={load}>
              Actualiser
            </button>
          </div>
        </div>
      )}

      <section className="space-y-3">
        <h2 className="font-display text-lg font-semibold text-encre">Plans</h2>
        <Table
          columns={[
            { key: 'code', header: 'Code' },
            { key: 'name', header: 'Nom' },
            { key: 'price_xof', header: 'Prix', render: (p) => formatXof(p.price_xof) },
            { key: 'billing_interval', header: 'Intervalle' },
            { key: 'max_eleves', header: 'Max élèves', render: (p) => p.max_eleves ?? '∞' },
            { key: 'trial_days', header: 'Essai (j)' },
          ]}
          data={plans}
          loading={loading}
          emptyMessage="Aucun plan."
        />
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-lg font-semibold text-encre">Abonnements</h2>
        <Table
          columns={[
            { key: 'school_code', header: 'Code' },
            { key: 'school_name', header: 'École' },
            {
              key: 'plan',
              header: 'Plan',
              render: (r) => r.subscription?.plan?.code || '—',
            },
            {
              key: 'status',
              header: 'Statut',
              render: (r) => r.subscription?.status || '—',
            },
            {
              key: 'period',
              header: 'Fin période',
              render: (r) => r.subscription?.current_period_end || '—',
            },
            {
              key: 'actions',
              header: '',
              render: (r) => (
                <button
                  type="button"
                  className="btn-ghost text-sm"
                  onClick={() => loadInvoices(r.school_id)}
                >
                  Factures
                </button>
              ),
            },
          ]}
          data={subs}
          loading={loading}
          emptyMessage="Aucun abonnement."
        />
      </section>

      {selected && (
        <section className="card-premium space-y-4 p-5">
          <h2 className="font-display text-lg font-semibold text-encre">Actions école</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            <FormField
              label="Plan"
              name="plan_code"
              type="select"
              value={planCode}
              onChange={(e) => setPlanCode(e.target.value)}
              options={plans.map((p) => ({ value: p.code, label: `${p.name} (${p.code})` }))}
            />
            <div className="flex items-end gap-2">
              <button type="button" className="btn-secondary" onClick={assign}>
                Assigner plan
              </button>
              <button type="button" className="btn-primary" onClick={issue}>
                Émettre facture
              </button>
            </div>
          </div>
          <Table
            columns={[
              { key: 'number', header: 'N°' },
              { key: 'amount_xof', header: 'Montant', render: (i) => formatXof(i.amount_xof) },
              { key: 'status', header: 'Statut' },
              { key: 'due_at', header: 'Échéance' },
              {
                key: 'pay',
                header: '',
                render: (i) =>
                  i.status !== 'paid' ? (
                    <button type="button" className="btn-ghost text-sm" onClick={() => pay(i.id)}>
                      Marquer payée
                    </button>
                  ) : (
                    'Payée'
                  ),
              },
            ]}
            data={invoices}
            emptyMessage="Aucune facture."
          />
        </section>
      )}
    </div>
  );
}
