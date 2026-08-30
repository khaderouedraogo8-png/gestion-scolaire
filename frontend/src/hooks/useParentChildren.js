import { useCallback, useEffect, useState } from 'react';
import { configApi } from '../services/api/config';
import { elevesApi } from '../services/api/eleves';

const STORAGE_KEY = 'parent_selected_eleve_id';

export default function useParentChildren() {
  const [children, setChildren] = useState([]);
  const [idAnnee, setIdAnnee] = useState('');
  const [selectedId, setSelectedId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let activeId = '';
      try {
        const annees = await configApi.listAnnees();
        const anneeList = annees.items || annees || [];
        const active = anneeList.find((a) => a.est_active);
        if (active) activeId = active.id;
      } catch {
        /* parent peut ne pas avoir accès à /annees — le backend utilise l'année active */
      }
      setIdAnnee(activeId);

      const data = await elevesApi.list({
        ...(activeId ? { id_annee: activeId } : {}),
        per_page: 50,
      });
      const items = data.items || [];
      setChildren(items);
      if (!activeId && items[0]?.id_annee) {
        setIdAnnee(String(items[0].id_annee));
      }

      const stored = localStorage.getItem(STORAGE_KEY);
      const pick =
        items.find((e) => String(e.id) === stored) ||
        items[0] ||
        null;
      setSelectedId(pick ? String(pick.id) : '');
    } catch {
      setError('Impossible de charger la liste de vos enfants.');
      setChildren([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const selectChild = (id) => {
    setSelectedId(String(id));
    localStorage.setItem(STORAGE_KEY, String(id));
  };

  const selectedChild = children.find((c) => String(c.id) === selectedId) || null;

  return {
    children,
    selectedChild,
    selectedId,
    selectChild,
    idAnnee,
    loading,
    error,
    reload: load,
  };
}
