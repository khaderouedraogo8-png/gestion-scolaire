import { useCallback, useEffect, useState } from 'react';
import { configApi } from '../../services/api/config';
import { emploiApi } from '../../services/api/emploi';
import Table from '../../components/Table';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function Classes() {
  const toast = useToast();

  const [classes, setClasses] = useState([]);
  const [niveaux, setNiveaux] = useState([]);
  const [annees, setAnnees] = useState([]);
  const [enseignants, setEnseignants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [anneeFilter, setAnneeFilter] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    libelle: '',
    id_niveau: '',
    id_annee: '',
    id_professeur_principal: '',
    capacite_max: '50',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await configApi.listClasses({
        id_annee: anneeFilter || undefined,
      });
      setClasses(data.items || data || []);
    } catch {
      toast.error('Erreur lors du chargement des classes');
    } finally {
      setLoading(false);
    }
  }, [anneeFilter, toast]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const init = async () => {
      try {
        const [niv, ans, ens] = await Promise.all([
          configApi.listNiveaux(),
          configApi.listAnnees(),
          emploiApi.listEnseignants(),
        ]);
        setNiveaux(niv.items || niv || []);
        const anneeList = ans.items || ans || [];
        setAnnees(anneeList);
        setEnseignants(ens.items || ens || []);
        const active = anneeList.find((a) => a.est_active);
        if (active) {
          setAnneeFilter(String(active.id));
          setForm((f) => ({ ...f, id_annee: String(active.id) }));
        }
      } catch {
        /* ignore */
      }
    };
    init();
  }, []);

  const openCreate = () => {
    setEditing(null);
    setForm({
      libelle: '',
      id_niveau: '',
      id_annee: anneeFilter || '',
      id_professeur_principal: '',
      capacite_max: '50',
    });
    setModalOpen(true);
  };

  const openEdit = (classe) => {
    setEditing(classe);
    setForm({
      libelle: classe.libelle || classe.nom || '',
      id_niveau: String(classe.id_niveau || ''),
      id_annee: String(classe.id_annee || ''),
      id_professeur_principal: classe.id_professeur_principal ? String(classe.id_professeur_principal) : '',
      capacite_max: String(classe.capacite_max || 50),
    });
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        libelle: form.libelle,
        id_niveau: form.id_niveau,
        id_annee: form.id_annee,
        id_professeur_principal: form.id_professeur_principal || null,
        capacite_max: Number(form.capacite_max),
      };
      if (editing) {
        await configApi.updateClasse(editing.id, payload);
        toast.success('Classe mise à jour');
      } else {
        await configApi.createClasse(payload);
        toast.success('Classe créée');
      }
      setModalOpen(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur lors de l\'enregistrement');
    } finally {
      setSaving(false);
    }
  };

  const findNiveau = (id) =>
    niveaux.find((n) => String(n.id) === String(id))?.libelle || '—';

  const findEnseignant = (id) => {
    const e = enseignants.find((ens) => String(ens.id) === String(id));
    return e ? `${e.prenom} ${e.nom}` : '—';
  };

  const columns = [
    {
      key: 'libelle',
      header: 'Classe',
      render: (r) => <span className="font-medium">{r.libelle || r.nom}</span>,
    },
    {
      key: 'niveau',
      header: 'Niveau',
      render: (r) => r.niveau?.libelle || r.niveau_nom || findNiveau(r.id_niveau),
    },
    {
      key: 'pp',
      header: 'Prof. principal',
      render: (r) =>
        r.professeur_principal
          ? `${r.professeur_principal.prenom} ${r.professeur_principal.nom}`
          : findEnseignant(r.id_professeur_principal),
    },
    {
      key: 'capacite',
      header: 'Capacité',
      render: (r) => `${r.effectif || r.nb_eleves || 0} / ${r.capacite_max || 50}`,
    },
    {
      key: 'actions',
      header: '',
      render: (r) => (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            openEdit(r);
          }}
          className="text-sm font-medium text-primary-600 hover:text-primary-800"
        >
          Modifier
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Classes</h1>
          <p className="text-sm text-slate-500">Organisation des classes par niveau et année</p>
        </div>
        <button type="button" onClick={openCreate} className="btn-primary">
          + Nouvelle classe
        </button>
      </div>

      <Table
        columns={columns}
        data={classes}
        loading={loading}
        filters={
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
        }
        emptyMessage="Aucune classe configurée"
      />

      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? 'Modifier la classe' : 'Nouvelle classe'}
        size="lg"
        footer={
          <>
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary">
              Annuler
            </button>
            <button type="submit" form="classe-form" disabled={saving} className="btn-primary">
              {saving ? 'Enregistrement...' : editing ? 'Enregistrer' : 'Créer'}
            </button>
          </>
        }
      >
        <form id="classe-form" onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
          <FormField
            label="Libellé"
            name="libelle"
            value={form.libelle}
            onChange={(e) => setForm({ ...form, libelle: e.target.value })}
            required
            placeholder="Ex. 6ème A"
          />
          <FormField
            label="Capacité max"
            name="capacite_max"
            type="number"
            value={form.capacite_max}
            onChange={(e) => setForm({ ...form, capacite_max: e.target.value })}
            min="1"
            max="200"
          />
          <FormField
            label="Niveau"
            name="id_niveau"
            type="select"
            value={form.id_niveau}
            onChange={(e) => setForm({ ...form, id_niveau: e.target.value })}
            required
            options={niveaux.map((n) => ({ value: String(n.id), label: n.libelle || n.nom }))}
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
            label="Professeur principal"
            name="id_professeur_principal"
            type="select"
            value={form.id_professeur_principal}
            onChange={(e) => setForm({ ...form, id_professeur_principal: e.target.value })}
            options={enseignants.map((e) => ({
              value: String(e.id),
              label: `${e.prenom} ${e.nom}`,
            }))}
            className="sm:col-span-2"
          />
        </form>
      </Modal>
    </div>
  );
}
