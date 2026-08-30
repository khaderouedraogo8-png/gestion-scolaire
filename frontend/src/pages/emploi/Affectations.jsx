import { useCallback, useEffect, useState } from 'react';
import { emploiApi } from '../../services/api/emploi';
import { configApi } from '../../services/api/config';
import { notesApi } from '../../services/api/notes';
import Table from '../../components/Table';
import { emptyIcons } from '../../utils/emptyIcons';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';

export default function Affectations() {
  const toast = useToast();
  const { isAdmin } = useAuth();

  const [affectations, setAffectations] = useState([]);
  const [enseignants, setEnseignants] = useState([]);
  const [classes, setClasses] = useState([]);
  const [matieres, setMatieres] = useState([]);
  const [annees, setAnnees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [classeFilter, setClasseFilter] = useState('');
  const [anneeFilter, setAnneeFilter] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    id_enseignant: '',
    id_classe: '',
    id_matiere: '',
    id_annee: '',
    volume_horaire_hebdo: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await emploiApi.listAffectations({
        id_classe: classeFilter || undefined,
        id_annee: anneeFilter || undefined,
      });
      setAffectations(data.items || data || []);
    } catch {
      toast.error('Erreur lors du chargement des affectations');
    } finally {
      setLoading(false);
    }
  }, [classeFilter, anneeFilter, toast]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const init = async () => {
      try {
        const [ens, cls, mat, ans] = await Promise.all([
          emploiApi.listEnseignants(),
          configApi.listClasses(),
          notesApi.listMatieres(),
          configApi.listAnnees(),
        ]);
        setEnseignants(ens.items || ens || []);
        const classList = cls.items || cls || [];
        setClasses(classList);
        setMatieres(mat.items || mat || []);
        const anneeList = ans.items || ans || [];
        setAnnees(anneeList);
        const active = anneeList.find((a) => a.est_active);
        if (active) setAnneeFilter(String(active.id));
      } catch {
        /* ignore */
      }
    };
    init();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await emploiApi.createAffectation({
        id_enseignant: form.id_enseignant,
        id_classe: form.id_classe,
        id_matiere: form.id_matiere,
        id_annee: form.id_annee,
        volume_horaire_hebdo: form.volume_horaire_hebdo ? Number(form.volume_horaire_hebdo) : null,
      });
      toast.success('Affectation créée');
      setModalOpen(false);
      setForm({ id_enseignant: '', id_classe: '', id_matiere: '', id_annee: '', volume_horaire_hebdo: '' });
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur lors de la création');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Supprimer cette affectation ?')) return;
    try {
      await emploiApi.deleteAffectation(id);
      toast.success('Affectation supprimée');
      load();
    } catch {
      toast.error('Erreur lors de la suppression');
    }
  };

  const findLabel = (list, id, key = 'nom') =>
    list.find((item) => String(item.id) === String(id))?.[key] ||
    list.find((item) => String(item.id) === String(id))?.libelle ||
    '—';

  const columns = [
    {
      key: 'enseignant',
      header: 'Enseignant',
      render: (r) => (
        <span className="font-medium">
          {r.enseignant?.prenom || ''} {r.enseignant?.nom || r.enseignant_nom || findLabel(enseignants, r.id_enseignant, 'nom')}
        </span>
      ),
    },
    {
      key: 'classe',
      header: 'Classe',
      render: (r) => r.classe?.libelle || r.classe?.nom || r.classe_nom || findLabel(classes, r.id_classe, 'libelle'),
    },
    {
      key: 'matiere',
      header: 'Matière',
      render: (r) => r.matiere?.nom || r.matiere_nom || findLabel(matieres, r.id_matiere),
    },
    {
      key: 'volume',
      header: 'Volume h/sem',
      render: (r) => (r.volume_horaire_hebdo ? `${r.volume_horaire_hebdo}h` : '—'),
    },
    {
      key: 'actions',
      header: '',
      render: (r) =>
        isAdmin ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              handleDelete(r.id);
            }}
            className="text-sm font-medium text-brique hover:text-brique/80"
          >
            Supprimer
          </button>
        ) : null,
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Emploi du temps"
        title="Affectations"
        subtitle="Liaison enseignant / classe / matière"
        actions={
          isAdmin && (
            <button type="button" onClick={() => setModalOpen(true)} className="btn-primary">
              + Nouvelle affectation
            </button>
          )
        }
      />

      <Table
        columns={columns}
        data={affectations}
        loading={loading}
        filters={
          <>
            <select
              value={anneeFilter}
              onChange={(e) => setAnneeFilter(e.target.value)}
              className="input w-auto"
            >
              <option value="">Toutes les années</option>
              {annees.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.libelle}{a.est_active ? ' (active)' : ''}
                </option>
              ))}
            </select>
            <select
              value={classeFilter}
              onChange={(e) => setClasseFilter(e.target.value)}
              className="input w-auto"
            >
              <option value="">Toutes les classes</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.libelle || c.nom}
                </option>
              ))}
            </select>
          </>
        }
        emptyIcon={emptyIcons.affectations}
        emptyMessage="Aucune affectation pour l'instant — configurez les affectations ci-dessus."
      />

      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Nouvelle affectation"
        size="lg"
        footer={
          <>
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary">
              Annuler
            </button>
            <button type="submit" form="aff-form" disabled={saving} className="btn-primary">
              {saving ? 'Enregistrement...' : 'Créer'}
            </button>
          </>
        }
      >
        <form id="aff-form" onSubmit={handleCreate} className="grid gap-4 sm:grid-cols-2">
          <FormField
            label="Enseignant"
            name="id_enseignant"
            type="select"
            value={form.id_enseignant}
            onChange={(e) => setForm({ ...form, id_enseignant: e.target.value })}
            required
            options={enseignants.map((e) => ({
              value: String(e.id),
              label: `${e.prenom} ${e.nom}`,
            }))}
          />
          <FormField
            label="Classe"
            name="id_classe"
            type="select"
            value={form.id_classe}
            onChange={(e) => setForm({ ...form, id_classe: e.target.value })}
            required
            options={classes.map((c) => ({
              value: String(c.id),
              label: c.libelle || c.nom,
            }))}
          />
          <FormField
            label="Matière"
            name="id_matiere"
            type="select"
            value={form.id_matiere}
            onChange={(e) => setForm({ ...form, id_matiere: e.target.value })}
            required
            options={matieres.map((m) => ({ value: String(m.id), label: m.libelle || m.nom }))}
          />
          <FormField
            label="Année scolaire"
            name="id_annee"
            type="select"
            value={form.id_annee}
            onChange={(e) => setForm({ ...form, id_annee: e.target.value })}
            required
            options={annees.map((a) => ({ value: String(a.id), label: a.libelle }))}
          />
          <FormField
            label="Volume horaire hebdo (h)"
            name="volume_horaire_hebdo"
            type="number"
            value={form.volume_horaire_hebdo}
            onChange={(e) => setForm({ ...form, volume_horaire_hebdo: e.target.value })}
            min="1"
            max="40"
          />
        </form>
      </Modal>
    </div>
  );
}
