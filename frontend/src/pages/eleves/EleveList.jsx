import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { elevesApi } from '../../services/api/eleves';
import { configApi } from '../../services/api/config';
import Table from '../../components/Table';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';

const STATUT_OPTIONS = [
  { value: '', label: 'Tous les statuts' },
  { value: 'inscrit', label: 'Inscrits' },
  { value: 'abandon', label: 'Abandons' },
  { value: 'suspendu', label: 'Suspendus' },
  { value: 'boursier', label: 'Boursiers' },
];

function StatutBadge({ statut, estBoursier }) {
  if (estBoursier) return <span className="badge-info">Boursier</span>;
  const map = {
    inscrit: 'badge-success',
    reinscrit: 'badge-success',
    abandon: 'badge-danger',
    suspendu: 'badge-warning',
    diplome: 'badge-neutral',
  };
  return <span className={map[statut] || 'badge-neutral'}>{statut || '—'}</span>;
}

export default function EleveList() {
  const navigate = useNavigate();
  const toast = useToast();
  const { isAdmin, isSecretariat } = useAuth();
  const canWrite = isAdmin || isSecretariat;

  const [eleves, setEleves] = useState([]);
  const [annees, setAnnees] = useState([]);
  const [anneeFilter, setAnneeFilter] = useState('');
  const [configReady, setConfigReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statut, setStatut] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const perPage = 15;

  useEffect(() => {
    let cancelled = false;

    const init = async () => {
      try {
        const ans = await configApi.listAnnees();
        if (cancelled) return;
        const anneeList = ans.items || ans || [];
        setAnnees(anneeList);
        const active = anneeList.find((a) => a.est_active);
        if (active) setAnneeFilter(String(active.id));
      } catch {
        /* ignore */
      } finally {
        if (!cancelled) setConfigReady(true);
      }
    };

    init();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!configReady) return;

    let cancelled = false;

    const load = async () => {
      setLoading(true);
      try {
        const data = await elevesApi.list({
          q: search || undefined,
          statut: statut || undefined,
          id_annee: anneeFilter || undefined,
          page,
          per_page: perPage,
        });
        if (!cancelled) {
          setEleves(data.items || []);
          setTotal(data.total || 0);
        }
      } catch {
        if (!cancelled) toast.error('Erreur lors du chargement des élèves');
        if (!cancelled) setEleves([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [configReady, search, statut, anneeFilter, page, toast]);

  const columns = [
    {
      key: 'matricule',
      header: 'Matricule',
      render: (row) => (
        <span className="font-mono text-xs font-medium text-primary-700">{row.matricule}</span>
      ),
    },
    {
      key: 'nom',
      header: 'Nom complet',
      render: (row) => (
        <div>
          <p className="font-medium text-slate-900">
            {row.prenom} {row.nom}
          </p>
          <p className="text-xs text-slate-500">{row.classe_nom || '—'}</p>
        </div>
      ),
    },
    {
      key: 'sexe',
      header: 'Sexe',
      render: (row) =>
        row.sexe === 'M' ? 'Masculin' : row.sexe === 'F' ? 'Féminin' : row.sexe || '—',
    },
    {
      key: 'statut',
      header: 'Statut',
      render: (row) => <StatutBadge statut={row.statut} estBoursier={row.est_boursier} />,
    },
    {
      key: 'actions',
      header: '',
      render: (row) => (
        <Link
          to={`/eleves/${row.id}`}
          className="text-sm font-medium text-primary-600 hover:text-primary-800"
          onClick={(e) => e.stopPropagation()}
        >
          Voir →
        </Link>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Élèves</h1>
          <p className="text-sm text-slate-500">Gestion des fiches élèves et inscriptions</p>
        </div>
        {canWrite && (
          <Link to="/eleves/nouveau" className="btn-primary">
            + Nouvel élève
          </Link>
        )}
      </div>

      <Table
        columns={columns}
        data={eleves}
        loading={loading}
        searchable
        searchPlaceholder="Rechercher par nom, matricule..."
        onSearch={(q) => {
          setSearch(q);
          setPage(1);
        }}
        onRowClick={(row) => navigate(`/eleves/${row.id}`)}
        filters={
          <div className="flex flex-wrap gap-2">
            <select
              value={anneeFilter}
              onChange={(e) => {
                setAnneeFilter(e.target.value);
                setPage(1);
              }}
              className="input w-auto"
            >
              {annees.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.libelle}
                  {a.est_active ? ' (active)' : ''}
                </option>
              ))}
            </select>
            <select
              value={statut}
              onChange={(e) => {
                setStatut(e.target.value);
                setPage(1);
              }}
              className="input w-auto"
            >
              {STATUT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        }
        pagination={{
          page,
          perPage,
          total,
          totalPages: Math.ceil(total / perPage) || 1,
          onPageChange: setPage,
        }}
        emptyMessage="Aucun élève trouvé pour cette année"
      />
    </div>
  );
}
