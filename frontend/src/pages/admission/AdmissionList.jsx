import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { admissionApi } from '../../services/api/admission';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';
import { emptyIcons } from '../../utils/emptyIcons';

const STATUTS = [
  { value: '', label: 'Tous' },
  { value: 'brouillon', label: 'Brouillon' },
  { value: 'soumis', label: 'Soumis' },
  { value: 'en_examen', label: 'En examen' },
  { value: 'accepte', label: 'Accepté' },
  { value: 'refuse', label: 'Refusé' },
  { value: 'liste_attente', label: 'Liste d’attente' },
  { value: 'inscrit', label: 'Inscrit' },
];

const BADGE = {
  brouillon: 'badge-neutral',
  soumis: 'badge-info',
  en_examen: 'badge-warning',
  accepte: 'badge-success',
  refuse: 'badge-danger',
  liste_attente: 'badge-warning',
  inscrit: 'badge-success',
};

export default function AdmissionList() {
  const toast = useToast();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statut, setStatut] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await admissionApi.list(statut ? { statut } : {});
      setRows(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Impossible de charger les dossiers');
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [statut, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const columns = [
    {
      key: 'candidat',
      header: 'Candidat',
      render: (r) => `${r.prenom || ''} ${r.nom || ''}`.trim(),
    },
    { key: 'niveau_demande', header: 'Niveau' },
    {
      key: 'telephone_parent',
      header: 'Contact parent',
      render: (r) => r.telephone_parent || r.email_parent || '—',
    },
    {
      key: 'statut',
      header: 'Statut',
      render: (r) => <span className={BADGE[r.statut] || 'badge-neutral'}>{r.statut}</span>,
    },
    {
      key: 'actions',
      header: '',
      render: (r) => (
        <Link to={`/admission/${r.id}`} className="text-sm font-medium text-or-cachet hover:underline">
          Ouvrir
        </Link>
      ),
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Admissions"
        title="Dossiers d’admission"
        subtitle="Funnel de candidatures — du brouillon à l’inscription"
        actions={
          <Link to="/admission/nouveau" className="btn-primary">
            <Plus className="h-4 w-4" strokeWidth={2} />
            Nouveau dossier
          </Link>
        }
      />

      <div className="flex flex-wrap gap-3">
        <select
          className="input max-w-xs"
          value={statut}
          onChange={(e) => setStatut(e.target.value)}
        >
          {STATUTS.map((s) => (
            <option key={s.value || 'all'} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      <Table
        columns={columns}
        data={rows}
        loading={loading}
        emptyIcon={emptyIcons.eleves}
        emptyMessage="Aucun dossier d’admission."
      />
    </div>
  );
}
