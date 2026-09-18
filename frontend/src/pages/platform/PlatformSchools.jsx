import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Building2 } from 'lucide-react';
import { platformApi } from '../../services/api/platform';
import PageHeader from '../../components/PageHeader';
import Table from '../../components/Table';
import { useToast } from '../../components/Toast';
import { useAuthStore } from '../../store/authStore';

export default function PlatformSchools() {
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;
  const navigate = useNavigate();
  const enterSchoolContext = useAuthStore((s) => s.enterSchoolContext);
  const exitSchoolContext = useAuthStore((s) => s.exitSchoolContext);
  const actingSchoolId = useAuthStore((s) => s.actingSchoolId);
  const currentSchool = useAuthStore((s) => s.currentSchool);

  const [schools, setSchools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const data = await platformApi.listSchools({ q: q || undefined });
      setSchools(Array.isArray(data) ? data : data.items || []);
    } catch {
      toastRef.current.error('Impossible de charger les écoles.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggleActive = async (school) => {
    try {
      if (school.is_active) {
        await platformApi.deactivateSchool(school.id);
        toast.success(`École ${school.code} désactivée`);
      } else {
        await platformApi.activateSchool(school.id);
        toast.success(`École ${school.code} activée`);
      }
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Action impossible');
    }
  };

  const switchInto = async (school) => {
    try {
      await enterSchoolContext(school.id);
      toast.success(`Contexte : ${school.name}`);
      navigate('/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Impossible d’entrer dans le contexte');
    }
  };

  const exitContext = async () => {
    try {
      await exitSchoolContext();
      toast.success('Retour au contexte plateforme');
    } catch {
      toast.error('Impossible de quitter le contexte');
    }
  };

  const columns = [
    { key: 'code', header: 'Code' },
    { key: 'name', header: 'Nom' },
    {
      key: 'is_active',
      header: 'Statut',
      render: (s) => (s.is_active ? 'Active' : 'Inactive'),
    },
    {
      key: 'plan_code',
      header: 'Plan',
      render: (s) => s.plan_code || '—',
    },
    {
      key: 'subscription_status',
      header: 'Abo',
      render: (s) => s.subscription_status || '—',
    },
    { key: 'users_count', header: 'Users' },
    { key: 'eleves_count', header: 'Élèves' },
    {
      key: 'actions',
      header: '',
      render: (s) => (
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-ghost text-sm" onClick={() => switchInto(s)}>
            Entrer
          </button>
          <button type="button" className="btn-ghost text-sm" onClick={() => toggleActive(s)}>
            {s.is_active ? 'Désactiver' : 'Activer'}
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Écoles (plateforme)"
        subtitle="Gestion centralisée SUPER_ADMIN — onboarding, activation, contexte"
        actions={
          <div className="flex flex-wrap gap-2">
            {actingSchoolId && (
              <button type="button" className="btn-secondary" onClick={exitContext}>
                Quitter {currentSchool?.code || 'contexte'}
              </button>
            )}
            <Link to="/platform/onboarding" className="btn-primary">
              Nouvelle école
            </Link>
          </div>
        }
      />

      <form
        className="flex flex-wrap gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          load();
        }}
      >
        <input
          className="input max-w-sm"
          placeholder="Rechercher nom ou code…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <button type="submit" className="btn-secondary">
          Filtrer
        </button>
      </form>

      <Table
        loading={loading}
        emptyIcon={Building2}
        emptyMessage="Aucune école — créez-en une via l’onboarding."
        columns={columns}
        data={schools}
      />
    </div>
  );
}
