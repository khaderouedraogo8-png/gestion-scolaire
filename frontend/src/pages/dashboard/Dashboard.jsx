import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { dashboardApi } from '../../services/api/dashboard';
import { configApi } from '../../services/api/config';
import { useToast } from '../../components/Toast';
import StatCard from '../../components/StatCard';
import Card from '../../components/Card';
import AbsenceFormModal from '../../components/AbsenceFormModal';
import { cycleLabel, toClassSlug } from '../../utils/classNavigation';

function AbsencesParClasseBlock({ title, cycles, emptyMessage }) {
  if (!cycles?.length) {
    return (
      <Card>
        <h3 className="mb-2 text-sm font-medium text-encre">{title}</h3>
        <p className="text-sm text-texte-secondaire">{emptyMessage}</p>
      </Card>
    );
  }

  return (
    <Card>
      <h3 className="mb-4 text-sm font-medium text-encre">{title}</h3>
      <div className="space-y-4">
        {cycles.map((block) => (
          <div key={block.cycle}>
            <p className="text-sm font-medium text-encre">
              {cycleLabel(block.cycle)} — {block.total} absence{block.total > 1 ? 's' : ''}
            </p>
            <ul className="mt-2 flex flex-wrap gap-2">
              {block.classes.map((cl) => (
                <li key={cl.id_classe}>
                  <Link
                    to={`/classes/${block.cycle}/${toClassSlug(cl.libelle)}?onglet=absences`}
                    className="inline-flex rounded-badge border border-bordure px-2 py-1 text-xs text-or-cachet hover:bg-or-cachet-clair"
                  >
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
      <Card>
        <h3 className="mb-4 text-sm font-medium text-encre">{title}</h3>
        <p className="text-sm text-texte-secondaire">Aucune donnée pour l'instant</p>
      </Card>
    );
  }

  const max = Math.max(...data.map((d) => d[valueKey] || 0), 1);

  return (
    <Card>
      <h3 className="mb-4 text-sm font-medium text-encre">{title}</h3>
      <div className="space-y-3">
        {data.map((item, i) => (
          <div key={i}>
            <div className="mb-1 flex justify-between text-xs">
              <span className="font-medium text-encre">{item[labelKey]}</span>
              <span className="tabular-nums text-texte-secondaire">{item[valueKey]}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-craie">
              <div
                className="h-full rounded-full bg-or-cachet transition-all"
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
      <Card>
        <h3 className="mb-4 text-sm font-medium text-encre">{title}</h3>
        <p className="text-sm text-texte-secondaire">Aucune donnée pour l'instant</p>
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

  const gradient = segments
    .map((s) => `${s.color} ${s.start}% ${s.start + s.pct}%`)
    .join(', ');

  return (
    <Card>
      <h3 className="mb-4 text-sm font-medium text-encre">{title}</h3>
      <div className="flex items-center gap-6">
        <div
          className="h-32 w-32 shrink-0 rounded-full"
          style={{ background: total > 0 ? `conic-gradient(${gradient})` : '#E4E2D9' }}
        />
        <div className="space-y-2">
          {segments.map((s, i) => (
            <div key={i} className="flex items-center gap-2 text-sm">
              <span className="h-3 w-3 rounded-full" style={{ backgroundColor: s.color }} />
              <span className="text-encre">{s.label}</span>
              <span className="font-medium tabular-nums text-encre">{s.value}</span>
              <span className="tabular-nums text-texte-secondaire">({s.pct.toFixed(0)}%)</span>
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
      <div className="flex items-center justify-center py-24">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-or-cachet-clair border-t-or-cachet" />
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
          <h1 className="page-title">Tableau de bord</h1>
          <p className="page-subtitle">Vue d'ensemble de votre établissement</p>
        </div>
        <button type="button" className="btn-primary" onClick={() => setAbsenceModalOpen(true)}>
          + Signaler une absence
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <StatCard
          title="Effectif total"
          value={stats?.total_eleves_inscrits ?? stats?.effectif_total ?? 0}
          subtitle="Élèves inscrits"
          tone="neutral"
        />
        <StatCard
          title="Taux de recouvrement"
          value={stats?.taux_recouvrement != null ? `${stats.taux_recouvrement}%` : '—'}
          subtitle="Paiements encaissés"
          tone="positive"
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
        />
        <StatCard
          title="Absences"
          value={stats?.total_absences ?? 0}
          subtitle="Total enregistrées"
          tone="negative"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <AbsencesParClasseBlock
          title="Absences du jour"
          cycles={absencesData?.absences_jour}
          emptyMessage="Aucune absence signalée aujourd'hui."
        />
        <AbsencesParClasseBlock
          title="Non justifiées en attente (7 jours)"
          cycles={absencesData?.non_justifiees_en_attente}
          emptyMessage="Aucune absence non justifiée en attente."
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
