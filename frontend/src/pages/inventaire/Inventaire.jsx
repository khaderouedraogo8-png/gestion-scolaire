import { useCallback, useEffect, useState } from 'react';
import { inventaireApi } from '../../services/api/inventaire';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function Inventaire() {
  const toast = useToast();
  const [articles, setArticles] = useState([]);
  const [mouvements, setMouvements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [article, setArticle] = useState({
    code: '',
    libelle: '',
    categorie: '',
    quantite: '0',
    seuil_alerte: '0',
    unite: 'u',
  });
  const [mouvement, setMouvement] = useState({
    id_article: '',
    type_mouvement: 'entree',
    quantite: '1',
    motif: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [a, m] = await Promise.all([
        inventaireApi.listArticles(),
        inventaireApi.listMouvements(),
      ]);
      setArticles(Array.isArray(a) ? a : []);
      setMouvements(Array.isArray(m) ? m : []);
    } catch {
      toast.error('Impossible de charger l’inventaire');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const createArticle = async (e) => {
    e.preventDefault();
    try {
      await inventaireApi.createArticle({
        ...article,
        quantite: Number(article.quantite) || 0,
        seuil_alerte: Number(article.seuil_alerte) || 0,
      });
      toast.success('Article créé');
      setArticle({ code: '', libelle: '', categorie: '', quantite: '0', seuil_alerte: '0', unite: 'u' });
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const createMouvement = async (e) => {
    e.preventDefault();
    try {
      await inventaireApi.createMouvement({
        ...mouvement,
        quantite: Number(mouvement.quantite) || 1,
      });
      toast.success('Mouvement enregistré');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Administration" title="Inventaire" subtitle="Articles et mouvements de stock" />

      <form onSubmit={createArticle} className="card-premium grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-3">
        <FormField label="Code" name="code" value={article.code} onChange={(e) => setArticle((f) => ({ ...f, code: e.target.value }))} required />
        <FormField label="Libellé" name="libelle" value={article.libelle} onChange={(e) => setArticle((f) => ({ ...f, libelle: e.target.value }))} required />
        <FormField label="Catégorie" name="categorie" value={article.categorie} onChange={(e) => setArticle((f) => ({ ...f, categorie: e.target.value }))} />
        <FormField label="Quantité" name="quantite" value={article.quantite} onChange={(e) => setArticle((f) => ({ ...f, quantite: e.target.value }))} />
        <FormField label="Seuil alerte" name="seuil_alerte" value={article.seuil_alerte} onChange={(e) => setArticle((f) => ({ ...f, seuil_alerte: e.target.value }))} />
        <FormField label="Unité" name="unite" value={article.unite} onChange={(e) => setArticle((f) => ({ ...f, unite: e.target.value }))} />
        <button type="submit" className="btn-primary w-fit">Ajouter</button>
      </form>

      <Table
        columns={[
          { key: 'code', header: 'Code' },
          { key: 'libelle', header: 'Libellé' },
          { key: 'categorie', header: 'Catégorie', render: (r) => r.categorie || '—' },
          {
            key: 'quantite',
            header: 'Stock',
            render: (r) => (
              <span className={r.quantite <= (r.seuil_alerte || 0) ? 'font-semibold text-brique' : ''}>
                {r.quantite} {r.unite || ''}
              </span>
            ),
          },
        ]}
        data={articles}
        loading={loading}
        emptyMessage="Aucun article."
      />

      <form onSubmit={createMouvement} className="card-premium grid gap-3 p-5 sm:grid-cols-4">
        <FormField
          label="Article"
          name="id_article"
          type="select"
          value={mouvement.id_article}
          onChange={(e) => setMouvement((f) => ({ ...f, id_article: e.target.value }))}
          options={articles.map((a) => ({ value: String(a.id), label: `${a.code} — ${a.libelle}` }))}
        />
        <FormField
          label="Type"
          name="type_mouvement"
          type="select"
          value={mouvement.type_mouvement}
          onChange={(e) => setMouvement((f) => ({ ...f, type_mouvement: e.target.value }))}
          options={[
            { value: 'entree', label: 'Entrée' },
            { value: 'sortie', label: 'Sortie' },
            { value: 'ajustement', label: 'Ajustement' },
          ]}
        />
        <FormField label="Quantité" name="quantite" value={mouvement.quantite} onChange={(e) => setMouvement((f) => ({ ...f, quantite: e.target.value }))} />
        <div className="flex items-end">
          <button type="submit" className="btn-secondary w-full">Mouvement</button>
        </div>
      </form>

      <Table
        columns={[
          { key: 'type_mouvement', header: 'Type' },
          { key: 'quantite', header: 'Qté' },
          { key: 'motif', header: 'Motif', render: (r) => r.motif || '—' },
          {
            key: 'date_mouvement',
            header: 'Date',
            render: (r) => (r.date_mouvement ? new Date(r.date_mouvement).toLocaleString('fr-FR') : '—'),
          },
        ]}
        data={mouvements.slice(0, 40)}
        loading={false}
        emptyMessage="Aucun mouvement."
      />
    </div>
  );
}
