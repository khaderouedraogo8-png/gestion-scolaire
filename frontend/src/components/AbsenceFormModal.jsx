import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { elevesApi } from '../services/api/eleves';
import { absencesApi } from '../services/api/absences';
import FormField from './FormField';
import { useToast } from './Toast';
import { cycleLabel } from '../utils/classNavigation';

const TYPE_OPTIONS = [
  { value: 'absence', label: 'Absence' },
  { value: 'retard', label: 'Retard' },
];

export default function AbsenceFormModal({ isOpen, onClose, onCreated }) {
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;

  const [saving, setSaving] = useState(false);
  const [eleves, setEleves] = useState([]);
  const [eleveSearch, setEleveSearch] = useState('');
  const [selectedEleve, setSelectedEleve] = useState(null);
  const [form, setForm] = useState({
    date_absence: new Date().toISOString().slice(0, 10),
    type_absence: 'absence',
    motif: '',
  });

  useEffect(() => {
    if (!isOpen) return;
    setSelectedEleve(null);
    setEleveSearch('');
    setEleves([]);
    setForm({
      date_absence: new Date().toISOString().slice(0, 10),
      type_absence: 'absence',
      motif: '',
    });
  }, [isOpen]);

  useEffect(() => {
    if (eleveSearch.length < 2) {
      setEleves([]);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const data = await elevesApi.list({ q: eleveSearch, statut: 'inscrit', per_page: 10 });
        if (!cancelled) setEleves(data.items || data || []);
      } catch {
        /* ignore */
      }
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [eleveSearch]);

  const handleSelect = (el) => {
    setSelectedEleve(el);
    setEleveSearch(`${el.prenom} ${el.nom} — ${el.matricule} — ${el.classe_nom || ''}`);
    setEleves([]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedEleve?.id) {
      toast.error('Veuillez sélectionner un élève dans la liste');
      return;
    }
    setSaving(true);
    try {
      await absencesApi.create({
        id_eleve: selectedEleve.id,
        date_absence: form.date_absence,
        type_absence: form.type_absence,
        motif: form.motif || undefined,
      });
      toast.success('Absence enregistrée');
      onCreated?.();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.message || "Erreur lors de l'enregistrement");
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-encre/50" onClick={onClose} aria-hidden="true" />
      <div className="relative w-full max-w-lg rounded-card border border-bordure bg-blanc p-6">
        <h2 className="page-title mb-4">Signaler une absence</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <label className="label" htmlFor="absence-eleve-search">
              Rechercher un élève (nom ou matricule)
            </label>
            <input
              id="absence-eleve-search"
              className="input"
              value={eleveSearch}
              onChange={(e) => {
                setEleveSearch(e.target.value);
                setSelectedEleve(null);
              }}
              placeholder="Nom, prénom ou matricule…"
              autoComplete="off"
            />
            {eleves.length > 0 && (
              <ul className="absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-input border border-bordure bg-blanc">
                {eleves.map((el) => (
                  <li key={el.id}>
                    <button
                      type="button"
                      className="w-full px-3 py-2 text-left text-sm hover:bg-craie"
                      onClick={() => handleSelect(el)}
                    >
                      {el.prenom} {el.nom} — {el.matricule} — {el.classe_nom || '—'}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {selectedEleve && (
            <div className="rounded-input border border-bordure bg-craie px-3 py-2 text-sm">
              <p>
                <span className="text-texte-secondaire">Classe :</span>{' '}
                <strong>{selectedEleve.classe_nom || '—'}</strong>
              </p>
              <p>
                <span className="text-texte-secondaire">Cycle :</span>{' '}
                <strong>{cycleLabel(selectedEleve.cycle)}</strong>
              </p>
            </div>
          )}

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
            value={form.motif}
            onChange={(e) => setForm({ ...form, motif: e.target.value })}
          />

          <div className="flex gap-3 pt-2">
            <button type="button" className="btn-secondary flex-1" onClick={onClose}>
              Annuler
            </button>
            <button type="submit" disabled={saving} className="btn-primary flex-1">
              {saving ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
