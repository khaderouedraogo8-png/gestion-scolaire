import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { GraduationCap } from 'lucide-react';
import { configApi } from '../../services/api/config';
import { emploiApi } from '../../services/api/emploi';
import Table from '../../components/Table';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import PageHeader from '../../components/PageHeader';
import StructureAcademiqueNav from '../../components/StructureAcademiqueNav';
import { useToast } from '../../components/Toast';
import {
  apiErrorMessage,
  asList,
  formatNiveauWithProgram,
} from '../../utils/academicLabels';

const EMPTY_FORM = {
  libelle: '',
  id_program: '',
  id_niveau: '',
  id_annee: '',
  id_professeur_principal: '',
  capacite_max: '50',
};

export default function Classes() {
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;

  const [classes, setClasses] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [niveaux, setNiveaux] = useState([]);
  const [annees, setAnnees] = useState([]);
  const [enseignants, setEnseignants] = useState([]);
  const [anneeFilter, setAnneeFilter] = useState('');
  const [programFilter, setProgramFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState({});
  const [saving, setSaving] = useState(false);

  const programById = useMemo(() => {
    const map = {};
    programs.forEach((p) => {
      map[String(p.id)] = p;
    });
    return map;
  }, [programs]);

  const niveauxForForm = useMemo(() => {
    if (!form.id_program) return [];
    return niveaux.filter((n) => String(n.id_program) === String(form.id_program));
  }, [niveaux, form.id_program]);

  useEffect(() => {
    const init = async () => {
      try {
        const [progs, nivs, ans, ens] = await Promise.all([
          configApi.listPrograms({ is_active: true }),
          configApi.listNiveaux(),
          configApi.listAnnees(),
          emploiApi.listEnseignants(),
        ]);
        setPrograms(asList(progs));
        setNiveaux(asList(nivs));
        const anneeList = asList(ans);
        setAnnees(anneeList);
        setEnseignants(asList(ens));
        const active = anneeList.find((a) => a.est_active);
        if (active) {
          setAnneeFilter(String(active.id));
          setForm((f) => ({ ...f, id_annee: String(active.id) }));
        }
      } catch (err) {
        toastRef.current.error(apiErrorMessage(err, 'Impossible de charger les référentiels.'));
      }
    };
    init();
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const params = {};
      if (anneeFilter) params.id_annee = anneeFilter;
      if (programFilter) params.id_program = programFilter;
      const data = await configApi.listClasses(params);
      setClasses(asList(data));
    } catch (err) {
      const msg = apiErrorMessage(err, 'Impossible de charger les classes.');
      setLoadError(msg);
      toastRef.current.error(msg);
    } finally {
      setLoading(false);
    }
  }, [anneeFilter, programFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setEditing(null);
    const defaultProgram = programFilter || (programs[0] ? String(programs[0].id) : '');
    setForm({
      ...EMPTY_FORM,
      id_annee: anneeFilter || '',
      id_program: defaultProgram,
      id_niveau: '',
    });
    setFieldErrors({});
    setModalOpen(true);
  };

  const openEdit = (classe) => {
    setEditing(classe);
    const niveau = niveaux.find((n) => String(n.id) === String(classe.id_niveau));
    setForm({
      libelle: classe.libelle || classe.nom || '',
      id_program: String(classe.id_program || niveau?.id_program || ''),
      id_niveau: String(classe.id_niveau || ''),
      id_annee: String(classe.id_annee || ''),
      id_professeur_principal: classe.id_professeur_principal
        ? String(classe.id_professeur_principal)
        : '',
      capacite_max: String(classe.capacite_max || 50),
    });
    setFieldErrors({});
    setModalOpen(true);
  };

  const validate = () => {
    const errors = {};
    if (!form.libelle.trim()) errors.libelle = 'Le libellé est obligatoire.';
    if (!form.id_program) errors.id_program = 'Le programme est obligatoire.';
    if (!form.id_niveau) errors.id_niveau = 'Le niveau est obligatoire.';
    if (!form.id_annee) errors.id_annee = 'L’année scolaire est obligatoire.';
    const niveau = niveaux.find((n) => String(n.id) === String(form.id_niveau));
    if (niveau && String(niveau.id_program) !== String(form.id_program)) {
      errors.id_niveau = 'Ce niveau n’appartient pas au programme sélectionné.';
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setSaving(true);
    try {
      const payload = {
        libelle: form.libelle.trim(),
        id_niveau: form.id_niveau,
        id_annee: form.id_annee,
        id_program: form.id_program,
        id_professeur_principal: form.id_professeur_principal || null,
        capacite_max: Number(form.capacite_max) || 50,
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
      toast.error(apiErrorMessage(err, "Erreur lors de l'enregistrement"));
    } finally {
      setSaving(false);
    }
  };

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
      key: 'program',
      header: 'Programme',
      render: (r) => {
        const p = programById[String(r.id_program)];
        return p ? p.name : '—';
      },
    },
    {
      key: 'niveau',
      header: 'Niveau',
      render: (r) => {
        const niveau =
          r.niveau || niveaux.find((n) => String(n.id) === String(r.id_niveau));
        if (!niveau) return '—';
        return formatNiveauWithProgram(niveau, programById);
      },
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
      align: 'right',
      render: (r) => (
        <button
          type="button"
          className="text-sm font-medium text-or-cachet hover:underline"
          onClick={() => openEdit(r)}
        >
          Modifier
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Structure académique"
        title="Classes"
        subtitle="Création guidée : Programme → Niveau → Classe. Les niveaux proposés dépendent du programme choisi."
        actions={
          <button type="button" className="btn-primary" onClick={openCreate}>
            + Nouvelle classe
          </button>
        }
      />

      <StructureAcademiqueNav />

      {loadError && !loading && classes.length === 0 ? (
        <div
          role="alert"
          className="rounded-card border border-brique/30 bg-brique-clair px-4 py-6 text-center"
        >
          <p className="text-sm text-brique">{loadError}</p>
          <button type="button" className="btn-secondary mt-4" onClick={load}>
            Réessayer
          </button>
        </div>
      ) : (
        <Table
          columns={columns}
          data={classes}
          loading={loading}
          emptyIcon={GraduationCap}
          emptyMessage="Aucune classe pour ces filtres. Créez une classe en choisissant d’abord le programme."
          filters={
            <>
              <select
                className="input w-auto"
                value={anneeFilter}
                onChange={(e) => setAnneeFilter(e.target.value)}
                aria-label="Filtrer par année"
              >
                <option value="">Toutes les années</option>
                {annees.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.libelle}
                    {a.est_active ? ' (active)' : ''}
                  </option>
                ))}
              </select>
              <select
                className="input w-auto"
                value={programFilter}
                onChange={(e) => setProgramFilter(e.target.value)}
                aria-label="Filtrer par programme"
              >
                <option value="">Tous les programmes</option>
                {programs.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.code})
                  </option>
                ))}
              </select>
            </>
          }
        />
      )}

      <Modal
        isOpen={modalOpen}
        onClose={() => !saving && setModalOpen(false)}
        title={editing ? 'Modifier la classe' : 'Nouvelle classe'}
        size="lg"
        footer={
          <>
            <button
              type="button"
              className="btn-secondary"
              disabled={saving}
              onClick={() => setModalOpen(false)}
            >
              Annuler
            </button>
            <button type="submit" form="classe-form" className="btn-primary" disabled={saving}>
              {saving ? 'Enregistrement…' : editing ? 'Enregistrer' : 'Créer'}
            </button>
          </>
        }
      >
        <form id="classe-form" onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
          <FormField
            label="Programme"
            name="id_program"
            type="select"
            value={form.id_program}
            onChange={(e) =>
              setForm({ ...form, id_program: e.target.value, id_niveau: '' })
            }
            options={programs.map((p) => ({
              value: String(p.id),
              label: `${p.name} (${p.code})`,
            }))}
            required
            error={fieldErrors.id_program}
            helpText="Étape 1 — filtre les niveaux disponibles."
          />
          <FormField
            label="Niveau"
            name="id_niveau"
            type="select"
            value={form.id_niveau}
            onChange={(e) => setForm({ ...form, id_niveau: e.target.value })}
            options={niveauxForForm.map((n) => ({
              value: String(n.id),
              label: formatNiveauWithProgram(n, programById),
            }))}
            required
            error={fieldErrors.id_niveau}
            disabled={!form.id_program}
            helpText="Étape 2 — uniquement les niveaux du programme choisi."
          />
          <FormField
            label="Libellé de la classe"
            name="libelle"
            value={form.libelle}
            onChange={(e) => setForm({ ...form, libelle: e.target.value })}
            required
            error={fieldErrors.libelle}
            placeholder="Ex. 2nde A"
          />
          <FormField
            label="Année scolaire"
            name="id_annee"
            type="select"
            value={form.id_annee}
            onChange={(e) => setForm({ ...form, id_annee: e.target.value })}
            options={annees.map((a) => ({ value: String(a.id), label: a.libelle }))}
            required
            error={fieldErrors.id_annee}
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
            label="Professeur principal"
            name="id_professeur_principal"
            type="select"
            value={form.id_professeur_principal}
            onChange={(e) => setForm({ ...form, id_professeur_principal: e.target.value })}
            options={enseignants.map((e) => ({
              value: String(e.id),
              label: `${e.prenom} ${e.nom}`,
            }))}
          />
        </form>
      </Modal>
    </div>
  );
}
