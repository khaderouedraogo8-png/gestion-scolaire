import { useCallback, useEffect, useState } from 'react';
import { vieScolaireApi } from '../../services/api/vieScolaire';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function Bibliotheque() {
  const toast = useToast();
  const [livres, setLivres] = useState([]);
  const [prets, setPrets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [livre, setLivre] = useState({ titre: '', auteur: '', isbn: '', exemplaires: '1' });
  const [pret, setPret] = useState({
    id_livre: '',
    id_eleve: '',
    date_pret: new Date().toISOString().slice(0, 10),
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [l, p] = await Promise.all([
        vieScolaireApi.listBibliothequeLivres(),
        vieScolaireApi.listBibliothequePrets(),
      ]);
      setLivres(Array.isArray(l) ? l : []);
      setPrets(Array.isArray(p) ? p : []);
    } catch {
      toast.error('Impossible de charger la bibliothèque');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const createLivre = async (e) => {
    e.preventDefault();
    try {
      await vieScolaireApi.createBibliothequeLivre({
        ...livre,
        exemplaires: Number(livre.exemplaires) || 1,
      });
      toast.success('Livre ajouté');
      setLivre({ titre: '', auteur: '', isbn: '', exemplaires: '1' });
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const createPret = async (e) => {
    e.preventDefault();
    try {
      await vieScolaireApi.createBibliothequePret(pret);
      toast.success('Prêt enregistré');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const retour = async (id) => {
    try {
      await vieScolaireApi.retourBibliothequePret(id);
      toast.success('Retour enregistré');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Vie scolaire" title="Bibliothèque" subtitle="Catalogue et prêts" />

      <form onSubmit={createLivre} className="card-premium grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4">
        <FormField label="Titre" name="titre" value={livre.titre} onChange={(e) => setLivre((f) => ({ ...f, titre: e.target.value }))} required />
        <FormField label="Auteur" name="auteur" value={livre.auteur} onChange={(e) => setLivre((f) => ({ ...f, auteur: e.target.value }))} />
        <FormField label="ISBN" name="isbn" value={livre.isbn} onChange={(e) => setLivre((f) => ({ ...f, isbn: e.target.value }))} />
        <FormField label="Exemplaires" name="exemplaires" value={livre.exemplaires} onChange={(e) => setLivre((f) => ({ ...f, exemplaires: e.target.value }))} />
        <button type="submit" className="btn-primary w-fit">Ajouter un livre</button>
      </form>

      <Table
        columns={[
          { key: 'titre', header: 'Titre' },
          { key: 'auteur', header: 'Auteur', render: (r) => r.auteur || '—' },
          { key: 'exemplaires', header: 'Exemplaires', render: (r) => r.exemplaires ?? r.quantite ?? '—' },
        ]}
        data={livres}
        loading={loading}
        emptyMessage="Aucun livre."
      />

      <form onSubmit={createPret} className="card-premium grid gap-3 p-5 sm:grid-cols-4">
        <FormField
          label="Livre"
          name="id_livre"
          type="select"
          value={pret.id_livre}
          onChange={(e) => setPret((f) => ({ ...f, id_livre: e.target.value }))}
          options={livres.map((l) => ({ value: String(l.id), label: l.titre }))}
        />
        <FormField label="ID élève" name="id_eleve" value={pret.id_eleve} onChange={(e) => setPret((f) => ({ ...f, id_eleve: e.target.value }))} required />
        <FormField label="Date prêt" name="date_pret" type="date" value={pret.date_pret} onChange={(e) => setPret((f) => ({ ...f, date_pret: e.target.value }))} required />
        <div className="flex items-end">
          <button type="submit" className="btn-secondary w-full">Emprunter</button>
        </div>
      </form>

      <Table
        columns={[
          { key: 'id_livre', header: 'Livre', render: (r) => String(r.id_livre).slice(0, 8) },
          { key: 'id_eleve', header: 'Élève', render: (r) => String(r.id_eleve).slice(0, 8) },
          { key: 'date_pret', header: 'Prêt' },
          {
            key: 'actions',
            header: '',
            render: (r) =>
              r.statut === 'en_cours' ? (
                <button type="button" className="text-sm font-medium text-or-cachet hover:underline" onClick={() => retour(r.id)}>
                  Retour
                </button>
              ) : (
                r.statut || 'Rendu'
              ),
          },
        ]}
        data={prets}
        loading={false}
        emptyMessage="Aucun prêt."
      />
    </div>
  );
}
