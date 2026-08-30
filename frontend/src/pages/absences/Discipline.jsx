import { useCallback, useEffect, useState } from 'react';
import { absencesApi } from '../../services/api/absences';
import { elevesApi } from '../../services/api/eleves';
import Table from '../../components/Table';
import { emptyIcons } from '../../utils/emptyIcons';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';

const TYPE_INCIDENT_OPTIONS = [
  { value: 'avertissement', label: 'Avertissement' },
  { value: 'blame', label: 'Blâme' },
  { value: 'exclusion_temporaire', label: 'Exclusion temporaire' },
];

function IncidentBadge({ type }) {
  const map = {
    avertissement: 'badge-warning',
    blame: 'badge-danger',
    exclusion_temporaire: 'badge-danger',
  };
  const labels = {
    avertissement: 'Avertissement',
    blame: 'Blâme',
    exclusion_temporaire: 'Exclusion temp.',
  };
  return <span className={map[type] || 'badge-neutral'}>{labels[type] || type || '—'}</span>;
}

export default function Discipline() {
  const toast = useToast();
  const { isAdmin, isSecretariat, isEnseignant } = useAuth();
  const canWrite = isAdmin || isSecretariat || isEnseignant;

  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [eleveSearch, setEleveSearch] = useState('');
  const [eleves, setEleves] = useState([]);
  const [form, setForm] = useState({
    id_eleve: '',
    type_incident: 'avertissement',
    date_incident: new Date().toISOString().slice(0, 10),
    description: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await absencesApi.listDiscipline();
      let items = data.items || data || [];
      if (search) {
        const q = search.toLowerCase();
        items = items.filter(
          (i) =>
            `${i.eleve?.prenom || ''} ${i.eleve?.nom || ''}`.toLowerCase().includes(q) ||
            (i.description || '').toLowerCase().includes(q)
        );
      }
      setIncidents(items);
    } catch {
      toast.error('Erreur lors du chargement des incidents');
    } finally {
      setLoading(false);
    }
  }, [search, toast]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (eleveSearch.length < 2) {
      setEleves([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const data = await elevesApi.list({ q: eleveSearch, per_page: 10 });
        setEleves(data.items || data.eleves || data || []);
      } catch {
        /* ignore */
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [eleveSearch]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.id_eleve) {
      toast.error('Veuillez sélectionner un élève');
      return;
    }
    setSaving(true);
    try {
      await absencesApi.createIncident({
        id_eleve: form.id_eleve,
        type_incident: form.type_incident,
        date_incident: form.date_incident,
        description: form.description || undefined,
      });
      toast.success('Incident enregistré');
      setModalOpen(false);
      setForm({
        id_eleve: '',
        type_incident: 'avertissement',
        date_incident: new Date().toISOString().slice(0, 10),
        description: '',
      });
      setEleveSearch('');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur lors de l\'enregistrement');
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    {
      key: 'eleve',
      header: 'Élève',
      render: (r) => (
        <div>
          <p className="font-medium">
            {r.eleve?.prenom || r.prenom} {r.eleve?.nom || r.nom}
          </p>
          <p className="text-xs text-texte-secondaire">{r.eleve?.matricule || r.matricule || '—'}</p>
        </div>
      ),
    },
    { key: 'date', header: 'Date', render: (r) => r.date_incident || '—' },
    {
      key: 'type',
      header: 'Type',
      render: (r) => <IncidentBadge type={r.type_incident} />,
    },
    {
      key: 'description',
      header: 'Description',
      render: (r) => (
        <span className="max-w-xs truncate block" title={r.description}>
          {r.description || '—'}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Vie scolaire"
        title="Discipline"
        subtitle="Incidents disciplinaires et sanctions"
        actions={
          canWrite && (
            <button type="button" onClick={() => setModalOpen(true)} className="btn-primary">
              + Déclarer un incident
            </button>
          )
        }
      />

      <Table
        columns={columns}
        data={incidents}
        loading={loading}
        searchable
        searchPlaceholder="Rechercher par élève ou description..."
        onSearch={setSearch}
        emptyIcon={emptyIcons.discipline}
        emptyMessage="Aucun incident disciplinaire pour l'instant"
      />

      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Déclarer un incident"
        size="lg"
        footer={
          <>
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary">
              Annuler
            </button>
            <button type="submit" form="inc-form" disabled={saving} className="btn-primary">
              {saving ? 'Enregistrement...' : 'Enregistrer'}
            </button>
          </>
        }
      >
        <form id="inc-form" onSubmit={handleCreate} className="space-y-4">
          <div className="relative">
            <FormField
              label="Rechercher un élève"
              name="search_eleve"
              value={eleveSearch}
              onChange={(e) => setEleveSearch(e.target.value)}
              placeholder="Nom, prénom ou matricule..."
            />
            {eleves.length > 0 && (
              <ul className="absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-lg border border-bordure bg-blanc ">
                {eleves.map((el) => (
                  <li key={el.id}>
                    <button
                      type="button"
                      onClick={() => {
                        setForm({ ...form, id_eleve: el.id });
                        setEleveSearch(`${el.prenom} ${el.nom}`);
                        setEleves([]);
                      }}
                      className="w-full px-4 py-2 text-left text-sm hover:bg-craie"
                    >
                      <span className="font-medium">{el.prenom} {el.nom}</span>
                      <span className="ml-2 text-texte-secondaire">{el.matricule}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              label="Date de l'incident"
              name="date_incident"
              type="date"
              value={form.date_incident}
              onChange={(e) => setForm({ ...form, date_incident: e.target.value })}
              required
            />
            <FormField
              label="Type d'incident"
              name="type_incident"
              type="select"
              value={form.type_incident}
              onChange={(e) => setForm({ ...form, type_incident: e.target.value })}
              options={TYPE_INCIDENT_OPTIONS}
            />
          </div>
          <FormField
            label="Description"
            name="description"
            type="textarea"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            rows={4}
            placeholder="Décrire les faits et le contexte..."
          />
        </form>
      </Modal>
    </div>
  );
}
