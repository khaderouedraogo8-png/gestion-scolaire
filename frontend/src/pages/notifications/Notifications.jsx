import { useCallback, useEffect, useState } from 'react';
import { notificationsApi } from '../../services/api/notifications';
import { elevesApi } from '../../services/api/eleves';
import Table from '../../components/Table';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';

const STATUT_OPTIONS = [
  { value: '', label: 'Tous les statuts' },
  { value: 'en_attente', label: 'En attente' },
  { value: 'envoye', label: 'Envoyé' },
  { value: 'echec', label: 'Échec' },
];

function StatutBadge({ statut }) {
  const map = {
    en_attente: 'badge-warning',
    envoye: 'badge-success',
    echec: 'badge-danger',
  };
  const labels = {
    en_attente: 'En attente',
    envoye: 'Envoyé',
    echec: 'Échec',
  };
  return <span className={map[statut] || 'badge-neutral'}>{labels[statut] || statut || '—'}</span>;
}

export default function Notifications() {
  const toast = useToast();
  const { isAdmin } = useAuth();

  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statutFilter, setStatutFilter] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');
  const [eleves, setEleves] = useState([]);
  const [form, setForm] = useState({
    id_eleve: '',
    canal: 'email',
    type_notification: 'information',
    contenu: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await notificationsApi.list({
        statut: statutFilter || undefined,
      });
      setNotifications(data.items || data || []);
    } catch {
      toast.error('Erreur lors du chargement des notifications');
    } finally {
      setLoading(false);
    }
  }, [statutFilter, toast]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (search.length < 2) {
      setEleves([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const data = await elevesApi.list({ q: search, per_page: 10 });
        setEleves(data.items || data.eleves || data || []);
      } catch {
        /* ignore */
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!form.contenu.trim()) {
      toast.error('Le contenu est requis');
      return;
    }
    setSaving(true);
    try {
      await notificationsApi.send({
        id_eleve: form.id_eleve || undefined,
        canal: form.canal,
        type_notification: form.type_notification,
        contenu: form.contenu,
      });
      toast.success('Notification ajoutée à la file d\'envoi');
      setModalOpen(false);
      setForm({ id_eleve: '', canal: 'email', type_notification: 'information', contenu: '' });
      setSearch('');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur lors de l\'envoi');
    } finally {
      setSaving(false);
    }
  };

  const handleRetry = async (id) => {
    try {
      await notificationsApi.retry(id);
      toast.success('Nouvelle tentative programmée');
      load();
    } catch {
      toast.error('Erreur lors de la relance');
    }
  };

  const columns = [
    {
      key: 'date',
      header: 'Date',
      render: (r) => r.created_at?.slice(0, 16).replace('T', ' ') || '—',
    },
    { key: 'canal', header: 'Canal', render: (r) => (r.canal === 'sms' ? 'SMS' : 'Email') },
    { key: 'type', header: 'Type', render: (r) => r.type_notification || '—' },
    {
      key: 'contenu',
      header: 'Contenu',
      render: (r) => (
        <span className="max-w-xs truncate block" title={r.contenu}>
          {r.contenu || '—'}
        </span>
      ),
    },
    {
      key: 'statut',
      header: 'Statut',
      render: (r) => <StatutBadge statut={r.statut} />,
    },
    {
      key: 'tentatives',
      header: 'Tentatives',
      render: (r) => r.tentative_count ?? 0,
    },
    {
      key: 'actions',
      header: '',
      render: (r) =>
        r.statut === 'echec' ? (
          <button
            type="button"
            onClick={() => handleRetry(r.id)}
            className="text-sm font-medium text-primary-600 hover:underline"
          >
            Relancer
          </button>
        ) : null,
    },
  ];

  const pendingCount = notifications.filter((n) => n.statut === 'en_attente').length;
  const failedCount = notifications.filter((n) => n.statut === 'echec').length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Notifications</h1>
          <p className="text-sm text-slate-500">File d'envoi SMS et email aux parents</p>
        </div>
        {isAdmin && (
          <button
            type="button"
            onClick={async () => {
              try {
                const r = await notificationsApi.traiterFile();
                toast.success(r.message || 'File traitée');
                load();
              } catch {
                toast.error('Erreur traitement file');
              }
            }}
            className="btn-secondary"
          >
            Traiter la file
          </button>
        )}
        <button type="button" onClick={() => setModalOpen(true)} className="btn-primary">
          + Nouvelle notification
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="card">
          <p className="text-sm text-slate-500">Total affiché</p>
          <p className="text-2xl font-bold text-slate-900">{notifications.length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-slate-500">En attente</p>
          <p className="text-2xl font-bold text-amber-600">{pendingCount}</p>
        </div>
        <div className="card">
          <p className="text-sm text-slate-500">Échecs</p>
          <p className="text-2xl font-bold text-red-600">{failedCount}</p>
        </div>
      </div>

      <Table
        columns={columns}
        data={notifications}
        loading={loading}
        filters={
          <select
            value={statutFilter}
            onChange={(e) => setStatutFilter(e.target.value)}
            className="input w-auto"
          >
            {STATUT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        }
        emptyMessage="Aucune notification dans la file"
      />

      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Nouvelle notification"
        size="lg"
        footer={
          <>
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary">
              Annuler
            </button>
            <button type="submit" form="notif-form" disabled={saving} className="btn-primary">
              {saving ? 'Envoi...' : 'Ajouter à la file'}
            </button>
          </>
        }
      >
        <form id="notif-form" onSubmit={handleSend} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              label="Canal"
              name="canal"
              type="select"
              value={form.canal}
              onChange={(e) => setForm({ ...form, canal: e.target.value })}
              options={[
                { value: 'email', label: 'Email' },
                { value: 'sms', label: 'SMS' },
              ]}
            />
            <FormField
              label="Type"
              name="type_notification"
              type="select"
              value={form.type_notification}
              onChange={(e) => setForm({ ...form, type_notification: e.target.value })}
              options={[
                { value: 'information', label: 'Information' },
                { value: 'absence', label: 'Absence' },
                { value: 'paiement', label: 'Paiement' },
                { value: 'retard_paiement', label: 'Retard paiement' },
                { value: 'discipline', label: 'Discipline' },
                { value: 'notes', label: 'Notes / Bulletins' },
              ]}
            />
          </div>
          <div className="relative">
            <FormField
              label="Élève concerné (optionnel)"
              name="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Rechercher un élève..."
            />
            {eleves.length > 0 && (
              <ul className="absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-lg border border-slate-200 bg-white shadow-lg">
                {eleves.map((el) => (
                  <li key={el.id}>
                    <button
                      type="button"
                      onClick={() => {
                        setForm({ ...form, id_eleve: el.id });
                        setSearch(`${el.prenom} ${el.nom}`);
                        setEleves([]);
                      }}
                      className="w-full px-4 py-2 text-left text-sm hover:bg-slate-50"
                    >
                      <span className="font-medium">{el.prenom} {el.nom}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <FormField
            label="Message"
            name="contenu"
            type="textarea"
            value={form.contenu}
            onChange={(e) => setForm({ ...form, contenu: e.target.value })}
            required
            rows={4}
            placeholder="Contenu du message à envoyer aux parents..."
          />
        </form>
      </Modal>
    </div>
  );
}
