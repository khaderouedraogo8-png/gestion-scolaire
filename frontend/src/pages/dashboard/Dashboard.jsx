import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Plus,
  GraduationCap,
  TrendingUp,
  Wallet,
  AlertCircle,
  ClipboardList,
  CalendarCheck,
  Clock,
  BarChart3,
  PieChart,
} from 'lucide-react';
import { dashboardApi } from '../../services/api/dashboard';
import { configApi } from '../../services/api/config';
import { useToast } from '../../components/Toast';
import StatCard from '../../components/StatCard';
import Card from '../../components/Card';
import PageHeader from '../../components/PageHeader';
import EmptyState from '../../components/EmptyState';
import AbsenceFormModal from '../../components/AbsenceFormModal';
import { cycleLabel, toClassSlug } from '../../utils/classNavigation';

function AbsencesParClasseBlock({ title, cycles, emptyMessage, emptyIcon: EmptyIcon }) {
  if (!cycles?.length) {
    return (
      <Card premium>
        <h3 className="section-title mb-4 !text-base">{title}</h3>
        <EmptyState icon={EmptyIcon} message={emptyMessage} />
      </Card>
    );
  }

  return (
    <Card premium>
      <h3 className="section-title mb-4 !text-base">{title}</h3>
      <div className="space-y-5">
        {cycles.map((block) => (
          <div key={block.cycle} className="border-b border-bordure/50 pb-4 last:border-0 last:pb-0">
            <p className="font-display text-sm font-medium text-encre">
              {cycleLabel(block.cycle)}
              <span className="ml-2 font-sans text-xs font-normal text-texte-secondaire">
                — {block.total} absence{block.total > 1 ? 's' : ''}
              </span>
            </p>
            <ul className="mt-3 flex flex-wrap gap-2">
              {block.classes.map((cl) => (
                <li key={cl.id_classe}>
                  <Link to={`/classes/${block.cycle}/${toClassSlug(cl.libelle)}?onglet=absences`} className="nav-pill">
                    {cl.libelle}: {cl.count}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </Card>
  );
}

function BarChart({ data, labelKey, valueKey, title }) {
  if (!data?.length) {
    return (
      <Card premium>
        <h3 className="section-title mb-4 !text-base">{title}</h3>
        <EmptyState icon={BarChart3} message="Aucune donnée pour l'instant." />
      </Card>
    );
  }

  const max = Math.max(...data.map((d) => d[valueKey] || 0), 1);

  return (
    <Card premium>
      <h3 className="section-title mb-5 !text-base">{title}</h3>
      <div className="space-y-4">
        {data.map((item, i) => (
          <div key={i}>
            <div className="mb-1.5 flex justify-between text-xs">
              <span className="font-medium text-encre">{item[labelKey]}</span>
              <span className="tabular-nums font-medium text-or-cachet">{item[valueKey]}%</span>
            </div>
            <div className="chart-bar-track">
              <div
                className="chart-bar-fill"
                style={{ width: `${((item[valueKey] || 0) / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function DonutChart({ data, title }) {
  if (!data?.length) {
    return (
      <Card premium>
        <h3 className="section-title mb-4 !text-base">{title}</h3>
        <EmptyState icon={PieChart} message="Aucune donnée pour l'instant." />
      </Card>
    );
  }

  const total = data.reduce((sum, d) => sum + (d.value || 0), 0);
  const colors = ['#14213D', '#2F6E4F', '#B8862E', '#A6432E', '#1F3A5F'];

  let cumulative = 0;
  const segments = data.map((d, i) => {
    const pct = total > 0 ? (d.value / total) * 100 : 0;
    const start = cumulative;
    cumulative += pct;
    return { ...d, pct, start, color: colors[i % colors.length] };
  });

  const gradient = segments.map((s) => `${s.color} ${s.start}% ${s.start + s.pct}%`).join(', ');

  return (
    <Card premium>
      <h3 className="section-title mb-6 !text-base">{title}</h3>
      <div className="flex flex-col items-center gap-8 sm:flex-row sm:items-start">
        <div className="relative shrink-0">
          <div
            className="h-36 w-36 rounded-full ring-1 ring-bordure/60"
            style={{ background: total > 0 ? `conic-gradient(${gradient})` : '#E4E2D9' }}
          />
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex h-[4.5rem] w-[4.5rem] flex-col items-center justify-center rounded-full border border-bordure/60 bg-blanc">
              <span className="font-display text-xl font-medium tabular-nums text-encre">{total}</span>
              <span className="text-[10px] uppercase tracking-[0.06em] text-texte-secondaire">Total</span>
            </div>
          </div>
        </div>
        <div className="w-full flex-1 space-y-2.5">
          {segments.map((s, i) => (
            <div
              key={i}
              className="flex items-center justify-between gap-3 rounded-input border border-bordure/60 bg-craie/40 px-3 py-2.5"
            >
              <div className="flex min-w-0 items-center gap-2.5">
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full ring-2 ring-blanc"
                  style={{ backgroundColor: s.color }}
                />
                <span className="truncate text-sm text-encre">{s.label}</span>
              </div>
              <div className="shrink-0 text-right text-sm">
                <span className="font-medium tabular-nums text-encre">{s.value}</span>
                <span className="ml-1.5 tabular-nums text-texte-secondaire">({s.pct.toFixed(0)}%)</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

export default function Dashboard() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [absencesData, setAbsencesData] = useState(null);
  const [idAnnee, setIdAnnee] = useState('');
  const [absenceModalOpen, setAbsenceModalOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const loadAnnees = async () => {
      try {
        const a = await configApi.listAnnees();
        const list = Array.isArray(a) ? a : a.items || [];
        const active = list.find((x) => x.est_active);
        if (!cancelled && active) setIdAnnee(String(active.id));
        else if (!cancelled) setLoading(false);
      } catch {
        if (!cancelled) {
          toast.error('Impossible de charger les années scolaires.');
          setLoading(false);
        }
      }
    };
    loadAnnees();
    return () => {
      cancelled = true;
    };
  }, [toast]);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      if (!idAnnee) return;
      setLoading(true);
      try {
        const [data, absences] = await Promise.all([
          dashboardApi.getStats({ id_annee: idAnnee }),
          dashboardApi.getAbsencesParClasse({ id_annee: idAnnee }),
        ]);
        if (!cancelled) {
          setStats(data);
          setAbsencesData(absences);
        }
      } catch {
        if (!cancelled) toast.error('Impossible de charger le tableau de bord.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [idAnnee, toast]);

  useEffect(() => {
    if (!idAnnee) {
      const t = setTimeout(() => setLoading(false), 0);
      return () => clearTimeout(t);
    }
  }, [idAnnee]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-32">
        <div className="loading-ring" />
        <p className="text-sm text-texte-secondaire">Chargement du tableau de bord…</p>
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
    <div className="space-y-10">
      <PageHeader
        eyebrow="Administration"
        title="Tableau de bord"
        subtitle="Vue d'ensemble claire de la vie de votre établissement"
        actions={
          <button type="button" className="btn-primary" onClick={() => setAbsenceModalOpen(true)}>
            <Plus className="h-4 w-4" strokeWidth={2} />
            Signaler une absence
          </button>
        }
      />

      <section>
        <h2 className="dashboard-section-label">Indicateurs clés</h2>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <StatCard
            title="Effectif total"
            value={stats?.total_eleves_inscrits ?? stats?.effectif_total ?? 0}
            subtitle="Élèves inscrits"
            tone="neutral"
            icon={GraduationCap}
            delay={0}
          />
          <StatCard
            title="Taux de recouvrement"
            value={stats?.taux_recouvrement != null ? `${stats.taux_recouvrement}%` : '—'}
            subtitle="Paiements encaissés"
            tone="positive"
            icon={TrendingUp}
            delay={60}
          />
          <StatCard
            title="Trésorerie"
            value={
              stats?.tresorerie != null
                ? `${Number(stats.tresorerie).toLocaleString('fr-FR')} FCFA`
                : '—'
            }
            subtitle="Total encaissé"
            tone="neutral"
            icon={Wallet}
            delay={120}
          />
          <StatCard
            title="Montant dû"
            value={
              stats?.total_du != null
                ? `${Number(stats.total_du).toLocaleString('fr-FR')} FCFA`
                : '—'
            }
            subtitle="Échéances scolaires"
            tone="warning"
            icon={AlertCircle}
            delay={180}
          />
          <StatCard
            title="Absences"
            value={stats?.total_absences ?? 0}
            subtitle="Total enregistrées"
            tone="negative"
            icon={ClipboardList}
            delay={240}
          />
        </div>
      </section>

      <section>
        <h2 className="dashboard-section-label">Suivi des absences</h2>
        <div className="grid gap-6 lg:grid-cols-2">
          <AbsencesParClasseBlock
            title="Absences du jour"
            cycles={absencesData?.absences_jour}
            emptyMessage="Aucune absence signalée aujourd'hui."
            emptyIcon={CalendarCheck}
          />
          <AbsencesParClasseBlock
            title="Non justifiées en attente (7 jours)"
            cycles={absencesData?.non_justifiees_en_attente}
            emptyMessage="Aucune absence non justifiée en attente."
            emptyIcon={Clock}
          />
        </div>
      </section>

      <section>
        <h2 className="dashboard-section-label">Analyses pédagogiques</h2>
        <div className="grid gap-6 lg:grid-cols-2">
          <DonutChart data={effectifData} title="Effectifs par niveau" />
          <BarChart
            data={reussiteData}
            labelKey="matiere"
            valueKey="taux"
            title="Taux de réussite par matière (%)"
          />
        </div>
      </section>

      <AbsenceFormModal
        isOpen={absenceModalOpen}
        onClose={() => setAbsenceModalOpen(false)}
        onCreated={async () => {
          if (idAnnee) {
            const absences = await dashboardApi.getAbsencesParClasse({ id_annee: idAnnee });
            setAbsencesData(absences);
          }
        }}
      />
    </div>
  );
}
