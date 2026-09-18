import { useCallback, useEffect, useState } from 'react';
import { elearningApi } from '../../services/api/elearning';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';

const TYPES = [
  { value: 'lien', label: 'Lien' },
  { value: 'pdf', label: 'PDF' },
  { value: 'video', label: 'Vidéo' },
  { value: 'document', label: 'Document' },
];

export default function Ressources() {
  const toast = useToast();
  const { isEnseignant, isAdmin } = useAuth();
  const canWrite = isEnseignant || isAdmin;
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    titre: '',
    type_ressource: 'lien',
    url: '',
    id_classe: '',
    description: '',
    publie: true,
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await elearningApi.listRessources();
      setRows(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Impossible de charger les ressources');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const create = async (e) => {
    e.preventDefault();
    try {
      await elearningApi.createRessource({
        titre: form.titre,
        type_ressource: form.type_ressource,
        url: form.url || null,
        id_classe: form.id_classe || null,
        description: form.description || null,
        publie: form.publie,
      });
      toast.success('Ressource publiée');
      setForm({
        titre: '',
        type_ressource: 'lien',
        url: '',
        id_classe: '',
        description: '',
        publie: true,
      });
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="E-learning"
        title="Ressources"
        subtitle="Cours, PDF et liens partagés aux classes"
      />

      {canWrite && (
        <form onSubmit={create} className="card-premium grid gap-3 p-5 sm:grid-cols-2">
          <FormField
            label="Titre"
            name="titre"
            value={form.titre}
            onChange={(e) => setForm((f) => ({ ...f, titre: e.target.value }))}
            required
          />
          <FormField
            label="Type"
            name="type_ressource"
            type="select"
            value={form.type_ressource}
            onChange={(e) => setForm((f) => ({ ...f, type_ressource: e.target.value }))}
            options={TYPES}
          />
          <FormField
            label="URL (https…)"
            name="url"
            value={form.url}
            onChange={(e) => setForm((f) => ({ ...f, url: e.target.value }))}
          />
          <FormField
            label="ID classe"
            name="id_classe"
            value={form.id_classe}
            onChange={(e) => setForm((f) => ({ ...f, id_classe: e.target.value }))}
          />
          <FormField
            label="Description"
            name="description"
            type="textarea"
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          />
          <button type="submit" className="btn-primary w-fit">
            Publier
          </button>
        </form>
      )}

      <Table
        columns={[
          { key: 'titre', header: 'Titre' },
          { key: 'type_ressource', header: 'Type' },
          {
            key: 'url',
            header: 'Lien',
            render: (r) =>
              r.url ? (
                <a href={r.url} target="_blank" rel="noreferrer" className="text-or-cachet underline">
                  Ouvrir
                </a>
              ) : (
                '—'
              ),
          },
          { key: 'publie', header: 'Publié', render: (r) => (r.publie ? 'Oui' : 'Non') },
        ]}
        data={rows}
        loading={loading}
        emptyMessage="Aucune ressource."
      />
    </div>
  );
}
