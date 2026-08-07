import { useCallback, useEffect, useState } from 'react';
import { notesApi } from '../../services/api/notes';
import { configApi } from '../../services/api/config';
import Table from '../../components/Table';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';

const STATUT_MAP = {
  brouillon: { class: 'badge-neutral', label: 'Brouillon' },
  valide: { class: 'badge-info', label: 'Validé' },
  publie: { class: 'badge-success', label: 'Publié' },
};

export default function BulletinList() {
  const toast = useToast();
  const { isAdmin } = useAuth();

  const [bulletins, setBulletins] = useState([]);
  const [classes, setClasses] = useState([]);
  const [trimestres, setTrimestres] = useState([]);
  const [loading, setLoading] = useState(true);
  const [classeFilter, setClasseFilter] = useState('');
  const [trimestreFilter, setTrimestreFilter] = useState('');
  const [genModal, setGenModal] = useState(false);
  const [genForm, setGenForm] = useState({ id_classe: '', id_trimestre: '' });
  const [generating, setGenerating] = useState(false);
  const [appModal, setAppModal] = useState(false);
  const [appForm, setAppForm] = useState({ id: '', appreciation_generale: '' });
  const [savingApp, setSavingApp] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await notesApi.listBulletins({
        id_classe: classeFilter || undefined,
        trimestre: trimestreFilter || undefined,
      });
      setBulletins(data.items || []);
    } catch {
      toast.error('Erreur lors du chargement des bulletins');
    } finally {
      setLoading(false);
    }
  }, [classeFilter, trimestreFilter, toast]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const init = async () => {
      try {
        const [classesData, anneesData] = await Promise.all([
          configApi.listClasses(),
          configApi.listAnnees(),
        ]);
        setClasses(classesData.items || classesData || []);
        const anneeList = anneesData.items || anneesData || [];
        const active = anneeList.find((a) => a.est_active);
        if (active) {
          const trims = await configApi.listTrimestres(active.id);
          const trimList = trims.items || trims || [];
          setTrimestres(trimList);
          if (trimList.length) {
            setGenForm((f) => ({ ...f, id_trimestre: String(trimList[0].id) }));
          }
        }
      } catch {
        /* ignore */
      }
    };
    init();
  }, []);

  const handleGenerer = async (e) => {
    e.preventDefault();
    setGenerating(true);
    try {
      const result = await notesApi.genererBulletinsClasse({
        id_classe: genForm.id_classe,
        id_trimestre: genForm.id_trimestre,
      });
      const count = result.total || result.items?.length || 0;
      toast.success(`${count} bulletin(s) généré(s) en brouillon`);
      if (result.errors?.length) {
        toast.warning(`${result.errors.length} élève(s) ignoré(s) (pas de notes)`);
      }
      setGenModal(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur lors de la génération');
    } finally {
      setGenerating(false);
    }
  };

  const handleValider = async (id) => {
    try {
      await notesApi.validerBulletin(id);
      toast.success('Bulletin validé');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const handlePublier = async (id) => {
    try {
      await notesApi.publierBulletin(id);
      toast.success('Bulletin publié — visible aux parents');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const handlePdf = async (id) => {
    try {
      const blob = await notesApi.getBulletinPdf(id);
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    } catch (err) {
      toast.error(err.response?.data?.message || 'PDF indisponible');
    }
  };

  const openAppreciation = (bulletin) => {
    setAppForm({
      id: bulletin.id,
      appreciation_generale: bulletin.appreciation_generale || '',
    });
    setAppModal(true);
  };

  const handleSaveAppreciation = async (e) => {
    e.preventDefault();
    setSavingApp(true);
    try {
      await notesApi.updateBulletinAppreciation(appForm.id, appForm.appreciation_generale);
      toast.success('Appréciation enregistrée');
      setAppModal(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    } finally {
      setSavingApp(false);
    }
  };

  const columns = [
    {
      key: 'eleve',
      header: 'Élève',
      render: (r) => (
        <div>
          <p className="font-medium">
            {r.prenom} {r.nom}
          </p>
          <p className="text-xs text-slate-500">{r.matricule}</p>
        </div>
      ),
    },
    { key: 'classe', header: 'Classe', render: (r) => r.classe_nom || '—' },
    { key: 'trimestre', header: 'Trimestre', render: (r) => (r.trimestre ? `T${r.trimestre}` : '—') },
    {
      key: 'moyenne',
      header: 'Moyenne',
      render: (r) => (r.moyenne != null ? `${Number(r.moyenne).toFixed(2)}/20` : '—'),
    },
    {
      key: 'rang',
      header: 'Rang',
      render: (r) => (r.rang != null ? `${r.rang}${r.rang === 1 ? 'er' : 'e'}` : '—'),
    },
    {
      key: 'statut',
      header: 'Statut',
      render: (r) => {
        const s = STATUT_MAP[r.statut] || STATUT_MAP.brouillon;
        return <span className={s.class}>{s.label}</span>;
      },
    },
    {
      key: 'actions',
      header: '',
      render: (r) => (
        <div className="flex flex-wrap gap-2">
          {isAdmin && r.statut !== 'publie' && (
            <button
              type="button"
              onClick={() => openAppreciation(r)}
              className="text-xs text-slate-600 hover:underline"
            >
              Appréciation
            </button>
          )}
          {r.statut === 'publie' && (
            <button type="button" onClick={() => handlePdf(r.id)} className="text-xs text-primary-600 hover:underline">
              PDF
            </button>
          )}
          {isAdmin && r.statut === 'brouillon' && (
            <button
              type="button"
              onClick={() => handleValider(r.id)}
              className="text-xs text-blue-600 hover:underline"
            >
              Valider
            </button>
          )}
          {isAdmin && r.statut === 'valide' && (
            <button
              type="button"
              onClick={() => handlePublier(r.id)}
              className="text-xs text-emerald-600 hover:underline"
            >
              Publier
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Bulletins</h1>
          <p className="text-sm text-slate-500">
            Workflow : brouillon → validé (directeur) → publié (parents)
          </p>
        </div>
        {isAdmin && (
          <button type="button" onClick={() => setGenModal(true)} className="btn-primary">
            Générer les bulletins
          </button>
        )}
      </div>

      <Table
        columns={columns}
        data={bulletins}
        loading={loading}
        filters={
          <>
            <select
              value={classeFilter}
              onChange={(e) => setClasseFilter(e.target.value)}
              className="input w-auto"
            >
              <option value="">Toutes les classes</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.libelle || c.nom}
                </option>
              ))}
            </select>
            <select
              value={trimestreFilter}
              onChange={(e) => setTrimestreFilter(e.target.value)}
              className="input w-auto"
            >
              <option value="">Tous les trimestres</option>
              <option value="1">Trimestre 1</option>
              <option value="2">Trimestre 2</option>
              <option value="3">Trimestre 3</option>
            </select>
          </>
        }
        emptyMessage="Aucun bulletin — saisissez des notes puis générez les bulletins"
      />

      <Modal
        isOpen={genModal}
        onClose={() => setGenModal(false)}
        title="Générer les bulletins"
        footer={
          <>
            <button type="button" onClick={() => setGenModal(false)} className="btn-secondary">
              Annuler
            </button>
            <button type="submit" form="gen-form" disabled={generating} className="btn-primary">
              {generating ? 'Génération...' : 'Générer'}
            </button>
          </>
        }
      >
        <form id="gen-form" onSubmit={handleGenerer} className="space-y-4">
          <FormField
            label="Classe"
            name="id_classe"
            type="select"
            value={genForm.id_classe}
            onChange={(e) => setGenForm({ ...genForm, id_classe: e.target.value })}
            required
            options={classes.map((c) => ({
              value: String(c.id),
              label: c.libelle || c.nom,
            }))}
          />
          <FormField
            label="Trimestre"
            name="id_trimestre"
            type="select"
            value={genForm.id_trimestre}
            onChange={(e) => setGenForm({ ...genForm, id_trimestre: e.target.value })}
            required
            options={trimestres.map((t) => ({
              value: String(t.id),
              label: `Trimestre ${t.numero}`,
            }))}
          />
          <p className="text-xs text-slate-500">
            Un bulletin en brouillon sera créé pour chaque élève inscrit dans la classe.
          </p>
        </form>
      </Modal>

      <Modal
        isOpen={appModal}
        onClose={() => setAppModal(false)}
        title="Appréciation générale"
        footer={
          <>
            <button type="button" onClick={() => setAppModal(false)} className="btn-secondary">
              Annuler
            </button>
            <button type="submit" form="app-form" disabled={savingApp} className="btn-primary">
              {savingApp ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          </>
        }
      >
        <form id="app-form" onSubmit={handleSaveAppreciation} className="space-y-4">
          <textarea
            className="input min-h-[160px] w-full"
            value={appForm.appreciation_generale}
            onChange={(e) => setAppForm({ ...appForm, appreciation_generale: e.target.value })}
            placeholder="Appréciation du conseil de classe…"
          />
          <p className="text-xs text-slate-500">
            Les incidents disciplinaires du trimestre sont injectés automatiquement à la génération.
          </p>
        </form>
      </Modal>
    </div>
  );
}
