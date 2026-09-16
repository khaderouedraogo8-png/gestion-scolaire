import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { configApi } from '../../services/api/config';
import Table from '../../components/Table';
import { emptyIcons } from '../../utils/emptyIcons';
import FormField from '../../components/FormField';
import Modal from '../../components/Modal';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';
import { apiErrorMessage, asList } from '../../utils/academicLabels';

/**
 * Écran legacy — mêmes données que /periodes (façade /trimestres).
 * L’UI canonique est /etablissement/periodes (pas de limite à 3 trimestres).
 */
export default function Trimestres() {
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;

  const [annees, setAnnees] = useState([]);
  const [anneeId, setAnneeId] = useState('');
  const [trimestres, setTrimestres] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [editId, setEditId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    numero: '1',
    date_debut: '',
    date_fin: '',
  });
  const [fieldErrors, setFieldErrors] = useState({});

  useEffect(() => {
    configApi
      .listAnnees()
      .then((data) => {
        const list = asList(data);
        setAnnees(list);
        const active = list.find((a) => a.est_active) || list[0];
        if (active) setAnneeId(String(active.id));
      })
      .catch((err) =>
        toastRef.current.error(apiErrorMessage(err, 'Impossible de charger les années.'))
      );
  }, []);

  const load = useCallback(async () => {
    if (!anneeId) return;
    setLoading(true);
    try {
      const data = await configApi.listTrimestres(anneeId);
      setTrimestres(asList(data));
    } catch (err) {
      toastRef.current.error(apiErrorMessage(err, 'Impossible de charger les trimestres.'));
    } finally {
      setLoading(false);
    }
  }, [anneeId]);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setEditId(null);
    const next =
      trimestres.reduce((max, t) => Math.max(max, Number(t.numero || t.sequence) || 0), 0) + 1;
    setForm({ numero: String(next), date_debut: '', date_fin: '' });
    setFieldErrors({});
    setModal(true);
  };

  const openEdit = (t) => {
    setEditId(t.id);
    setForm({
      numero: String(t.numero ?? t.sequence ?? 1),
      date_debut: t.date_debut,
      date_fin: t.date_fin,
    });
    setFieldErrors({});
    setModal(true);
  };

  const validate = () => {
    const errors = {};
    if (!form.numero || Number(form.numero) < 1) {
      errors.numero = 'Le numéro (séquence) doit être ≥ 1.';
    }
    if (!form.date_debut) errors.date_debut = 'Date de début obligatoire.';
    if (!form.date_fin) errors.date_fin = 'Date de fin obligatoire.';
    if (form.date_debut && form.date_fin && form.date_debut > form.date_fin) {
      errors.date_fin = 'La date de fin doit être postérieure ou égale à la date de début.';
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setSaving(true);
    const payload = {
      id_annee: anneeId,
      numero: Number(form.numero),
      date_debut: form.date_debut,
      date_fin: form.date_fin,
    };
    try {
      if (editId) {
        await configApi.updateTrimestre(editId, payload);
        toast.success('Période mise à jour');
      } else {
        await configApi.createTrimestre(payload);
        toast.success('Période créée');
      }
      setModal(false);
      load();
    } catch (err) {
      toast.error(apiErrorMessage(err, "Erreur lors de l'enregistrement"));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Désactiver cette période (legacy trimestres) ?')) return;
    try {
      await configApi.deleteTrimestre(id);
      toast.success('Période désactivée');
      load();
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Impossible de désactiver cette période'));
    }
  };

  const columns = [
    {
      key: 'numero',
      header: 'Séquence',
      render: (r) => {
        const n = r.numero ?? r.sequence;
        const label = r.label || r.libelle;
        return (
          <div>
            <span className="font-medium">{label || `Période ${n}`}</span>
            <p className="text-xs text-texte-secondaire">n° {n}</p>
          </div>
        );
      },
    },
    { key: 'date_debut', header: 'Début' },
    { key: 'date_fin', header: 'Fin' },
    {
      key: 'actions',
      header: '',
      render: (r) => (
        <div className="space-x-3 text-right">
          <button type="button" onClick={() => openEdit(r)} className="text-or-cachet hover:underline">
            Modifier
          </button>
          <button type="button" onClick={() => handleDelete(r.id)} className="text-brique hover:underline">
            Désactiver
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Configuration · legacy"
        title="Trimestres"
        subtitle="Façade historique sur les périodes académiques (même API métier). Préférez l’écran Périodes."
        actions={
          <>
            <Link to="/etablissement/periodes" className="btn-secondary">
              Ouvrir Périodes
            </Link>
            <select
              className="input w-auto"
              value={anneeId}
              onChange={(e) => setAnneeId(e.target.value)}
              aria-label="Année scolaire"
            >
              {annees.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.libelle}
                </option>
              ))}
            </select>
            <button type="button" onClick={openCreate} className="btn-primary">
              + Période
            </button>
          </>
        }
      />

      <Table
        columns={columns}
        data={trimestres}
        loading={loading}
        emptyIcon={emptyIcons.trimestres}
        emptyMessage="Aucune période pour l'instant — ajoutez-en une pour cette année scolaire (sans limite à 3)."
      />

      <Modal
        isOpen={modal}
        onClose={() => !saving && setModal(false)}
        title={editId ? 'Modifier la période' : 'Nouvelle période'}
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              disabled={saving}
              onClick={() => setModal(false)}
            >
              Annuler
            </button>
            <button type="submit" form="trimestre-form" className="btn-primary" disabled={saving}>
              {saving ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          </>
        }
      >
        <form id="trimestre-form" onSubmit={handleSubmit} className="space-y-4">
          <FormField
            label="Numéro (séquence)"
            name="numero"
            type="number"
            min="1"
            value={form.numero}
            onChange={(e) => setForm({ ...form, numero: e.target.value })}
            required
            error={fieldErrors.numero}
            helpText="Correspond à sequence côté périodes — 1, 2, 3, 4… sans limite."
          />
          <FormField
            label="Date début"
            name="date_debut"
            type="date"
            value={form.date_debut}
            onChange={(e) => setForm({ ...form, date_debut: e.target.value })}
            required
            error={fieldErrors.date_debut}
          />
          <FormField
            label="Date fin"
            name="date_fin"
            type="date"
            value={form.date_fin}
            onChange={(e) => setForm({ ...form, date_fin: e.target.value })}
            required
            error={fieldErrors.date_fin}
          />
        </form>
      </Modal>
    </div>
  );
}
