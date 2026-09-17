import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { admissionApi } from '../../services/api/admission';
import { configApi } from '../../services/api/config';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

const STATUT_OPTIONS = [
  { value: 'brouillon', label: 'Brouillon' },
  { value: 'soumis', label: 'Soumis' },
  { value: 'en_examen', label: 'En examen' },
  { value: 'accepte', label: 'Accepté' },
  { value: 'refuse', label: 'Refusé' },
  { value: 'liste_attente', label: 'Liste d’attente' },
  { value: 'inscrit', label: 'Inscrit' },
];

const empty = {
  nom: '',
  prenom: '',
  sexe: '',
  date_naissance: '',
  lieu_naissance: '',
  telephone_parent: '',
  email_parent: '',
  niveau_demande: '',
  id_annee: '',
  notes: '',
  statut: 'brouillon',
};

export default function AdmissionForm() {
  const { id } = useParams();
  const isNew = !id || id === 'nouveau';
  const navigate = useNavigate();
  const toast = useToast();
  const [form, setForm] = useState(empty);
  const [annees, setAnnees] = useState([]);
  const [classes, setClasses] = useState([]);
  const [idClasse, setIdClasse] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(!isNew);

  useEffect(() => {
    configApi.listAnnees().then((a) => {
      const list = Array.isArray(a) ? a : a.items || [];
      setAnnees(list);
      const active = list.find((x) => x.est_active);
      if (active && isNew) setForm((f) => ({ ...f, id_annee: String(active.id) }));
    }).catch(() => {});
    configApi.listClasses?.().then((c) => {
      setClasses(Array.isArray(c) ? c : c.items || []);
    }).catch(() => {});
  }, [isNew]);

  useEffect(() => {
    if (isNew) return;
    let cancelled = false;
    (async () => {
      try {
        const d = await admissionApi.get(id);
        if (!cancelled) {
          setForm({
            nom: d.nom || '',
            prenom: d.prenom || '',
            sexe: d.sexe || '',
            date_naissance: d.date_naissance || '',
            lieu_naissance: d.lieu_naissance || '',
            telephone_parent: d.telephone_parent || '',
            email_parent: d.email_parent || '',
            niveau_demande: d.niveau_demande || '',
            id_annee: d.id_annee ? String(d.id_annee) : '',
            notes: d.notes || '',
            statut: d.statut || 'brouillon',
            id_eleve: d.id_eleve,
          });
        }
      } catch {
        if (!cancelled) toast.error('Dossier introuvable');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, isNew, toast]);

  const onChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  };

  const payload = () => ({
    nom: form.nom.trim(),
    prenom: form.prenom.trim(),
    sexe: form.sexe || null,
    date_naissance: form.date_naissance || null,
    lieu_naissance: form.lieu_naissance || null,
    telephone_parent: form.telephone_parent || null,
    email_parent: form.email_parent || null,
    niveau_demande: form.niveau_demande || null,
    id_annee: form.id_annee || null,
    notes: form.notes || null,
    statut: form.statut || 'brouillon',
  });

  const handleSave = async (e) => {
    e.preventDefault();
    if (!form.nom.trim() || !form.prenom.trim()) {
      toast.error('Nom et prénom requis');
      return;
    }
    setSaving(true);
    try {
      if (isNew) {
        const created = await admissionApi.create(payload());
        toast.success('Dossier créé');
        navigate(`/admission/${created.id}`, { replace: true });
      } else {
        await admissionApi.update(id, payload());
        toast.success('Dossier enregistré');
      }
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur enregistrement');
    } finally {
      setSaving(false);
    }
  };

  const handleStatut = async (statut) => {
    try {
      const d = await admissionApi.patchStatut(id, statut);
      setForm((f) => ({ ...f, statut: d.statut }));
      toast.success(`Statut → ${statut}`);
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur statut');
    }
  };

  const handleConvert = async () => {
    if (!idClasse) {
      toast.error('Sélectionnez une classe');
      return;
    }
    try {
      const res = await admissionApi.convertToEleve(id, {
        id_classe: idClasse,
        id_annee: form.id_annee || undefined,
      });
      toast.success('Converti en élève');
      if (res.id_eleve || res.eleve?.id) {
        navigate(`/eleves/${res.id_eleve || res.eleve.id}`);
      } else {
        setForm((f) => ({ ...f, statut: 'inscrit', id_eleve: res.id }));
      }
    } catch (err) {
      toast.error(err.response?.data?.message || 'Conversion impossible');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <div className="loading-ring" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Admissions"
        title={isNew ? 'Nouveau dossier' : `${form.prenom} ${form.nom}`}
        subtitle="Candidature et conversion élève"
        actions={
          <Link to="/admission" className="btn-secondary">
            Retour à la liste
          </Link>
        }
      />

      <form onSubmit={handleSave} className="card-premium space-y-5 p-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Nom" name="nom" value={form.nom} onChange={onChange} required />
          <FormField label="Prénom" name="prenom" value={form.prenom} onChange={onChange} required />
          <FormField
            label="Sexe"
            name="sexe"
            type="select"
            value={form.sexe}
            onChange={onChange}
            options={[
              { value: 'M', label: 'Masculin' },
              { value: 'F', label: 'Féminin' },
            ]}
          />
          <FormField
            label="Date de naissance"
            name="date_naissance"
            type="date"
            value={form.date_naissance}
            onChange={onChange}
          />
          <FormField
            label="Lieu de naissance"
            name="lieu_naissance"
            value={form.lieu_naissance}
            onChange={onChange}
          />
          <FormField
            label="Niveau demandé"
            name="niveau_demande"
            value={form.niveau_demande}
            onChange={onChange}
          />
          <FormField
            label="Tél. parent"
            name="telephone_parent"
            value={form.telephone_parent}
            onChange={onChange}
          />
          <FormField
            label="Email parent"
            name="email_parent"
            type="email"
            value={form.email_parent}
            onChange={onChange}
          />
          <FormField
            label="Année scolaire"
            name="id_annee"
            type="select"
            value={form.id_annee}
            onChange={onChange}
            options={annees.map((a) => ({ value: String(a.id), label: a.libelle }))}
          />
          {!isNew && (
            <FormField
              label="Statut"
              name="statut"
              type="select"
              value={form.statut}
              onChange={(e) => handleStatut(e.target.value)}
              options={STATUT_OPTIONS}
            />
          )}
        </div>
        <FormField
          label="Notes internes"
          name="notes"
          type="textarea"
          value={form.notes}
          onChange={onChange}
          rows={3}
        />
        <div className="flex flex-wrap gap-3">
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? 'Enregistrement…' : 'Enregistrer'}
          </button>
        </div>
      </form>

      {!isNew && form.statut === 'accepte' && !form.id_eleve && (
        <div className="card-premium space-y-4 p-6">
          <h3 className="section-title !text-base">Convertir en élève</h3>
          <FormField
            label="Classe d’affectation"
            name="id_classe"
            type="select"
            value={idClasse}
            onChange={(e) => setIdClasse(e.target.value)}
            options={classes.map((c) => ({
              value: String(c.id),
              label: c.libelle || c.nom || String(c.id),
            }))}
          />
          <button type="button" className="btn-primary" onClick={handleConvert}>
            Créer l’élève et l’inscription
          </button>
        </div>
      )}
    </div>
  );
}
