import { useCallback, useEffect, useState } from 'react';
import { notesApi } from '../../services/api/notes';
import { configApi } from '../../services/api/config';
import Table from '../../components/Table';
import { emptyIcons } from '../../utils/emptyIcons';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';
import { formatBulletinRulesets } from '../../utils/bulletinRulesets';
import { formatMoyenneDisplay } from '../../utils/academicResultsDisplay';

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
  const [periodes, setPeriodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [classeFilter, setClasseFilter] = useState('');
  const [periodeFilter, setPeriodeFilter] = useState('');
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
        id_trimestre: periodeFilter || undefined,
      });
      setBulletins(data.items || []);
    } catch {
      toast.error('Erreur lors du chargement des bulletins');
    } finally {
      setLoading(false);
    }
  }, [classeFilter, periodeFilter, toast]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const init = async () => {
      try {
        const [classesData, anneesData, periodesData] = await Promise.all([
          configApi.listClasses(),
          configApi.listAnnees(),
          configApi.listPeriodes({ is_active: true }),
        ]);
        setClasses(classesData.items || classesData || []);
        const anneeList = anneesData.items || anneesData || [];
        const active = anneeList.find((a) => a.est_active);
        let periods = periodesData.items || periodesData || [];
        if (active) {
          const yearPeriods = periods.filter(
            (p) => String(p.id_annee) === String(active.id) || !p.id_annee
          );
          if (yearPeriods.length) periods = yearPeriods;
        }
        setPeriodes(periods);
        if (periods.length) {
          setGenForm((f) => ({ ...f, id_trimestre: String(periods[0].id) }));
        }
      } catch {
        toast.error('Impossible de charger les filtres (classes / périodes).');
      }
    };
    init();
  }, [toast]);

  const periodeLabel = (p) =>
    p.label || p.libelle || p.code || `Période ${p.sequence ?? p.numero ?? ''}`;

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
          <p className="text-xs text-texte-secondaire">{r.matricule}</p>
        </div>
      ),
    },
    { key: 'classe', header: 'Classe', render: (r) => r.classe_nom || '—' },
    {
      key: 'trimestre',
      header: 'Période',
      render: (r) => {
        const match = periodes.find((p) => String(p.id) === String(r.id_trimestre));
        if (match) return periodeLabel(match);
        return r.trimestre != null ? `T${r.trimestre}` : '—';
      },
    },
    {
      key: 'moyenne',
      header: 'Moyenne',
      render: (r) => formatMoyenneDisplay(r.moyenne, r.scale_max),
    },
    {
      key: 'rulesets',
      header: 'Règles',
      render: (r) => {
        const { label, title } = formatBulletinRulesets(r.rulesets_snapshot);
        return (
          <span className="text-xs text-texte-secondaire" title={title}>
            {label}
          </span>
        );
      },
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
              className="text-xs text-texte-secondaire hover:underline"
            >
              Appréciation
            </button>
          )}
          {r.statut === 'publie' && (
            <button type="button" onClick={() => handlePdf(r.id)} className="text-xs text-or-cachet hover:underline">
              PDF
            </button>
          )}
          {isAdmin && r.statut === 'brouillon' && (
            <button
              type="button"
              onClick={() => handleValider(r.id)}
              className="text-xs text-or-cachet hover:underline"
            >
              Valider
            </button>
          )}
          {isAdmin && r.statut === 'valide' && (
            <button
              type="button"
              onClick={() => handlePublier(r.id)}
              className="text-xs text-feuille hover:underline"
            >
              Publier
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Notes & bulletins"
        title="Bulletins"
        subtitle="Workflow : brouillon → validé (directeur) → publié (parents)"
        actions={
          isAdmin && (
            <button type="button" onClick={() => setGenModal(true)} className="btn-primary">
              Générer les bulletins
            </button>
          )
        }
      />

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
              value={periodeFilter}
              onChange={(e) => setPeriodeFilter(e.target.value)}
              className="input w-auto"
            >
              <option value="">Toutes les périodes</option>
              {periodes.map((p) => (
                <option key={p.id} value={p.id}>
                  {periodeLabel(p)}
                </option>
              ))}
            </select>
          </>
        }
        emptyIcon={emptyIcons.bulletins}
        emptyMessage="Aucun bulletin pour l'instant — saisissez des notes puis générez les bulletins."
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
            label="Période"
            name="id_trimestre"
            type="select"
            value={genForm.id_trimestre}
            onChange={(e) => setGenForm({ ...genForm, id_trimestre: e.target.value })}
            required
            options={periodes.map((t) => ({
              value: String(t.id),
              label: periodeLabel(t),
            }))}
          />
          <p className="text-xs text-texte-secondaire">
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
          <p className="text-xs text-texte-secondaire">
            Les incidents disciplinaires du trimestre sont injectés automatiquement à la génération.
          </p>
        </form>
      </Modal>
    </div>
  );
}
