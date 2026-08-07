import { useEffect, useState } from 'react';
import { dashboardApi } from '../../services/api/dashboard';
import { configApi } from '../../services/api/config';
import { useToast } from '../../components/Toast';

function StatCard({ title, value, subtitle, icon, color = 'primary' }) {
  const colors = {
    primary: 'bg-primary-50 text-primary-700',
    emerald: 'bg-emerald-50 text-emerald-700',
    amber: 'bg-amber-50 text-amber-700',
    blue: 'bg-blue-50 text-blue-700',
  };

  return (
    <div className="card">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <p className="mt-2 text-3xl font-bold text-slate-900">{value ?? '—'}</p>
          {subtitle && <p className="mt-1 text-xs text-slate-500">{subtitle}</p>}
        </div>
        <div className={`flex h-12 w-12 items-center justify-center rounded-xl text-2xl ${colors[color]}`}>
          {icon}
        </div>
      </div>
    </div>
  );
}

function BarChart({ data, labelKey, valueKey, title }) {
  if (!data?.length) {
    return (
      <div className="card">
        <h3 className="mb-4 text-sm font-semibold text-slate-900">{title}</h3>
        <p className="text-sm text-slate-500">Aucune donnée disponible</p>
      </div>
    );
  }

  const max = Math.max(...data.map((d) => d[valueKey] || 0), 1);

  return (
    <div className="card">
      <h3 className="mb-4 text-sm font-semibold text-slate-900">{title}</h3>
      <div className="space-y-3">
        {data.map((item, i) => (
          <div key={i}>
            <div className="mb-1 flex justify-between text-xs">
              <span className="font-medium text-slate-700">{item[labelKey]}</span>
              <span className="text-slate-500">{item[valueKey]}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-primary-500 transition-all"
                style={{ width: `${((item[valueKey] || 0) / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DonutChart({ data, title }) {
  if (!data?.length) {
    return (
      <div className="card">
        <h3 className="mb-4 text-sm font-semibold text-slate-900">{title}</h3>
        <p className="text-sm text-slate-500">Aucune donnée disponible</p>
      </div>
    );
  }

  const total = data.reduce((sum, d) => sum + (d.value || 0), 0);
  const colors = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#3b82f6'];

  let cumulative = 0;
  const segments = data.map((d, i) => {
    const pct = total > 0 ? (d.value / total) * 100 : 0;
    const start = cumulative;
    cumulative += pct;
    return { ...d, pct, start, color: colors[i % colors.length] };
  });

  const gradient = segments
    .map((s) => `${s.color} ${s.start}% ${s.start + s.pct}%`)
    .join(', ');

  return (
    <div className="card">
      <h3 className="mb-4 text-sm font-semibold text-slate-900">{title}</h3>
      <div className="flex items-center gap-6">
        <div
          className="h-32 w-32 shrink-0 rounded-full"
          style={{ background: total > 0 ? `conic-gradient(${gradient})` : '#e2e8f0' }}
        />
        <div className="space-y-2">
          {segments.map((s, i) => (
            <div key={i} className="flex items-center gap-2 text-sm">
              <span className="h-3 w-3 rounded-full" style={{ backgroundColor: s.color }} />
              <span className="text-slate-700">{s.label}</span>
              <span className="font-medium text-slate-900">{s.value}</span>
              <span className="text-slate-400">({s.pct.toFixed(0)}%)</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [idAnnee, setIdAnnee] = useState('');

  useEffect(() => {
    const loadAnnees = async () => {
      try {
        const a = await configApi.listAnnees();
        const list = Array.isArray(a) ? a : a.items || [];
        const active = list.find((x) => x.est_active);
        if (active) setIdAnnee(String(active.id));
        else setLoading(false);
      } catch {
        toast.error('Erreur chargement années scolaires');
        setLoading(false);
      }
    };
    loadAnnees();
  }, [toast]);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      try {
        const data = await dashboardApi.getStats(
          idAnnee ? { id_annee: idAnnee } : {}
        );
        if (!cancelled) setStats(data);
      } catch {
        if (!cancelled) toast.error('Erreur lors du chargement du tableau de bord');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [idAnnee, toast]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      </div>
    );
  }

  const effectifsRaw = stats?.effectifs_par_niveau || [];
  const byNiveau = {};
  effectifsRaw.forEach((e) => {
    byNiveau[e.niveau] = (byNiveau[e.niveau] || 0) + (e.effectif || 0);
  });
  const effectifData = Object.entries(byNiveau).map(([label, value]) => ({ label, value }));

  const reussiteData = (stats?.taux_reussite_par_matiere || []).map((r) => ({
    matiere: r.matiere,
    taux: r.taux,
  }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Tableau de bord</h1>
          <p className="text-sm text-slate-500">Vue d'ensemble de votre établissement</p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <StatCard
          title="Effectif total"
          value={stats?.total_eleves_inscrits ?? stats?.effectif_total ?? 0}
          subtitle="Élèves inscrits"
          icon="👨‍🎓"
          color="primary"
        />
        <StatCard
          title="Taux de recouvrement"
          value={stats?.taux_recouvrement != null ? `${stats.taux_recouvrement}%` : '—'}
          subtitle="Paiements encaissés"
          icon="💰"
          color="emerald"
        />
        <StatCard
          title="Trésorerie"
          value={
            stats?.tresorerie != null
              ? `${Number(stats.tresorerie).toLocaleString('fr-FR')} FCFA`
              : '—'
          }
          subtitle="Total encaissé"
          icon="🏦"
          color="blue"
        />
        <StatCard
          title="Montant dû"
          value={
            stats?.total_du != null
              ? `${Number(stats.total_du).toLocaleString('fr-FR')} FCFA`
              : '—'
          }
          subtitle="Échéances scolaires"
          icon="⚠️"
          color="amber"
        />
        <StatCard
          title="Absences"
          value={stats?.total_absences ?? 0}
          subtitle="Total enregistrées"
          icon="📋"
          color="primary"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <DonutChart data={effectifData} title="Effectifs par niveau" />
        <BarChart
          data={reussiteData}
          labelKey="matiere"
          valueKey="taux"
          title="Taux de réussite par matière (%)"
        />
      </div>
    </div>
  );
}
