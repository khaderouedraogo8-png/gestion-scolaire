import { useEffect, useState } from 'react';
import { configApi } from '../../services/api/config';
import { elevesApi } from '../../services/api/eleves';
import apiClient from '../../services/api/client';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';

export default function AppelMobile() {
  const toast = useToast();
  const [classes, setClasses] = useState([]);
  const [idClasse, setIdClasse] = useState('');
  const [eleves, setEleves] = useState([]);
  const [absents, setAbsents] = useState(new Set());
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    configApi.getClasses().then((d) => setClasses(Array.isArray(d) ? d : d.items || [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (!idClasse) return;
    elevesApi
      .list({ id_classe: idClasse, per_page: 200 })
      .then((d) => setEleves(d.items || d || []))
      .catch(() => toast.error('Impossible de charger les élèves'));
  }, [idClasse, toast]);

  const toggle = (id) => {
    setAbsents((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const submit = async () => {
    setSaving(true);
    const payload = {
      id_classe: idClasse,
      presents: eleves.filter((e) => !absents.has(e.id)).map((e) => e.id),
      absents: [...absents].map((id) => ({ id_eleve: id, type_absence: 'absence' })),
    };
    try {
      if (typeof navigator !== 'undefined' && navigator.onLine === false) {
        const { enqueueOffline } = await import('../../utils/offlineQueue');
        await enqueueOffline('appel', {
          url: '/api/absences/appel',
          method: 'POST',
          body: payload,
        });
        toast.success("Hors ligne — appel mis en file d'attente");
        setAbsents(new Set());
        return;
      }
      const { data } = await apiClient.post('/absences/appel', payload);
      toast.success(data.message || 'Appel enregistré');
      setAbsents(new Set());
    } catch {
      toast.error("Échec de l'appel");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Assiduité"
        title="Appel mobile"
        subtitle="Touchez un élève pour le marquer absent — envoi en un geste"
      />
      <div className="card-premium space-y-4">
        <label className="block text-sm font-medium text-encre">
          Classe
          <select
            className="mt-1 w-full rounded-lg border border-bordure px-3 py-2"
            value={idClasse}
            onChange={(e) => setIdClasse(e.target.value)}
          >
            <option value="">Choisir…</option>
            {classes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.libelle}
              </option>
            ))}
          </select>
        </label>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
          {eleves.map((e) => {
            const absent = absents.has(e.id);
            return (
              <button
                key={e.id}
                type="button"
                onClick={() => toggle(e.id)}
                className={`min-h-[56px] rounded-lg border px-3 py-3 text-left text-sm transition ${
                  absent
                    ? 'border-brique bg-brique/10 text-brique'
                    : 'border-bordure bg-blanc text-encre hover:border-or-cachet'
                }`}
              >
                <span className="font-medium">
                  {e.prenom} {e.nom}
                </span>
                <span className="mt-0.5 block text-xs opacity-70">
                  {absent ? 'Absent' : 'Présent'}
                </span>
              </button>
            );
          })}
        </div>
        {idClasse && (
          <button
            type="button"
            className="btn-primary"
            disabled={saving || eleves.length === 0}
            onClick={submit}
          >
            {saving ? 'Enregistrement…' : `Valider l'appel (${absents.size} absent(s))`}
          </button>
        )}
      </div>
    </div>
  );
}
