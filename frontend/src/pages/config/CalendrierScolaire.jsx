import { useEffect, useState } from 'react';
import { configApi } from '../../services/api/config';
import FormField from '../../components/FormField';
import Modal from '../../components/Modal';
import Table from '../../components/Table';
import Badge from '../../components/Badge';
import { useToast } from '../../components/Toast';

const TYPES = [
  { value: 'ferie', label: 'Jour férié' },
  { value: 'vacances', label: 'Vacances' },
  { value: 'rentree', label: 'Rentrée' },
  { value: 'examen_officiel', label: 'Examen officiel' },
  { value: 'autre', label: 'Autre' },
];

export default function CalendrierScolaire() {
  const toast = useToast();
  const [annees, setAnnees] = useState([]);
  const [anneeId, setAnneeId] = useState('');
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState({
    type_evenement: 'ferie',
    libelle: '',
    date_debut: '',
    date_fin: '',
    bloque_programmation: true,
  });

  useEffect(() => {
    configApi.listAnnees().then((data) => {
      const list = data.items || data || [];
      setAnnees(list);
      const active = list.find((a) => a.est_active) || list[0];
      if (active) setAnneeId(String(active.id));
    });
  }, []);

  const load = async () => {
    if (!anneeId) return;
    setLoading(true);
    try {
      const data = await configApi.listCalendrier(anneeId);
      setEvents(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Erreur chargement calendrier');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [anneeId]);

  const openCreate = () => {
    setEditId(null);
    setForm({
      type_evenement: 'ferie',
      libelle: '',
      date_debut: '',
      date_fin: '',
      bloque_programmation: true,
    });
    setModal(true);
  };

  const openEdit = (ev) => {
    setEditId(ev.id);
    setForm({
      type_evenement: ev.type_evenement,
      libelle: ev.libelle,
      date_debut: ev.date_debut,
      date_fin: ev.date_fin,
      bloque_programmation: ev.bloque_programmation !== false,
    });
    setModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = { ...form, id_annee: anneeId, bloque_programmation: Boolean(form.bloque_programmation) };
    try {
      if (editId) {
        await configApi.updateEvenementCalendrier(editId, payload);
        toast.success('Événement mis à jour');
      } else {
        await configApi.createEvenementCalendrier(payload);
        toast.success('Événement ajouté');
      }
      setModal(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Supprimer cet événement ?')) return;
    try {
      await configApi.deleteEvenementCalendrier(id);
      toast.success('Événement supprimé');
      load();
    } catch {
      toast.error('Erreur suppression');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="page-title">Calendrier scolaire</h1>
          <p className="page-subtitle">Jours fériés, vacances et dates bloquées pour la programmation</p>
        </div>
        <button type="button" className="btn-primary" onClick={openCreate}>
          + Ajouter
        </button>
      </div>

      <FormField
        label="Année scolaire"
        type="select"
        value={anneeId}
        onChange={(e) => setAnneeId(e.target.value)}
        options={annees.map((a) => ({ value: String(a.id), label: a.libelle }))}
        className="max-w-xs"
      />

      <Table
        columns={[
          { key: 'libelle', header: 'Libellé' },
          { key: 'type_evenement', header: 'Type' },
          { key: 'date_debut', header: 'Début' },
          { key: 'date_fin', header: 'Fin' },
          {
            key: 'bloque',
            header: 'Bloque prog.',
            render: (r) =>
              r.bloque_programmation ? (
                <Badge variant="warning">Oui</Badge>
              ) : (
                <Badge variant="default">Non</Badge>
              ),
          },
          {
            key: 'actions',
            header: '',
            render: (r) => (
              <div className="flex gap-2">
                <button type="button" className="text-xs text-or-cachet hover:underline" onClick={() => openEdit(r)}>
                  Modifier
                </button>
                <button type="button" className="text-xs text-brique hover:underline" onClick={() => handleDelete(r.id)}>
                  Supprimer
                </button>
              </div>
            ),
          },
        ]}
        data={events}
        loading={loading}
        emptyMessage="Aucun événement — ajoutez les jours fériés et vacances."
      />

      <Modal isOpen={modal} onClose={() => setModal(false)} title={editId ? 'Modifier événement' : 'Nouvel événement'}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField
            label="Type"
            type="select"
            value={form.type_evenement}
            onChange={(e) => setForm({ ...form, type_evenement: e.target.value })}
            options={TYPES}
            required
          />
          <FormField
            label="Libellé"
            value={form.libelle}
            onChange={(e) => setForm({ ...form, libelle: e.target.value })}
            required
          />
          <FormField
            label="Date début"
            type="date"
            value={form.date_debut}
            onChange={(e) => setForm({ ...form, date_debut: e.target.value })}
            required
          />
          <FormField
            label="Date fin"
            type="date"
            value={form.date_fin}
            onChange={(e) => setForm({ ...form, date_fin: e.target.value })}
            required
          />
          <FormField
            label="Bloquer devoirs/compositions"
            type="checkbox"
            value={form.bloque_programmation}
            onChange={(e) => setForm({ ...form, bloque_programmation: e.target.checked })}
          />
          <button type="submit" className="btn-primary w-full">
            Enregistrer
          </button>
        </form>
      </Modal>
    </div>
  );
}
