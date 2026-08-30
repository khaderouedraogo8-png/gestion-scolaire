import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import Table from '../../components/Table';
import Badge from '../../components/Badge';
import FormField from '../../components/FormField';
import { configApi } from '../../services/api/config';
import { notesApi } from '../../services/api/notes';
import { pedagogieApi, downloadBlob } from '../../services/api/pedagogie';
import { useToast } from '../../components/Toast';
import useParentChildren from '../../hooks/useParentChildren';
import { cycleLabel } from '../../utils/classNavigation';

const TABS = [
  { id: 'devoirs', label: 'Devoirs' },
  { id: 'compositions', label: 'Compositions' },
  { id: 'cahier', label: 'Cahier de texte' },
];

async function openPdf(apiCall, filename, toast) {
  try {
    const { data } = await apiCall();
    downloadBlob(data, filename);
  } catch (err) {
    toast.error(err.response?.data?.message || 'Erreur lors de la génération PDF');
  }
}

export default function ParentPedagogie() {
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get('onglet') || 'devoirs';
  const { children, selectedChild, selectedId, selectChild, idAnnee, loading, error } =
    useParentChildren();

  const [loadingTab, setLoadingTab] = useState(false);
  const [programmeDevoirs, setProgrammeDevoirs] = useState([]);
  const [chargeStats, setChargeStats] = useState(null);
  const [compositions, setCompositions] = useState([]);
  const [seances, setSeances] = useState([]);
  const [trimestres, setTrimestres] = useState([]);
  const [idTrimestrePdf, setIdTrimestrePdf] = useState('');

  const idClasse = selectedChild?.id_classe || '';

  useEffect(() => {
    if (!idAnnee) return;
    configApi
      .listTrimestres(idAnnee)
      .then((trim) => {
        const trimList = Array.isArray(trim) ? trim : trim.items || [];
        setTrimestres(trimList);
        if (trimList[0]) setIdTrimestrePdf(trimList[0].id);
      })
      .catch(() => setTrimestres([]));
  }, [idAnnee]);

  const loadTab = useCallback(async () => {
    if (!idClasse || !idAnnee) return;
    setLoadingTab(true);
    try {
      if (activeTab === 'devoirs') {
        const [prog, charge] = await Promise.all([
          pedagogieApi.listProgrammeDevoirs({ id_classe: idClasse, id_annee: idAnnee }),
          pedagogieApi.getChargeTravail({
            id_classe: idClasse,
            id_annee: idAnnee,
            id_trimestre: idTrimestrePdf || undefined,
          }),
        ]);
        setProgrammeDevoirs(Array.isArray(prog) ? prog : []);
        setChargeStats(charge);
      } else if (activeTab === 'compositions') {
        const data = await notesApi.listEvaluations({
          id_classe: idClasse,
          type_evaluation: 'examen',
        });
        setCompositions(Array.isArray(data) ? data : data.items || []);
      } else if (activeTab === 'cahier') {
        const seancesData = await pedagogieApi.listSeances({
          id_classe: idClasse,
          id_annee: idAnnee,
        });
        setSeances(Array.isArray(seancesData) ? seancesData : []);
      }
    } catch {
      toast.error('Impossible de charger les informations pédagogiques.');
    } finally {
      setLoadingTab(false);
    }
  }, [activeTab, idClasse, idAnnee, idTrimestrePdf, toast]);

  useEffect(() => {
    loadTab();
  }, [loadTab]);

  const compositionsByTrimestre = useMemo(() => {
    const groups = {};
    compositions.forEach((c) => {
      const key = c.trimestre_numero ?? '?';
      if (!groups[key]) groups[key] = [];
      groups[key].push(c);
    });
    return groups;
  }, [compositions]);

  const setTab = (tabId) => {
    setSearchParams({ onglet: tabId });
  };

  if (loading) {
    return <p className="text-sm text-texte-secondaire">Chargement…</p>;
  }

  if (error) {
    return <p className="text-sm text-brique">{error}</p>;
  }

  if (children.length === 0) {
    return (
      <div className="space-y-4">
        <h1 className="page-title">Programme pédagogique</h1>
        <p className="page-subtitle">Aucun enfant rattaché à votre compte pour l'année en cours.</p>
      </div>
    );
  }

  const classeLabel = selectedChild?.classe_nom || 'classe';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Programme pédagogique</h1>
        <p className="page-subtitle">
          Devoirs, compositions et cahier de texte — consultation en lecture seule
        </p>
      </div>

      <div className="card flex flex-wrap items-end gap-4">
        <FormField
          label="Enfant"
          type="select"
          value={selectedId}
          onChange={(e) => selectChild(e.target.value)}
          options={children.map((c) => ({
            value: String(c.id),
            label: `${c.prenom} ${c.nom} — ${c.classe_nom || 'Sans classe'}`,
          }))}
          className="min-w-[240px] flex-1"
        />
        {selectedChild?.classe_nom && (
          <p className="text-sm text-texte-secondaire">
            {cycleLabel(selectedChild.cycle)} · {selectedChild.classe_nom}
          </p>
        )}
      </div>

      {!idClasse && (
        <p className="text-sm text-brique">
          Cet enfant n'est pas inscrit dans une classe pour l'année en cours.
        </p>
      )}

      {idClasse && (
        <>
          <div className="flex flex-wrap gap-2 border-b border-bordure pb-2">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setTab(tab.id)}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-or-cachet-clair text-encre'
                    : 'text-texte-secondaire hover:bg-fond-alt'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === 'devoirs' && (
            <>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="page-subtitle">Planning récurrent des devoirs attendus</p>
                <button
                  type="button"
                  className="btn-secondary text-sm"
                  onClick={() =>
                    openPdf(
                      () =>
                        pedagogieApi.pdfProgrammeDevoirs({
                          id_classe: idClasse,
                          id_annee: idAnnee,
                        }),
                      `programme_devoirs_${classeLabel}.pdf`,
                      toast
                    )
                  }
                >
                  Télécharger le programme (PDF)
                </button>
              </div>
              <Table
                columns={[
                  { key: 'jour_libelle', header: 'Jour' },
                  { key: 'matiere_nom', header: 'Matière' },
                  { key: 'frequence', header: 'Fréquence' },
                  { key: 'note', header: 'Remarque', render: (r) => r.note || '—' },
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
                          id_classe: idClasse,
                          id_trimestre: idTrimestrePdf,
                        }),
                      `compositions_${classeLabel}.pdf`,
                      toast
                    )
                  }
                >
                  Calendrier PDF
                </button>
                <button
                  type="button"
                  className="btn-primary text-sm"
                  disabled={!idTrimestrePdf}
                  onClick={() =>
                    openPdf(
                      () =>
                        pedagogieApi.pdfProgrammeTrimestriel({
                          id_classe: idClasse,
                          id_trimestre: idTrimestrePdf,
                          id_annee: idAnnee,
                        }),
                      `programme_trimestriel_${classeLabel}.pdf`,
                      toast
                    )
                  }
                >
                  Programme trimestriel PDF
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
                      {
                        key: 'libelle',
                        header: 'Libellé',
                        render: (r) => r.libelle || 'Composition',
                      },
                      {
                        key: 'statut',
                        header: 'Statut',
                        render: () => <Badge variant="success">Publiée</Badge>,
                      },
                    ]}
                    data={items}
                    loading={loadingTab}
                    emptyMessage="Aucune composition publiée."
                  />
                </div>
              ))}
              {!loadingTab && compositions.length === 0 && (
                <p className="text-sm text-texte-secondaire">
                  Aucune composition publiée pour cette classe.
                </p>
              )}
            </>
          )}

          {activeTab === 'cahier' && (
            <>
              <p className="page-subtitle">
                Contenu des séances enregistrées par les enseignants
              </p>
              <Table
                columns={[
                  { key: 'date_seance', header: 'Date' },
                  { key: 'matiere_nom', header: 'Matière' },
                  { key: 'enseignant_nom', header: 'Enseignant' },
                  { key: 'contenu', header: 'Contenu' },
                ]}
                data={seances}
                loading={loadingTab}
                emptyMessage="Aucune séance consignée pour cette classe."
              />
            </>
          )}
        </>
      )}
    </div>
  );
}
