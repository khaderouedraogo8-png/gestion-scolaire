import { useCallback, useEffect, useState } from 'react';
import { auditApi } from '../../services/api/audit';
import Table from '../../components/Table';
import { useToast } from '../../components/Toast';

export default function AuditJournal() {
  const toast = useToast();
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await auditApi.list({ action: actionFilter || undefined, limit: 200 });
      setEntries(data.items || []);
    } catch {
      toast.error('Erreur chargement journal audit');
    } finally {
      setLoading(false);
    }
  }, [actionFilter, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const columns = [
    {
      key: 'created_at',
      header: 'Date',
      render: (r) => (r.created_at ? new Date(r.created_at).toLocaleString('fr-FR') : '—'),
    },
    { key: 'action', header: 'Action' },
    { key: 'utilisateur', header: 'Utilisateur', render: (r) => r.utilisateur || r.email || '—' },
    { key: 'table_cible', header: 'Cible', render: (r) => r.table_cible || '—' },
    {
      key: 'details',
      header: 'Détails',
      render: (r) =>
        r.details ? (
          <span className="text-xs text-texte-secondaire">{JSON.stringify(r.details).slice(0, 80)}</span>
        ) : (
          '—'
        ),
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Journal d'audit</h1>
        <p className="page-subtitle">Traçabilité des actions sensibles</p>
      </div>

      <Table
        columns={columns}
        data={entries}
        loading={loading}
        filters={
          <input
            className="input w-auto"
            placeholder="Filtrer par action (ex. CONNEXION)"
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
          />
        }
        emptyMessage="Aucune entrée"
      />
    </div>
  );
}
