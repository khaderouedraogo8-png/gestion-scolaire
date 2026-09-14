import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Calendar } from 'lucide-react';
import { emploiApi } from '../../services/api/emploi';
import { configApi } from '../../services/api/config';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import PageHeader from '../../components/PageHeader';
import EmptyState from '../../components/EmptyState';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';

const JOURS = [
  { value: '1', label: 'Lundi' },
  { value: '2', label: 'Mardi' },
  { value: '3', label: 'Mercredi' },
  { value: '4', label: 'Jeudi' },
  { value: '5', label: 'Vendredi' },
];

const HOUR_START = 7;
const HOUR_END = 18;
const SLOT_MINUTES = 60;

const emptyForm = {
  id_affectation: '',
  id_salle: '',
  jour_semaine: '1',
  heure_debut: '08:00',
  heure_fin: '10:00',
};

function parseTime(t) {
  if (!t) return 0;
  const [h, m] = String(t).slice(0, 5).split(':').map(Number);
  return (h || 0) * 60 + (m || 0);
}

function formatHour(minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

export default function EmploiTemps() {
  const toast = useToast();
  const { isAdmin } = useAuth();
  const [creneaux, setCreneaux] = useState([]);
  const [classes, setClasses] = useState([]);
  const [affectations, setAffectations] = useState([]);
  const [salles, setSalles] = useState([]);
  const [classeFilter, setClasseFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [view, setView] = useState('grille');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await emploiApi.listCreneaux({
        id_classe: classeFilter || undefined,
      });
      setCreneaux(Array.isArray(data) ? data : data.items || []);
    } catch {
      toast.error('Erreur chargement emploi du temps');
    } finally {
      setLoading(false);
    }
  }, [classeFilter, toast]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    Promise.all([
      configApi.listClasses(),
      emploiApi.listAffectations(),
      emploiApi.listSalles(),
    ]).then(([cls, aff, sal]) => {
      setClasses(cls.items || cls || []);
      setAffectations(aff.items || aff || []);
      setSalles(Array.isArray(sal) ? sal : sal.items || []);
    });
  }, []);

  const timeRows = useMemo(() => {
    const rows = [];
    for (let m = HOUR_START * 60; m < HOUR_END * 60; m += SLOT_MINUTES) {
      rows.push(m);
    }
    return rows;
  }, []);

  const openCreate = () => {
    setEditId(null);
    setForm(emptyForm);
    setModalOpen(true);
  };

  const openEdit = (c) => {
    setEditId(c.id);
    setForm({
      id_affectation: String(c.id_affectation),
      id_salle: c.id_salle ? String(c.id_salle) : '',
      jour_semaine: String(c.jour_semaine),
      heure_debut: c.heure_debut?.slice(0, 5) || '08:00',
      heure_fin: c.heure_fin?.slice(0, 5) || '10:00',
    });
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = {
      id_affectation: form.id_affectation,
      id_salle: form.id_salle || null,
      jour_semaine: Number(form.jour_semaine),
      heure_debut: form.heure_debut,
      heure_fin: form.heure_fin,
    };
    try {
      if (editId) {
        await emploiApi.updateCreneau(editId, payload);
        toast.success('Créneau mis à jour');
      } else {
        await emploiApi.createCreneau(payload);
        toast.success('Créneau ajouté');
      }
      setModalOpen(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Supprimer ce créneau ?')) return;
    try {
      await emploiApi.deleteCreneau(id);
      toast.success('Créneau supprimé');
      load();
    } catch {
      toast.error('Erreur suppression');
    }
  };

  const creneauxForCell = (jour, slotStart) => {
    const slotEnd = slotStart + SLOT_MINUTES;
    return creneaux.filter((c) => {
      if (Number(c.jour_semaine) !== Number(jour)) return false;
      const start = parseTime(c.heure_debut);
      const end = parseTime(c.heure_fin);
      return start < slotEnd && end > slotStart;
    });
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-32">
        <div className="loading-ring" />
        <p className="text-sm text-texte-secondaire">Chargement de l’emploi du temps…</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Emploi du temps"
        title="Emploi du temps"
        subtitle="Créneaux par classe, matière et enseignant"
        actions={
          <>
            <select
              className="input w-auto"
              value={classeFilter}
              onChange={(e) => setClasseFilter(e.target.value)}
            >
              <option value="">Toutes les classes</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.libelle}
                </option>
              ))}
            </select>
            <div className="inline-flex rounded-input border border-bordure bg-blanc p-0.5">
              <button
                type="button"
                className={`rounded-[5px] px-3 py-1.5 text-xs font-medium transition-colors ${
                  view === 'grille' ? 'bg-or-cachet-clair text-or-cachet' : 'text-texte-secondaire'
                }`}
                onClick={() => setView('grille')}
              >
                Grille
              </button>
              <button
                type="button"
                className={`rounded-[5px] px-3 py-1.5 text-xs font-medium transition-colors ${
                  view === 'liste' ? 'bg-or-cachet-clair text-or-cachet' : 'text-texte-secondaire'
                }`}
                onClick={() => setView('liste')}
              >
                Liste
              </button>
            </div>
            {isAdmin && (
              <button type="button" className="btn-primary" onClick={openCreate}>
                + Créneau
              </button>
            )}
          </>
        }
      />

      {creneaux.length === 0 ? (
        <EmptyState
          icon={Calendar}
          title="Aucun créneau"
          message="Créez d’abord des affectations enseignant–matière–classe, puis planifiez les créneaux."
          actionLabel={isAdmin ? 'Gérer les affectations' : undefined}
          actionHref={isAdmin ? '/emploi/affectations' : undefined}
        />
      ) : view === 'grille' ? (
        <div className="edt-grid-shell">
          <div
            className="edt-grid"
            style={{ gridTemplateColumns: `4.5rem repeat(${JOURS.length}, minmax(7.5rem, 1fr))` }}
          >
            <div className="edt-grid-corner" />
            {JOURS.map((j) => (
              <div key={j.value} className="edt-grid-day">
                {j.label}
              </div>
            ))}
            {timeRows.map((slot) => (
              <div key={slot} className="contents">
                <div className="edt-grid-time">{formatHour(slot)}</div>
                {JOURS.map((j) => {
                  const items = creneauxForCell(j.value, slot);
                  return (
                    <div key={`${j.value}-${slot}`} className="edt-grid-cell">
                      {items.map((c) => (
                        <button
                          key={c.id}
                          type="button"
                          className="edt-slot"
                          onClick={() => (isAdmin ? openEdit(c) : undefined)}
                          title={`${c.matiere_nom || 'Matière'} — ${c.enseignant_nom || ''}`}
                        >
                          <span className="edt-slot-title">{c.matiere_nom || 'Matière'}</span>
                          <span className="edt-slot-meta">
                            {(c.heure_debut || '').slice(0, 5)}–{(c.heure_fin || '').slice(0, 5)}
                          </span>
                          {!classeFilter && c.classe_nom && (
                            <span className="edt-slot-meta">{c.classe_nom}</span>
                          )}
                          {c.salle_libelle && (
                            <span className="edt-slot-meta">{c.salle_libelle}</span>
                          )}
                        </button>
                      ))}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="overflow-hidden rounded-card border border-bordure bg-blanc">
          <table className="min-w-full divide-y divide-bordure">
            <thead className="bg-craie">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase">Jour</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase">Horaire</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase">Matière</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase">Classe</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase">Enseignant</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase">Salle</th>
                {isAdmin && <th className="px-4 py-3" />}
              </tr>
            </thead>
            <tbody className="divide-y divide-bordure/50">
              {creneaux.map((c) => (
                <tr key={c.id}>
                  <td className="px-4 py-3 text-sm">{c.jour_libelle}</td>
                  <td className="px-4 py-3 text-sm">
                    {c.heure_debut} — {c.heure_fin}
                  </td>
                  <td className="px-4 py-3 text-sm">{c.matiere_nom || '—'}</td>
                  <td className="px-4 py-3 text-sm">{c.classe_nom || '—'}</td>
                  <td className="px-4 py-3 text-sm">{c.enseignant_nom || '—'}</td>
                  <td className="px-4 py-3 text-sm">{c.salle_libelle || '—'}</td>
                  {isAdmin && (
                    <td className="space-x-2 px-4 py-3 text-right text-sm">
                      <button
                        type="button"
                        onClick={() => openEdit(c)}
                        className="text-or-cachet hover:underline"
                      >
                        Modifier
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(c.id)}
                        className="text-brique hover:underline"
                      >
                        Suppr.
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {creneaux.length > 0 && isAdmin && view === 'grille' && (
        <p className="text-xs text-texte-secondaire">
          Astuce : cliquez un créneau pour le modifier. Besoin d’affectations ?{' '}
          <Link to="/emploi/affectations" className="font-medium text-or-cachet hover:underline">
            Gérer les affectations
          </Link>
        </p>
      )}

      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editId ? 'Modifier le créneau' : 'Nouveau créneau'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField
            label="Affectation"
            name="id_affectation"
            type="select"
            value={form.id_affectation}
            onChange={(e) => setForm({ ...form, id_affectation: e.target.value })}
            required
            options={affectations.map((a) => ({
              value: String(a.id),
              label: `${a.matiere_nom || a.matiere?.libelle} — ${a.classe_nom || a.classe?.libelle} (${a.enseignant_nom || ''})`,
            }))}
          />
          <FormField
            label="Salle"
            name="id_salle"
            type="select"
            value={form.id_salle}
            onChange={(e) => setForm({ ...form, id_salle: e.target.value })}
            options={[
              { value: '', label: '—' },
              ...salles.map((s) => ({ value: String(s.id), label: s.libelle })),
            ]}
          />
          <FormField
            label="Jour"
            name="jour_semaine"
            type="select"
            value={form.jour_semaine}
            onChange={(e) => setForm({ ...form, jour_semaine: e.target.value })}
            options={JOURS}
          />
          <div className="grid grid-cols-2 gap-4">
            <FormField
              label="Heure début"
              type="time"
              value={form.heure_debut}
              onChange={(e) => setForm({ ...form, heure_debut: e.target.value })}
              required
            />
            <FormField
              label="Heure fin"
              type="time"
              value={form.heure_fin}
              onChange={(e) => setForm({ ...form, heure_fin: e.target.value })}
              required
            />
          </div>
          {editId && (
            <button
              type="button"
              className="btn-danger w-full"
              onClick={() => {
                setModalOpen(false);
                handleDelete(editId);
              }}
            >
              Supprimer ce créneau
            </button>
          )}
          <button type="submit" className="btn-primary w-full">
            Enregistrer
          </button>
        </form>
      </Modal>
    </div>
  );
}
