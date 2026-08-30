import { useCallback, useEffect, useRef, useState } from 'react';
import { auditApi } from '../../services/api/audit';
import Table from '../../components/Table';
import { emptyIcons } from '../../utils/emptyIcons';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';

export default function AuditJournal() {
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await auditApi.list({ action: actionFilter || undefined, limit: 200 });
      setEntries(data.items || []);
    } catch {
      toastRef.current.error('Impossible de charger le journal d\'audit. Réessayez.');
    } finally {
      setLoading(false);
    }
  }, [actionFilter]);

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
    <div className="space-y-8">
      <PageHeader
        eyebrow="Configuration"
        title="Journal d'audit"
        subtitle="Traçabilité des actions sensibles"
      />

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
        emptyIcon={emptyIcons.audit}
        emptyMessage="Aucune entrée pour l'instant — ajustez les filtres si besoin."
      />
    </div>
  );
}
