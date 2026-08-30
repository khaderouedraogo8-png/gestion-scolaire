import { useCallback, useEffect, useState } from 'react';
import { emptyIcons } from '../../utils/emptyIcons';
import { absencesApi } from '../../services/api/absences';
import { elevesApi } from '../../services/api/eleves';
import Table from '../../components/Table';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';

const TYPE_OPTIONS = [
  { value: 'absence', label: 'Absence' },
  { value: 'retard', label: 'Retard' },
];

function JustifBadge({ justifiee }) {
  return justifiee ? (
    <span className="badge-success">Justifiée</span>
  ) : (
    <span className="badge-warning">Non justifiée</span>
  );
}

export default function Absences() {
  const toast = useToast();
  const { isAdmin, isSecretariat, isEnseignant } = useAuth();
  const canWrite = isAdmin || isSecretariat || isEnseignant;

  const [absences, setAbsences] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dateDebut, setDateDebut] = useState('');
  const [dateFin, setDateFin] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [justifyModal, setJustifyModal] = useState(null);
  const [motif, setMotif] = useState('');
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');
  const [eleves, setEleves] = useState([]);
  const [eleveSearch, setEleveSearch] = useState('');
  const [form, setForm] = useState({
    id_eleve: '',
    date_absence: new Date().toISOString().slice(0, 10),
    type_absence: 'absence',
    motif: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await absencesApi.list({
        date_debut: dateDebut || undefined,
        date_fin: dateFin || undefined,
      });
      let items = data.items || data || [];
      if (search) {
        const q = search.toLowerCase();
        items = items.filter(
          (a) =>
            `${a.eleve?.prenom || ''} ${a.eleve?.nom || ''}`.toLowerCase().includes(q) ||
            (a.eleve?.matricule || '').toLowerCase().includes(q)
        );
      }
      setAbsences(items);
    } catch {
      toast.error('Erreur lors du chargement des absences');
    } finally {
      setLoading(false);
    }
  }, [dateDebut, dateFin, search, toast]);

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
        const data = await elevesApi.list({ q: eleveSearch, statut: 'inscrit', per_page: 10 });
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
      await absencesApi.create({
        id_eleve: form.id_eleve,
        date_absence: form.date_absence,
        type_absence: form.type_absence,
        motif: form.motif || undefined,
      });
      toast.success('Absence enregistrée');
      setModalOpen(false);
      setForm({
        id_eleve: '',
        date_absence: new Date().toISOString().slice(0, 10),
        type_absence: 'absence',
        motif: '',
      });
      setSearch('');
      setEleveSearch('');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur lors de l\'enregistrement');
    } finally {
      setSaving(false);
    }
  };

  const handleJustify = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await absencesApi.justifier(justifyModal.id, { motif, justifiee: true });
      toast.success('Absence justifiée');
      setJustifyModal(null);
      setMotif('');
      load();
    } catch {
      toast.error('Erreur lors de la justification');
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
    { key: 'date', header: 'Date', render: (r) => r.date_absence || '—' },
    {
      key: 'type',
      header: 'Type',
      render: (r) => (r.type_absence === 'retard' ? 'Retard' : 'Absence'),
    },
    { key: 'motif', header: 'Motif', render: (r) => r.motif || '—' },
    {
      key: 'justifiee',
      header: 'Statut',
      render: (r) => <JustifBadge justifiee={r.justifiee} />,
    },
    {
      key: 'actions',
      header: '',
      render: (r) =>
        canWrite && !r.justifiee ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setJustifyModal(r);
            }}
            className="text-sm font-medium text-or-cachet hover:text-or-cachet/80"
          >
            Justifier
          </button>
        ) : null,
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Vie scolaire"
        title="Absences"
        subtitle="Suivi des absences et retards"
        actions={
          canWrite && (
            <button type="button" onClick={() => setModalOpen(true)} className="btn-primary">
              + Signaler une absence
            </button>
          )
        }
      />

      <Table
        columns={columns}
        data={absences}
        loading={loading}
        searchable
        searchPlaceholder="Filtrer par nom ou matricule..."
        onSearch={setSearch}
        filters={
          <>
            <input
              type="date"
              value={dateDebut}
              onChange={(e) => setDateDebut(e.target.value)}
              className="input w-auto"
              placeholder="Du"
            />
            <input
              type="date"
              value={dateFin}
              onChange={(e) => setDateFin(e.target.value)}
              className="input w-auto"
              placeholder="Au"
            />
          </>
        }
        emptyIcon={emptyIcons.absences}
        emptyMessage="Aucune absence enregistrée pour l'instant sur cette période"
      />

      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Signaler une absence"
        footer={
          <>
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary">
              Annuler
            </button>
            <button type="submit" form="abs-form" disabled={saving} className="btn-primary">
              {saving ? 'Enregistrement...' : 'Enregistrer'}
            </button>
          </>
        }
      >
        <form id="abs-form" onSubmit={handleCreate} className="space-y-4">
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
          <FormField
            label="Date"
            name="date_absence"
            type="date"
            value={form.date_absence}
            onChange={(e) => setForm({ ...form, date_absence: e.target.value })}
            required
          />
          <FormField
            label="Type"
            name="type_absence"
            type="select"
            value={form.type_absence}
            onChange={(e) => setForm({ ...form, type_absence: e.target.value })}
            options={TYPE_OPTIONS}
          />
          <FormField
            label="Motif (optionnel)"
            name="motif"
            type="textarea"
            value={form.motif}
            onChange={(e) => setForm({ ...form, motif: e.target.value })}
            rows={2}
          />
        </form>
      </Modal>

      <Modal
        isOpen={Boolean(justifyModal)}
        onClose={() => setJustifyModal(null)}
        title="Justifier l'absence"
        footer={
          <>
            <button type="button" onClick={() => setJustifyModal(null)} className="btn-secondary">
              Annuler
            </button>
            <button type="submit" form="just-form" disabled={saving} className="btn-primary">
              {saving ? 'Enregistrement...' : 'Confirmer'}
            </button>
          </>
        }
      >
        <form id="just-form" onSubmit={handleJustify} className="space-y-4">
          <p className="text-sm text-texte-secondaire">
            Absence du {justifyModal?.date_absence} —{' '}
            {justifyModal?.eleve?.prenom || justifyModal?.prenom}{' '}
            {justifyModal?.eleve?.nom || justifyModal?.nom}
          </p>
          <FormField
            label="Motif de justification"
            name="motif"
            type="textarea"
            value={motif}
            onChange={(e) => setMotif(e.target.value)}
            required
            rows={3}
          />
        </form>
      </Modal>
    </div>
  );
}
