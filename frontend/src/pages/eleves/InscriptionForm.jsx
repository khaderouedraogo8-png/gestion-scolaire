import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { elevesApi } from '../../services/api/eleves';
import { configApi } from '../../services/api/config';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function InscriptionForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();

  const [eleve, setEleve] = useState(null);
  const [annees, setAnnees] = useState([]);
  const [classes, setClasses] = useState([]);
  const [form, setForm] = useState({
    id_annee: '',
    id_classe: '',
    statut: 'inscrit',
    est_boursier: false,
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const [eleveData, anneesData, classesData] = await Promise.all([
          elevesApi.get(id),
          configApi.listAnnees(),
          configApi.listClasses(),
        ]);
        setEleve(eleveData);
        const anneeList = anneesData.items || anneesData || [];
        setAnnees(anneeList);
        setClasses(classesData.items || classesData || []);
        const activeAnnee = anneeList.find((a) => a.est_active);
        if (activeAnnee) setForm((prev) => ({ ...prev, id_annee: String(activeAnnee.id) }));
      } catch {
        toast.error('Erreur lors du chargement');
        navigate(`/eleves/${id}`);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id, navigate, toast]);

  const filteredClasses = useMemo(
    () => classes.filter((c) => !form.id_annee || String(c.id_annee) === String(form.id_annee)),
    [classes, form.id_annee]
  );

  const validate = () => {
    const newErrors = {};
    if (!form.id_annee) newErrors.id_annee = "L'année scolaire est requise";
    if (!form.id_classe) newErrors.id_classe = 'La classe est requise';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
      ...(name === 'id_annee' ? { id_classe: '' } : {}),
    }));
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setSaving(true);
    try {
      await elevesApi.inscrire(id, {
        id_annee: form.id_annee,
        id_classe: form.id_classe,
        statut: form.statut,
        est_boursier: form.est_boursier,
      });
      toast.success('Inscription enregistrée avec succès');
      navigate(`/eleves/${id}`);
    } catch (err) {
      toast.error(err.response?.data?.message || "Erreur lors de l'inscription");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-or-cachet-clair border-t-or-cachet" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <div>
        <Link to={`/eleves/${id}`} className="text-sm text-or-cachet hover:underline">
          ← Retour à la fiche
        </Link>
        <h1 className="mt-2 page-title">Réinscription</h1>
        <p className="page-subtitle">
          {eleve?.prenom} {eleve?.nom} — {eleve?.matricule}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="card space-y-5">
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
            label: a.libelle,
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

        <FormField
          label="Statut"
          name="statut"
          type="select"
          value={form.statut}
          onChange={handleChange}
          options={[
            { value: 'inscrit', label: 'Inscrit' },
            { value: 'reinscrit', label: 'Réinscrit' },
            { value: 'suspendu', label: 'Suspendu' },
            { value: 'abandon', label: 'Abandon' },
            { value: 'diplome', label: 'Diplômé' },
          ]}
        />

        <FormField
          label="Élève boursier"
          name="est_boursier"
          type="checkbox"
          value={form.est_boursier}
          onChange={handleChange}
        />

        <div className="flex justify-end gap-3 border-t border-bordure pt-5">
          <Link to={`/eleves/${id}`} className="btn-secondary">
            Annuler
          </Link>
          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? 'Enregistrement...' : "Confirmer l'inscription"}
          </button>
        </div>
      </form>
    </div>
  );
}
