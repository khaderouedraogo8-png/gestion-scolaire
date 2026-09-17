import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { TrendingUp, Wallet, AlertCircle, Users } from 'lucide-react';
import { financeApi } from '../../services/api/finance';
import { configApi } from '../../services/api/config';
import StatCard from '../../components/StatCard';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';

const AGING_KEYS = ['J0-30', 'J31-60', 'J61-90', 'J90+'];

function AgingBars({ aging }) {
  if (!aging) return null;
  const max = Math.max(...AGING_KEYS.map((k) => Number(aging[k]?.montant || 0)), 1);
  return (
    <div className="space-y-3">
      {AGING_KEYS.map((key) => {
        const bucket = aging[key] || { montant: 0, count: 0 };
        const pct = Math.round((Number(bucket.montant) / max) * 100);
        return (
          <div key={key}>
            <div className="mb-1 flex justify-between text-xs text-texte-secondaire">
              <span>{key}</span>
              <span>
                {Number(bucket.montant).toLocaleString('fr-FR')} FCFA · {bucket.count} échéance(s)
              </span>
            </div>
            <div className="h-2.5 overflow-hidden rounded bg-bordure/40">
              <div
                className="h-full rounded bg-brique/80 transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function Recouvrement() {
  const toast = useToast();
  const [detail, setDetail] = useState(null);
  const [annees, setAnnees] = useState([]);
  const [idAnnee, setIdAnnee] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    configApi.listAnnees().then((a) => {
      const list = Array.isArray(a) ? a : a.items || [];
      setAnnees(list);
      const active = list.find((x) => x.est_active);
      if (active) setIdAnnee(String(active.id));
    }).catch(() => toast.error('Impossible de charger les années'));
  }, [toast]);

  const load = useCallback(async () => {
    if (!idAnnee) return;
    setLoading(true);
    try {
      const data = await financeApi.getRecouvrementDetail({ id_annee: idAnnee });
      setDetail(data);
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur recouvrement');
      setDetail(null);
    } finally {
      setLoading(false);
    }
  }, [idAnnee, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const top = detail?.top_debiteurs || detail?.top_arrieres || [];
  const byClasse = detail?.by_classe || [];
  const byMotif = detail?.by_motif || [];

  const motifMax = useMemo(
    () => Math.max(...byMotif.map((m) => Number(m.montant) || 0), 1),
    [byMotif]
  );

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Finance"
        title="Recouvrement"
        subtitle="Tableau de bord détaillé des encaissements et arriérés"
        actions={
          <Link to="/finance/arrieres" className="btn-secondary">
            Voir les arriérés
          </Link>
        }
      />

      <select
        className="input max-w-xs"
        value={idAnnee}
        onChange={(e) => setIdAnnee(e.target.value)}
      >
        {annees.map((a) => (
          <option key={a.id} value={String(a.id)}>
            {a.libelle}
          </option>
        ))}
      </select>

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="loading-ring" />
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              title="Taux de recouvrement"
              value={detail ? `${detail.taux_recouvrement}%` : '—'}
              icon={TrendingUp}
              tone="positive"
            />
            <StatCard
              title="Total dû"
              value={
                detail
                  ? `${Number(detail.total_du).toLocaleString('fr-FR')} FCFA`
                  : '—'
              }
              icon={Wallet}
              tone="warning"
            />
            <StatCard
              title="Total payé"
              value={
                detail
                  ? `${Number(detail.total_paye).toLocaleString('fr-FR')} FCFA`
                  : '—'
              }
              icon={Wallet}
              tone="neutral"
            />
            <StatCard
              title="Élèves en retard"
              value={detail?.nb_eleves_en_retard ?? 0}
              icon={Users}
              tone="negative"
              subtitle={
                detail
                  ? `${Number(detail.total_arriere).toLocaleString('fr-FR')} FCFA`
                  : undefined
              }
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <section>
              <h2 className="dashboard-section-label">Aging (jours de retard)</h2>
              <div className="card-premium p-5">
                <AgingBars aging={detail?.aging} />
              </div>
            </section>
            <section>
              <h2 className="dashboard-section-label">Par motif</h2>
              <div className="card-premium space-y-3 p-5">
                {byMotif.length === 0 ? (
                  <p className="text-sm text-texte-secondaire">Aucun motif en retard.</p>
                ) : (
                  byMotif.map((m) => (
                    <div key={m.motif}>
                      <div className="mb-1 flex justify-between text-xs">
                        <span>{m.motif}</span>
                        <span className="tabular-nums">
                          {Number(m.montant).toLocaleString('fr-FR')} FCFA
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded bg-bordure/40">
                        <div
                          className="h-full rounded bg-or-cachet/70"
                          style={{
                            width: `${Math.round((Number(m.montant) / motifMax) * 100)}%`,
                          }}
                        />
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>

          <div>
            <h2 className="dashboard-section-label">Par classe</h2>
            <Table
              columns={[
                { key: 'classe', header: 'Classe' },
                {
                  key: 'montant',
                  header: 'Arriéré',
                  render: (r) => `${Number(r.montant).toLocaleString('fr-FR')} FCFA`,
                },
                { key: 'count', header: 'Échéances' },
              ]}
              data={byClasse}
              loading={false}
              emptyMessage="Aucune répartition par classe."
            />
          </div>

          <div>
            <h2 className="dashboard-section-label">Top débiteurs</h2>
            <Table
              columns={[
                { key: 'matricule', header: 'Matricule' },
                {
                  key: 'nom',
                  header: 'Élève',
                  render: (r) => `${r.prenom} ${r.nom}`,
                },
                {
                  key: 'arriere',
                  header: 'Arriéré',
                  render: (r) => (
                    <span className="font-semibold text-brique">
                      {Number(r.arriere).toLocaleString('fr-FR')} FCFA
                    </span>
                  ),
                },
                {
                  key: 'total_paye',
                  header: 'Payé',
                  render: (r) => `${Number(r.total_paye).toLocaleString('fr-FR')} FCFA`,
                },
              ]}
              data={top}
              loading={false}
              emptyIcon={AlertCircle}
              emptyMessage="Aucun arriéré pour cette année."
            />
          </div>
        </>
      )}
    </div>
  );
}
