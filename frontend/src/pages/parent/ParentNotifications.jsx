import { useEffect, useState } from 'react';
import { Bell } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import EmptyState from '../../components/EmptyState';
import Card from '../../components/Card';
import Badge from '../../components/Badge';
import { notificationsApi } from '../../services/api/notifications';
import { useToast } from '../../components/Toast';

export default function ParentNotifications() {
  const toast = useToast();
  const [items, setItems] = useState([]);
  const [nonLues, setNonLues] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const data = await notificationsApi.inbox();
      setItems(data.items || []);
      setNonLues(data.non_lues || 0);
    } catch {
      toast.error('Impossible de charger vos notifications.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const markRead = async (id) => {
    try {
      await notificationsApi.markRead(id);
      setItems((prev) =>
        prev.map((n) => (n.id === id ? { ...n, lu: true, lu_le: new Date().toISOString() } : n))
      );
      setNonLues((c) => Math.max(0, c - 1));
    } catch {
      toast.error('Impossible de marquer comme lu.');
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-32">
        <div className="loading-ring" />
        <p className="text-sm text-texte-secondaire">Chargement…</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Espace parent"
        title="Boîte de réception"
        subtitle={nonLues > 0 ? `${nonLues} non lue(s)` : 'Toutes vos notifications'}
      />

      {!items.length ? (
        <EmptyState icon={Bell} message="Aucune notification pour le moment." />
      ) : (
        <div className="space-y-3">
          {items.map((n) => (
            <Card key={n.id} premium className={!n.lu ? 'border-or-cachet/40' : ''}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-display text-sm font-medium text-encre">
                      {n.type_notification || 'Notification'}
                    </span>
                    {!n.lu ? <Badge variant="warning">Non lu</Badge> : <Badge variant="success">Lu</Badge>}
                    <span className="text-xs text-texte-secondaire">{n.canal}</span>
                  </div>
                  <p className="whitespace-pre-wrap text-sm text-texte-secondaire">{n.contenu}</p>
                  <p className="text-xs text-texte-secondaire">
                    {n.created_at ? new Date(n.created_at).toLocaleString('fr-FR') : ''}
                  </p>
                </div>
                {!n.lu && (
                  <button type="button" className="btn-secondary text-xs" onClick={() => markRead(n.id)}>
                    Marquer lu
                  </button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
