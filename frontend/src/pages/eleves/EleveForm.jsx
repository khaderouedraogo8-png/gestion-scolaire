import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { elevesApi } from '../../services/api/eleves';
import { configApi } from '../../services/api/config';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

const EMPTY_PARENT = {
  nom: '',
  prenom: '',
  lien_parente: '',
  telephone: '',
  email: '',
  tuteur_legal: false,
};

const initialForm = {
  nom: '',
  prenom: '',
  date_naissance: '',
  lieu_naissance: '',
  sexe: '',
  adresse: '',
  notes_medicales: '',
  id_annee: '',
  id_classe: '',
};

export default function EleveForm() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const toast = useToast();

  const [form, setForm] = useState(initialForm);
  const [parents, setParents] = useState([]);
  const [annees, setAnnees] = useState([]);
  const [classes, setClasses] = useState([]);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const init = async () => {
      try {
        if (!isEdit) {
          const [anneesData, classesData] = await Promise.all([
            configApi.listAnnees(),
            configApi.listClasses(),
          ]);
          const anneeList = anneesData.items || anneesData || [];
          const classeList = classesData.items || classesData || [];
          setAnnees(anneeList);
          setClasses(classeList);
          const active = anneeList.find((a) => a.est_active);
          if (active) {
            setForm((f) => ({
              ...f,
              id_annee: String(active.id),
            }));
          }
        } else {
          const data = await elevesApi.get(id);
          setForm({
            nom: data.nom || '',
            prenom: data.prenom || '',
            date_naissance: data.date_naissance || '',
            lieu_naissance: data.lieu_naissance || '',
            sexe: data.sexe || '',
            adresse: data.adresse || '',
            notes_medicales: data.notes_medicales || '',
            id_annee: '',
            id_classe: '',
          });
        }
      } catch {
        toast.error('Erreur lors du chargement');
        navigate('/eleves');
      } finally {
        setLoading(false);
      }
    };
    init();
  }, [id, isEdit, navigate, toast]);

  const filteredClasses = classes.filter(
    (c) => !form.id_annee || String(c.id_annee) === String(form.id_annee)
  );

  const validate = () => {
    const newErrors = {};
    if (!form.nom.trim()) newErrors.nom = 'Le nom est requis';
    if (!form.prenom.trim()) newErrors.prenom = 'Le prénom est requis';
    if (!form.sexe) newErrors.sexe = 'Le sexe est requis';
    if (!isEdit) {
      if (!form.id_annee) newErrors.id_annee = "L'année scolaire est requise";
      if (!form.id_classe) newErrors.id_classe = 'La classe est requise';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' }));
  };

  const handleParentChange = (index, e) => {
    const { name, value, type, checked } = e.target;
    setParents((prev) =>
      prev.map((p, i) =>
        i === index ? { ...p, [name]: type === 'checkbox' ? checked : value } : p
      )
    );
  };

  const addParent = () => setParents((prev) => [...prev, { ...EMPTY_PARENT }]);

  const removeParent = (index) =>
    setParents((prev) => prev.filter((_, i) => i !== index));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setSaving(true);
    try {
      if (isEdit) {
        await elevesApi.update(id, {
          nom: form.nom,
          prenom: form.prenom,
          sexe: form.sexe,
          date_naissance: form.date_naissance || null,
          lieu_naissance: form.lieu_naissance || null,
          adresse: form.adresse || null,
        });
        toast.success('Élève modifié avec succès');
        navigate(`/eleves/${id}`);
      } else {
        const payload = {
          nom: form.nom,
          prenom: form.prenom,
          sexe: form.sexe,
          date_naissance: form.date_naissance || null,
          lieu_naissance: form.lieu_naissance || null,
          adresse: form.adresse || null,
          id_annee: form.id_annee,
          id_classe: form.id_classe,
          notes_medicales: form.notes_medicales || null,
          parents: parents.filter((p) => p.nom.trim() && p.prenom.trim()),
        };
        const data = await elevesApi.create(payload);
        toast.success('Élève inscrit avec succès');
        navigate(`/eleves/${data.id}`);
      }
    } catch (err) {
      toast.error(err.response?.data?.message || "Erreur lors de l'enregistrement");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <Link to={isEdit ? `/eleves/${id}` : '/eleves'} className="text-sm text-primary-600 hover:underline">
          ← Retour
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-slate-900">
          {isEdit ? "Modifier l'élève" : 'Nouvel élève — Inscription'}
        </h1>
        {!isEdit && (
          <p className="text-sm text-slate-500">
            Création de la fiche élève et inscription pour l'année scolaire active
          </p>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <section className="card space-y-5">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Identité
          </h2>
          <div className="grid gap-5 sm:grid-cols-2">
            <FormField label="Nom" name="nom" value={form.nom} onChange={handleChange} error={errors.nom} required />
            <FormField label="Prénom" name="prenom" value={form.prenom} onChange={handleChange} error={errors.prenom} required />
            <FormField label="Date de naissance" name="date_naissance" type="date" value={form.date_naissance} onChange={handleChange} />
            <FormField label="Lieu de naissance" name="lieu_naissance" value={form.lieu_naissance} onChange={handleChange} />
            <FormField
              label="Sexe"
              name="sexe"
              type="select"
              value={form.sexe}
              onChange={handleChange}
              error={errors.sexe}
              required
              options={[
                { value: 'M', label: 'Masculin' },
                { value: 'F', label: 'Féminin' },
              ]}
            />
          </div>
          <FormField label="Adresse" name="adresse" type="textarea" value={form.adresse} onChange={handleChange} rows={2} />
          {!isEdit && (
            <FormField
              label="Notes médicales (confidentielles)"
              name="notes_medicales"
              type="textarea"
              value={form.notes_medicales}
              onChange={handleChange}
              rows={2}
              helpText="Allergies, conditions particulières — chiffrées en base"
            />
          )}
        </section>

        {!isEdit && (
          <section className="card space-y-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              Inscription
            </h2>
            <div className="grid gap-5 sm:grid-cols-2">
              <FormField
                label="Année scolaire"
                name="id_annee"
                type="select"
                value={form.id_annee}
                onChange={handleChange}
                error={errors.id_annee}
                required
                options={annees.map((a) => ({
                  value: String(a.id),
                  label: `${a.libelle}${a.est_active ? ' (active)' : ''}`,
                }))}
              />
              <FormField
                label="Classe"
                name="id_classe"
                type="select"
                value={form.id_classe}
                onChange={handleChange}
                error={errors.id_classe}
                required
                options={filteredClasses.map((c) => ({
                  value: String(c.id),
                  label: c.libelle || c.nom,
                }))}
              />
            </div>
          </section>
        )}

        {!isEdit && (
          <section className="card space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                Parents / Tuteurs
              </h2>
              <button type="button" onClick={addParent} className="btn-secondary text-sm">
                + Ajouter
              </button>
            </div>
            {parents.length === 0 ? (
              <p className="text-sm text-slate-500">Aucun parent ajouté (optionnel)</p>
            ) : (
              parents.map((parent, index) => (
                <div key={index} className="rounded-lg border border-slate-200 p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-slate-700">Parent {index + 1}</p>
                    <button type="button" onClick={() => removeParent(index)} className="text-sm text-red-600">
                      Supprimer
                    </button>
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <FormField label="Nom" name="nom" value={parent.nom} onChange={(e) => handleParentChange(index, e)} />
                    <FormField label="Prénom" name="prenom" value={parent.prenom} onChange={(e) => handleParentChange(index, e)} />
                    <FormField
                      label="Lien de parenté"
                      name="lien_parente"
                      type="select"
                      value={parent.lien_parente}
                      onChange={(e) => handleParentChange(index, e)}
                      options={[
                        { value: 'pere', label: 'Père' },
                        { value: 'mere', label: 'Mère' },
                        { value: 'tuteur', label: 'Tuteur légal' },
                        { value: 'autre', label: 'Autre' },
                      ]}
                    />
                    <FormField label="Téléphone" name="telephone" value={parent.telephone} onChange={(e) => handleParentChange(index, e)} />
                    <FormField label="Email" name="email" type="email" value={parent.email} onChange={(e) => handleParentChange(index, e)} />
                    <FormField
                      label="Tuteur légal"
                      name="tuteur_legal"
                      type="checkbox"
                      value={parent.tuteur_legal}
                      onChange={(e) => handleParentChange(index, e)}
                    />
                  </div>
                </div>
              ))
            )}
          </section>
        )}

        <div className="flex justify-end gap-3">
          <Link to={isEdit ? `/eleves/${id}` : '/eleves'} className="btn-secondary">
            Annuler
          </Link>
          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? 'Enregistrement...' : isEdit ? 'Enregistrer' : "Inscrire l'élève"}
          </button>
        </div>
      </form>
    </div>
  );
}
