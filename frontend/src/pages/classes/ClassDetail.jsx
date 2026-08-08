import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import Breadcrumb from '../../components/Breadcrumb';
import Table from '../../components/Table';
import Badge from '../../components/Badge';
import FormField from '../../components/FormField';
import { configApi } from '../../services/api/config';
import { elevesApi } from '../../services/api/eleves';
import { absencesApi } from '../../services/api/absences';
import { financeApi } from '../../services/api/finance';
import { notesApi } from '../../services/api/notes';
import { pedagogieApi, downloadBlob } from '../../services/api/pedagogie';
import { emploiApi } from '../../services/api/emploi';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';
import { cycleLabel, findClassBySlug } from '../../utils/classNavigation';

const TABS = [
  { id: 'eleves', label: 'Élèves' },
  { id: 'devoirs', label: 'Devoirs' },
  { id: 'compositions', label: 'Compositions' },
  { id: 'cahier', label: 'Cahier de texte' },
  { id: 'absences', label: 'Absences' },
  { id: 'scolarite', label: 'Scolarité' },
  { id: 'notes', label: 'Notes & Bulletins' },
];

const JOURS = [
  { value: 1, label: 'Lundi' },
  { value: 2, label: 'Mardi' },
  { value: 3, label: 'Mercredi' },
  { value: 4, label: 'Jeudi' },
  { value: 5, label: 'Vendredi' },
  { value: 6, label: 'Samedi' },
  { value: 7, label: 'Dimanche' },
];

function JustifBadge({ justifiee }) {
  return justifiee ? <Badge variant="success">Justifiée</Badge> : <Badge variant="warning">Non justifiée</Badge>;
}

async function openPdf(apiCall, filename, toast) {
  try {
    const { data } = await apiCall();
    downloadBlob(data, filename);
  } catch (err) {
    toast.error(err.response?.data?.message || 'Erreur lors de la génération PDF');
  }
}

export default function ClassDetail() {
  const { cycle, classeSlug } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { user } = useAuth();
  const canEdit = user?.role !== 'parent';

  const activeTab = searchParams.get('onglet') || 'eleves';
  const [classe, setClasse] = useState(null);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [loadingTab, setLoadingTab] = useState(true);
  const [eleves, setEleves] = useState([]);
  const [absences, setAbsences] = useState([]);
  const [arrieres, setArrieres] = useState([]);
  const [evaluations, setEvaluations] = useState([]);
  const [compositions, setCompositions] = useState([]);
  const [programmeDevoirs, setProgrammeDevoirs] = useState([]);
  const [chargeStats, setChargeStats] = useState(null);
  const [seances, setSeances] = useState([]);
  const [enseignants, setEnseignants] = useState([]);
  const [matieres, setMatieres] = useState([]);
  const [trimestres, setTrimestres] = useState([]);
  const [idAnnee, setIdAnnee] = useState('');
  const [idTrimestrePdf, setIdTrimestrePdf] = useState('');
  const [ficheEvalId, setFicheEvalId] = useState('');
  const [dateAppel, setDateAppel] = useState(new Date().toISOString().slice(0, 10));
  const [devoirForm, setDevoirForm] = useState({
    jour_semaine: 1,
    id_matiere: '',
    frequence: 'hebdomadaire',
    note: '',
  });
  const [seanceForm, setSeanceForm] = useState({
    id_matiere: '',
    id_enseignant: '',
    date_seance: new Date().toISOString().slice(0, 10),
    contenu: '',
  });

  useEffect(() => {
    let cancelled = false;

    const loadMeta = async () => {
      setLoadingMeta(true);
      try {
        const annees = await configApi.listAnnees();
        const list = Array.isArray(annees) ? annees : annees.items || [];
        const active = list.find((a) => a.est_active);
        if (!active) return;
        if (!cancelled) {
          setIdAnnee(active.id);
          const trim = await configApi.listTrimestres(active.id);
          const trimList = Array.isArray(trim) ? trim : trim.items || [];
          setTrimestres(trimList);
          if (trimList[0]) setIdTrimestrePdf(trimList[0].id);
        }

        const data = await configApi.listClassesNav({
          cycle,
          id_annee: active.id,
          enriched: true,
        });
        const found = findClassBySlug(Array.isArray(data) ? data : [], classeSlug);
        if (!cancelled) setClasse(found || null);
      } catch {
        if (!cancelled) toast.error('Impossible de charger la classe.');
      } finally {
        if (!cancelled) setLoadingMeta(false);
      }
    };

    loadMeta();
    return () => {
      cancelled = true;
    };
  }, [cycle, classeSlug, toast]);

  const loadTab = useCallback(async () => {
    if (!classe?.id) return;
    setLoadingTab(true);
    try {
      if (activeTab === 'eleves') {
        const data = await elevesApi.list({
          id_classe: classe.id,
          id_annee: idAnnee || undefined,
          per_page: 100,
        });
        setEleves(data.items || []);
      } else if (activeTab === 'absences') {
        const data = await absencesApi.list({ id_classe: classe.id });
        setAbsences(Array.isArray(data) ? data : data.items || []);
      } else if (activeTab === 'scolarite') {
        if (!idAnnee) return;
        const data = await financeApi.listArrieres({ id_annee: idAnnee, id_classe: classe.id });
        setArrieres(Array.isArray(data) ? data : []);
      } else if (activeTab === 'notes') {
        const data = await notesApi.listEvaluations({ id_classe: classe.id });
        const list = Array.isArray(data) ? data : data.items || [];
        setEvaluations(list);
        if (list[0]) setFicheEvalId(list[0].id);
      } else if (activeTab === 'devoirs') {
        if (!idAnnee) return;
        const [prog, mats, charge] = await Promise.all([
          pedagogieApi.listProgrammeDevoirs({ id_classe: classe.id, id_annee: idAnnee }),
          notesApi.listMatieres(),
          pedagogieApi.getChargeTravail({
            id_classe: classe.id,
            id_annee: idAnnee,
            id_trimestre: idTrimestrePdf || undefined,
          }),
        ]);
        setProgrammeDevoirs(Array.isArray(prog) ? prog : []);
        setMatieres(Array.isArray(mats) ? mats : []);
        setChargeStats(charge);
      } else if (activeTab === 'compositions') {
        const data = await notesApi.listEvaluations({
          id_classe: classe.id,
          type_evaluation: 'examen',
        });
        setCompositions(Array.isArray(data) ? data : data.items || []);
      } else if (activeTab === 'cahier') {
        if (!idAnnee) return;
        const [seancesData, mats, ens] = await Promise.all([
          pedagogieApi.listSeances({ id_classe: classe.id, id_annee: idAnnee }),
          notesApi.listMatieres(),
          canEdit ? emploiApi.listEnseignants() : Promise.resolve([]),
        ]);
        setSeances(Array.isArray(seancesData) ? seancesData : []);
        setMatieres(Array.isArray(mats) ? mats : []);
        const ensList = Array.isArray(ens) ? ens : ens.items || [];
        setEnseignants(ensList);
        if (ensList[0] && !seanceForm.id_enseignant) {
          setSeanceForm((f) => ({ ...f, id_enseignant: ensList[0].id }));
        }
      }
    } catch {
      toast.error('Impossible de charger les données de cet onglet.');
    } finally {
      setLoadingTab(false);
    }
  }, [activeTab, classe?.id, idAnnee, idTrimestrePdf, canEdit, toast]);

  useEffect(() => {
    loadTab();
  }, [loadTab]);

  const setTab = (tabId) => {
    setSearchParams({ onglet: tabId });
  };

  const handleAddDevoir = async (e) => {
    e.preventDefault();
    if (!devoirForm.id_matiere || !idAnnee) return;
    try {
      await pedagogieApi.saveProgrammeDevoir({
        id_classe: classe.id,
        id_matiere: devoirForm.id_matiere,
        jour_semaine: Number(devoirForm.jour_semaine),
        frequence: devoirForm.frequence,
        note: devoirForm.note || null,
        id_annee: idAnnee,
      });
      toast.success('Devoir ajouté au programme');
      setDevoirForm({ jour_semaine: 1, id_matiere: '', frequence: 'hebdomadaire', note: '' });
      loadTab();
    } catch (err) {
      toast.error(err.response?.data?.message || "Erreur lors de l'enregistrement");
    }
  };

  const handleDeleteDevoir = async (id) => {
    try {
      await pedagogieApi.deleteProgrammeDevoir(id);
      toast.success('Entrée supprimée');
      loadTab();
    } catch {
      toast.error('Impossible de supprimer');
    }
  };

  const handlePublier = async (id) => {
    try {
      await notesApi.publierEvaluation(id);
      toast.success('Composition publiée');
      loadTab();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const handleAddSeance = async (e) => {
    e.preventDefault();
    if (!seanceForm.id_matiere || !seanceForm.id_enseignant || !idAnnee) return;
    try {
      await pedagogieApi.saveSeance({
        id_classe: classe.id,
        id_annee: idAnnee,
        ...seanceForm,
      });
      toast.success('Séance enregistrée');
      setSeanceForm((f) => ({ ...f, contenu: '' }));
      loadTab();
    } catch (err) {
      toast.error(err.response?.data?.message || "Erreur lors de l'enregistrement");
    }
  };

  const handleDeleteSeance = async (id) => {
    try {
      await pedagogieApi.deleteSeance(id);
      toast.success('Séance supprimée');
      loadTab();
    } catch {
      toast.error('Impossible de supprimer');
    }
  };

  const compositionsByTrimestre = useMemo(() => {
    const groups = {};
    compositions.forEach((c) => {
      const key = c.trimestre_numero || c.id_trimestre;
      if (!groups[key]) groups[key] = [];
      groups[key].push(c);
    });
    return groups;
  }, [compositions]);

  const breadcrumbItems = useMemo(
    () => [
      { label: 'Classes', to: '/classes' },
      { label: cycleLabel(cycle), to: `/classes/${cycle}` },
      { label: classe?.libelle || '…' },
    ],
    [cycle, classe?.libelle]
  );

  if (loadingMeta) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-or-cachet-clair border-t-or-cachet" />
      </div>
    );
  }

  if (!classe) {
    return (
      <div className="space-y-4">
        <Breadcrumb items={breadcrumbItems.slice(0, 2)} />
        <p className="text-sm text-texte-secondaire">Classe introuvable.</p>
        <Link to={`/classes/${cycle}`} className="btn-secondary inline-flex">
          Retour au cycle
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Breadcrumb items={breadcrumbItems} />
      <div>
        <h1 className="page-title">{classe.libelle}</h1>
        <p className="page-subtitle">{cycleLabel(cycle)}</p>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-bordure">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'border-b-2 border-or-cachet text-or-cachet'
                : 'text-texte-secondaire hover:text-encre'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'eleves' && (
        <>
          <div className="flex justify-end">
            <button
              type="button"
              className="btn-secondary text-sm"
              onClick={() =>
                openPdf(
                  () => pedagogieApi.pdfListeEleves({ id_classe: classe.id }),
                  `liste_${classe.libelle}.pdf`,
                  toast
                )
              }
            >
              Imprimer la liste
            </button>
          </div>
          <Table
            columns={[
              { key: 'matricule', header: 'Matricule' },
              { key: 'nom', header: 'Nom', render: (r) => `${r.prenom} ${r.nom}` },
              { key: 'statut', header: 'Statut' },
            ]}
            data={eleves}
            loading={loadingTab}
            emptyMessage="Aucun élève inscrit dans cette classe pour l'instant."
            onRowClick={(row) => navigate(`/eleves/${row.id}`)}
          />
        </>
      )}

      {activeTab === 'devoirs' && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="page-subtitle">Planning récurrent des devoirs attendus</p>
            <button
              type="button"
              className="btn-secondary text-sm"
              onClick={() =>
                openPdf(
                  () => pedagogieApi.pdfProgrammeDevoirs({ id_classe: classe.id, id_annee: idAnnee }),
                  `programme_devoirs_${classe.libelle}.pdf`,
                  toast
                )
              }
            >
              Imprimer le programme
            </button>
          </div>
          {canEdit && (
            <form onSubmit={handleAddDevoir} className="card grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              <FormField
                label="Jour"
                type="select"
                value={String(devoirForm.jour_semaine)}
                onChange={(e) => setDevoirForm({ ...devoirForm, jour_semaine: e.target.value })}
                options={JOURS.map((j) => ({ value: String(j.value), label: j.label }))}
                required
              />
              <FormField
                label="Matière"
                type="select"
                value={devoirForm.id_matiere}
                onChange={(e) => setDevoirForm({ ...devoirForm, id_matiere: e.target.value })}
                options={matieres.map((m) => ({ value: m.id, label: m.libelle }))}
                required
              />
              <FormField
                label="Fréquence"
                type="select"
                value={devoirForm.frequence}
                onChange={(e) => setDevoirForm({ ...devoirForm, frequence: e.target.value })}
                options={[
                  { value: 'hebdomadaire', label: 'Hebdomadaire' },
                  { value: 'quinzomadaire', label: 'Quinzomadaire' },
                ]}
              />
              <FormField
                label="Remarque"
                value={devoirForm.note}
                onChange={(e) => setDevoirForm({ ...devoirForm, note: e.target.value })}
              />
              <div className="flex items-end">
                <button type="submit" className="btn-primary w-full">
                  Ajouter
                </button>
              </div>
            </form>
          )}
          <Table
            columns={[
              { key: 'jour_libelle', header: 'Jour' },
              { key: 'matiere_nom', header: 'Matière' },
              { key: 'frequence', header: 'Fréquence' },
              { key: 'note', header: 'Remarque', render: (r) => r.note || '—' },
              ...(canEdit
                ? [
                    {
                      key: 'actions',
                      header: '',
                      render: (r) => (
                        <button
                          type="button"
                          className="text-xs text-brique hover:underline"
                          onClick={() => handleDeleteDevoir(r.id)}
                        >
                          Supprimer
                        </button>
                      ),
                    },
                  ]
                : []),
            ]}
            data={programmeDevoirs}
            loading={loadingTab}
            emptyMessage="Aucun devoir programmé pour cette classe."
          />
          {chargeStats && (
            <div className="card space-y-3">
              <h3 className="font-semibold text-encre">Charge de travail</h3>
              {chargeStats.alertes?.length > 0 ? (
                <ul className="space-y-1 text-sm text-brique">
                  {chargeStats.alertes.map((a) => (
                    <li key={a}>⚠ {a}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-texte-secondaire">Aucune surcharge détectée.</p>
              )}
            </div>
          )}
        </>
      )}

      {activeTab === 'compositions' && (
        <>
          <div className="flex flex-wrap items-end gap-3">
            <FormField
              label="Trimestre (PDF)"
              type="select"
              value={idTrimestrePdf}
              onChange={(e) => setIdTrimestrePdf(e.target.value)}
              options={trimestres.map((t) => ({
                value: t.id,
                label: `Trimestre ${t.numero}`,
              }))}
              className="max-w-xs"
            />
            <button
              type="button"
              className="btn-secondary text-sm"
              disabled={!idTrimestrePdf}
              onClick={() =>
                openPdf(
                  () =>
                    pedagogieApi.pdfCalendrierCompositions({
                      id_classe: classe.id,
                      id_trimestre: idTrimestrePdf,
                    }),
                  `compositions_${classe.libelle}.pdf`,
                  toast
                )
              }
            >
              Imprimer le calendrier
            </button>
            <button
              type="button"
              className="btn-primary text-sm"
              disabled={!idTrimestrePdf}
              onClick={() =>
                openPdf(
                  () =>
                    pedagogieApi.pdfProgrammeTrimestriel({
                      id_classe: classe.id,
                      id_trimestre: idTrimestrePdf,
                      id_annee: idAnnee,
                    }),
                  `programme_trimestriel_${classe.libelle}.pdf`,
                  toast
                )
              }
            >
              Export programme trimestriel
            </button>
          </div>
          {Object.entries(compositionsByTrimestre).map(([trim, items]) => (
            <div key={trim} className="space-y-2">
              <h2 className="font-semibold text-encre">Trimestre {trim}</h2>
              <Table
                columns={[
                  { key: 'date_evaluation', header: 'Date' },
                  { key: 'matiere_nom', header: 'Matière' },
                  { key: 'coefficient', header: 'Coef.' },
                  { key: 'libelle', header: 'Libellé', render: (r) => r.libelle || 'Composition' },
                  {
                    key: 'statut',
                    header: 'Statut',
                    render: (r) =>
                      r.statut_publication === 'publie' ? (
                        <Badge variant="success">Publiée</Badge>
                      ) : (
                        <Badge variant="warning">Brouillon</Badge>
                      ),
                  },
                  ...(canEdit
                    ? [
                        {
                          key: 'actions',
                          header: '',
                          render: (r) =>
                            r.statut_publication === 'brouillon' ? (
                              <button
                                type="button"
                                className="text-xs text-or-cachet hover:underline"
                                onClick={() => handlePublier(r.id)}
                              >
                                Publier
                              </button>
                            ) : null,
                        },
                      ]
                    : []),
                ]}
                data={items}
                loading={loadingTab}
                emptyMessage="Aucune composition."
              />
            </div>
          ))}
          {!loadingTab && compositions.length === 0 && (
            <p className="text-sm text-texte-secondaire">Aucune composition pour cette classe.</p>
          )}
        </>
      )}

      {activeTab === 'cahier' && (
        <>
          <p className="page-subtitle">Contenu des séances — trace pédagogique consultable par la direction et les parents</p>
          {canEdit && (
            <form onSubmit={handleAddSeance} className="card space-y-4">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <FormField
                  label="Date"
                  type="date"
                  value={seanceForm.date_seance}
                  onChange={(e) => setSeanceForm({ ...seanceForm, date_seance: e.target.value })}
                  required
                />
                <FormField
                  label="Matière"
                  type="select"
                  value={seanceForm.id_matiere}
                  onChange={(e) => setSeanceForm({ ...seanceForm, id_matiere: e.target.value })}
                  options={matieres.map((m) => ({ value: m.id, label: m.libelle }))}
                  required
                />
                <FormField
                  label="Enseignant"
                  type="select"
                  value={seanceForm.id_enseignant}
                  onChange={(e) => setSeanceForm({ ...seanceForm, id_enseignant: e.target.value })}
                  options={enseignants.map((e) => ({
                    value: e.id,
                    label: `${e.prenom} ${e.nom}`,
                  }))}
                  required
                />
              </div>
              <FormField
                label="Contenu de la séance"
                type="textarea"
                rows={4}
                value={seanceForm.contenu}
                onChange={(e) => setSeanceForm({ ...seanceForm, contenu: e.target.value })}
                required
              />
              <button type="submit" className="btn-primary">
                Enregistrer la séance
              </button>
            </form>
          )}
          <Table
            columns={[
              { key: 'date_seance', header: 'Date' },
              { key: 'matiere_nom', header: 'Matière' },
              { key: 'enseignant_nom', header: 'Enseignant' },
              { key: 'contenu', header: 'Contenu' },
              ...(canEdit
                ? [
                    {
                      key: 'actions',
                      header: '',
                      render: (r) => (
                        <button
                          type="button"
                          className="text-xs text-brique hover:underline"
                          onClick={() => handleDeleteSeance(r.id)}
                        >
                          Supprimer
                        </button>
                      ),
                    },
                  ]
                : []),
            ]}
            data={seances}
            loading={loadingTab}
            emptyMessage="Aucune séance consignée pour cette classe."
          />
        </>
      )}

      {activeTab === 'absences' && (
        <>
          <div className="flex flex-wrap items-end gap-3">
            <FormField
              label="Date de l'appel"
              type="date"
              value={dateAppel}
              onChange={(e) => setDateAppel(e.target.value)}
              className="max-w-xs"
            />
            <button
              type="button"
              className="btn-secondary text-sm"
              onClick={() =>
                openPdf(
                  () => pedagogieApi.pdfFicheAppel({ id_classe: classe.id, date: dateAppel }),
                  `appel_${classe.libelle}.pdf`,
                  toast
                )
              }
            >
              Imprimer fiche d'appel
            </button>
          </div>
          <Table
            columns={[
              {
                key: 'eleve',
                header: 'Élève',
                render: (r) =>
                  r.eleve
                    ? `${r.eleve.prenom} ${r.eleve.nom}`
                    : `${r.prenom || ''} ${r.nom || ''}`.trim(),
              },
              { key: 'date_absence', header: 'Date' },
              { key: 'type_absence', header: 'Type' },
              { key: 'justifiee', header: 'Statut', render: (r) => <JustifBadge justifiee={r.justifiee} /> },
            ]}
            data={absences}
            loading={loadingTab}
            emptyMessage="Aucune absence enregistrée pour cette classe."
          />
        </>
      )}

      {activeTab === 'scolarite' && (
        <>
          <div className="flex justify-end">
            <button
              type="button"
              className="btn-secondary text-sm"
              onClick={() =>
                openPdf(
                  () => pedagogieApi.pdfFicheScolarite({ id_classe: classe.id, id_annee: idAnnee }),
                  `scolarite_${classe.libelle}.pdf`,
                  toast
                )
              }
            >
              Imprimer la fiche scolarité
            </button>
          </div>
          <Table
            columns={[
              { key: 'matricule', header: 'Matricule' },
              { key: 'nom', header: 'Élève', render: (r) => `${r.prenom} ${r.nom}` },
              {
                key: 'arriere',
                header: 'Arriéré',
                align: 'right',
                render: (r) => `${Number(r.arriere).toLocaleString('fr-FR')} FCFA`,
              },
            ]}
            data={arrieres}
            loading={loadingTab}
            emptyMessage="Aucun arriéré pour les élèves de cette classe."
          />
          <p className="text-center text-sm">
            <Link to="/finance/arrieres" className="text-or-cachet hover:underline">
              Voir tous les arriérés de l'établissement
            </Link>
          </p>
        </>
      )}

      {activeTab === 'notes' && (
        <>
          <div className="flex flex-wrap items-end gap-3">
            <FormField
              label="Évaluation (fiche correction)"
              type="select"
              value={ficheEvalId}
              onChange={(e) => setFicheEvalId(e.target.value)}
              options={evaluations.map((ev) => ({
                value: ev.id,
                label: `${ev.libelle || ev.type_evaluation} — ${ev.matiere_nom || ''}`,
              }))}
              className="max-w-md"
            />
            <button
              type="button"
              className="btn-secondary text-sm"
              disabled={!ficheEvalId}
              onClick={() =>
                openPdf(
                  () => pedagogieApi.pdfFicheCorrection({ id_evaluation: ficheEvalId }),
                  'fiche_correction.pdf',
                  toast
                )
              }
            >
              Imprimer fiche correction
            </button>
          </div>
          <Table
            columns={[
              { key: 'libelle', header: 'Évaluation', render: (r) => r.libelle || r.type_evaluation },
              { key: 'matiere_nom', header: 'Matière' },
              { key: 'date_evaluation', header: 'Date' },
              {
                key: 'statut_saisie',
                header: 'Saisie',
                render: (r) =>
                  r.statut_saisie === 'cloturee' ? (
                    <Badge variant="success">Clôturée</Badge>
                  ) : (
                    <Badge variant="warning">En cours</Badge>
                  ),
              },
            ]}
            data={evaluations}
            loading={loadingTab}
            emptyMessage="Aucune évaluation pour cette classe pour l'instant."
            onRowClick={(row) => navigate(`/notes/saisie/${row.id}`)}
          />
        </>
      )}
    </div>
  );
}
