import { useCallback, useEffect, useState } from 'react';
import { elearningApi } from '../../services/api/elearning';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';

export default function Remises() {
  const toast = useToast();
  const { isEnseignant, isAdmin, user } = useAuth();
  const canGrade = isEnseignant || isAdmin;
  const isEleve = user?.role === 'eleve';
  const [rows, setRows] = useState([]);
  const [devoirs, setDevoirs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ id_devoir: '', id_eleve: '', contenu: '', fichier_url: '' });
  const [grade, setGrade] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [remises, list] = await Promise.all([
        elearningApi.listRemises(),
        elearningApi.listDevoirs(),
      ]);
      setRows(Array.isArray(remises) ? remises : []);
      setDevoirs(Array.isArray(list) ? list : []);
    } catch {
      toast.error('Impossible de charger les remises');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const submit = async (e) => {
    e.preventDefault();
    try {
      await elearningApi.submitRemise({
        id_devoir: form.id_devoir,
        ...(isEleve ? {} : { id_eleve: form.id_eleve }),
        contenu: form.contenu || null,
        fichier_url: form.fichier_url || null,
      });
      toast.success('Remise enregistrée');
      setForm({ id_devoir: '', id_eleve: '', contenu: '', fichier_url: '' });
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const noteOne = async (id) => {
    const g = grade[id];
    if (!g?.note) {
      toast.error('Note requise');
      return;
    }
    try {
      await elearningApi.noteRemise(id, { note: g.note, commentaire: g.commentaire || null });
      toast.success('Remise notée');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur notation');
    }
  };

  const titreDevoir = (id) => devoirs.find((d) => d.id === id)?.titre || id?.slice?.(0, 8) || '—';

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="E-learning"
        title="Remises"
        subtitle="Dépôt des travaux et notation enseignant"
      />

      {(isEleve || canGrade) && (
        <form onSubmit={submit} className="card-premium grid gap-3 p-5 sm:grid-cols-2">
          <FormField
            label="Devoir"
            name="id_devoir"
            type="select"
            value={form.id_devoir}
            onChange={(e) => setForm((f) => ({ ...f, id_devoir: e.target.value }))}
            required
            options={devoirs.map((d) => ({ value: d.id, label: d.titre }))}
          />
          {!isEleve && (
            <FormField
              label="ID élève"
              name="id_eleve"
              value={form.id_eleve}
              onChange={(e) => setForm((f) => ({ ...f, id_eleve: e.target.value }))}
              required
            />
          )}
          <FormField
            label="Contenu / réponse"
            name="contenu"
            type="textarea"
            value={form.contenu}
            onChange={(e) => setForm((f) => ({ ...f, contenu: e.target.value }))}
          />
          <FormField
            label="Lien fichier (URL)"
            name="fichier_url"
            value={form.fichier_url}
            onChange={(e) => setForm((f) => ({ ...f, fichier_url: e.target.value }))}
          />
          <button type="submit" className="btn-primary w-fit">
            Déposer
          </button>
        </form>
      )}

      <Table
        columns={[
          { key: 'id_devoir', header: 'Devoir', render: (r) => titreDevoir(r.id_devoir) },
          { key: 'statut', header: 'Statut' },
          {
            key: 'note',
            header: 'Note',
            render: (r) => (r.note != null ? r.note : '—'),
          },
          {
            key: 'contenu',
            header: 'Aperçu',
            render: (r) => (r.contenu ? String(r.contenu).slice(0, 50) : r.fichier_url || '—'),
          },
          ...(canGrade
            ? [
                {
                  key: 'actions',
                  header: 'Noter',
                  render: (r) => (
                    <div className="flex flex-wrap items-center gap-2">
                      <input
                        className="input-premium w-16"
                        placeholder="/20"
                        value={grade[r.id]?.note || ''}
                        onChange={(e) =>
                          setGrade((g) => ({ ...g, [r.id]: { ...g[r.id], note: e.target.value } }))
                        }
                      />
                      <button type="button" className="btn-secondary text-xs" onClick={() => noteOne(r.id)}>
                        OK
                      </button>
                    </div>
                  ),
                },
              ]
            : []),
        ]}
        data={rows}
        loading={loading}
        emptyMessage="Aucune remise."
      />
    </div>
  );
}
