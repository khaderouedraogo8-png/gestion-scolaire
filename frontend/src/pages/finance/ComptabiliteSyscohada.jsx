import { useCallback, useEffect, useState } from 'react';
import { BookOpen } from 'lucide-react';
import { financeApi } from '../../services/api/finance';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import EmptyState from '../../components/EmptyState';
import { useToast } from '../../components/Toast';

export default function ComptabiliteSyscohada() {
  const toast = useToast();
  const [comptes, setComptes] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await financeApi.getSyscohadaPlan();
      const list = Array.isArray(data) ? data : data.items || data.comptes || [];
      setComptes(list);
    } catch {
      toast.error('Impossible de charger le plan comptable');
      setComptes([]);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const columns = [
    { key: 'numero', header: 'N° compte', render: (r) => r.numero || r.code || '—' },
    { key: 'libelle', header: 'Libellé', render: (r) => r.libelle || r.intitule || '—' },
    {
      key: 'classe',
      header: 'Classe',
      render: (r) => r.classe ?? r.classe_compte ?? '—',
    },
    {
      key: 'type',
      header: 'Type',
      render: (r) => r.type_compte || r.type || '—',
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Finance"
        title="Plan comptable SYSCOHADA"
        subtitle="Référentiel comptable — lecture seule"
      />

      {!loading && comptes.length === 0 && (
        <div className="rounded-lg border border-ambre/40 bg-ambre-clair/40 px-4 py-3 text-sm text-encre">
          Plan SYSCOHADA skeleton — seed via admin pour initialiser les comptes de base.
        </div>
      )}

      {comptes.length === 0 && !loading ? (
        <div className="card-premium">
          <EmptyState
            icon={BookOpen}
            title="Plan comptable vide"
            message="Le référentiel SYSCOHADA n'a pas encore été initialisé pour cet établissement."
          />
        </div>
      ) : (
        <Table
          columns={columns}
          data={comptes}
          loading={loading}
          emptyIcon={BookOpen}
          emptyMessage="Aucun compte dans le plan SYSCOHADA."
        />
      )}
    </div>
  );
}
