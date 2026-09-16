import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { notesApi } from '../../services/api/notes';
import { configApi } from '../../services/api/config';
import { elevesApi } from '../../services/api/eleves';
import Table from '../../components/Table';
import { emptyIcons } from '../../utils/emptyIcons';
import FormField from '../../components/FormField';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';
import {
  formatMoyenneDisplay,
  formatResultSource,
  formatRulesetRef,
} from '../../utils/academicResultsDisplay';

/**
 * Parcours consultation des résultats académiques (PR14).
 * Aucun calcul de moyenne côté client — lecture/recalcul via API PR13.
 */
export default function ResultatsAcademiques() {
  const toast = useToast();
  const { isAdmin, isEnseignant } = useAuth();
  const canRecalc = isAdmin || isEnseignant;
  const [searchParams] = useSearchParams();

  const [classes, setClasses] = useState([]);
  const [trimestres, setTrimestres] = useState([]);
  const [eleves, setEleves] = useState([]);
  const [evaluations, setEvaluations] = useState([]);
  const [notesByEval, setNotesByEval] = useState({});

  const [idClasse, setIdClasse] = useState(() => searchParams.get('id_classe') || '');
  const [idPeriod, setIdPeriod] = useState(() => searchParams.get('id_period') || '');
  const [idEleve, setIdEleve] = useState(() => searchParams.get('id_eleve') || '');

  const [results, setResults] = useState([]);
  const [hasStale, setHasStale] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [selectedMatiere, setSelectedMatiere] = useState(null);

  useEffect(() => {
    const init = async () => {
      setLoadingMeta(true);
      try {
        const [classesData, anneesData] = await Promise.all([
          configApi.listClasses(),
          configApi.listAnnees(),
        ]);
        setClasses(classesData.items || classesData || []);
        const anneeList = anneesData.items || anneesData || [];
        const active = anneeList.find((a) => a.est_active) || anneeList[0];
        if (active) {
          const trims = await configApi.listTrimestres(active.id);
          const trimList = trims.items || trims || [];
          setTrimestres(trimList);
          const periodFromUrl = searchParams.get('id_period');
          if (trimList.length && !periodFromUrl) {
            setIdPeriod(String(trimList[0].id));
          }
        }
      } catch {
        toast.error('Erreur lors du chargement des filtres');
      } finally {
        setLoadingMeta(false);
      }
    };
    init();
    // Intentionnel : initialisation une fois au montage (+ query initiale)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toast]);

  useEffect(() => {
    if (!idClasse) {
      setEleves([]);
      setIdEleve('');
      return;
    }
    const loadEleves = async () => {
      try {
        const data = await elevesApi.list({
          id_classe: idClasse,
          per_page: 100,
        });
        const items = data.items || data || [];
        setEleves(items);
        setIdEleve((prev) => (items.some((e) => String(e.id) === prev) ? prev : ''));
      } catch {
        toast.error('Erreur lors du chargement des élèves');
        setEleves([]);
      }
    };
    loadEleves();
  }, [idClasse, toast]);

  const loadResults = useCallback(async () => {
    if (!idClasse || !idPeriod || !idEleve) {
      setResults([]);
      setHasStale(false);
      return;
    }
    setLoading(true);
    try {
      const data = await notesApi.listResultats({
        id_eleve: idEleve,
        id_classe: idClasse,
        id_period: idPeriod,
      });
      setResults(data.items || []);
      setHasStale(Boolean(data.has_stale));
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur lors du chargement des résultats');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [idClasse, idPeriod, idEleve, toast]);

  useEffect(() => {
    loadResults();
    setSelectedMatiere(null);
  }, [loadResults]);

  useEffect(() => {
    if (!idClasse || !idPeriod) {
      setEvaluations([]);
      return;
    }
    const loadEvals = async () => {
      try {
        const data = await notesApi.listEvaluations({
          id_classe: idClasse,
          id_trimestre: idPeriod,
          per_page: 100,
        });
        setEvaluations(Array.isArray(data) ? data : data.items || []);
      } catch {
        setEvaluations([]);
      }
    };
    loadEvals();
  }, [idClasse, idPeriod]);

  const handleRecalculer = async () => {
    if (!idClasse || !idPeriod || !idEleve) return;
    setRecalculating(true);
    try {
      const data = await notesApi.recalculerResultats({
        id_classe: idClasse,
        id_period: idPeriod,
        id_eleve: idEleve,
      });
      const block = (data.items || []).find((i) => String(i.id_eleve) === String(idEleve));
      setResults(block?.results || []);
      setHasStale(false);
      toast.success('Résultats recalculés via le moteur de règles');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur lors du recalcul');
    } finally {
      setRecalculating(false);
    }
  };

  const loadNotesForMatiere = async (matiereId) => {
    setSelectedMatiere(matiereId);
    const evals = evaluations.filter((e) => String(e.id_matiere) === String(matiereId));
    const next = { ...notesByEval };
    await Promise.all(
      evals.map(async (ev) => {
        if (next[ev.id]) return;
        try {
          const grid = await notesApi.getNotesGrid(ev.id);
          const note = (grid.notes || []).find((n) => String(n.id_eleve) === String(idEleve));
          next[ev.id] = note || null;
        } catch {
          next[ev.id] = null;
        }
      })
    );
    setNotesByEval(next);
  };

  const evalsForMatiere = useMemo(
    () =>
      selectedMatiere
        ? evaluations.filter((e) => String(e.id_matiere) === String(selectedMatiere))
        : [],
    [evaluations, selectedMatiere]
  );

  const columns = [
    {
      key: 'matiere',
      header: 'Matière',
      render: (r) => (
        <button
          type="button"
          className="text-left font-medium text-or-cachet hover:underline"
          onClick={() => loadNotesForMatiere(r.id_matiere)}
        >
          {r.matiere_libelle || '—'}
        </button>
      ),
    },
    {
      key: 'moyenne',
      header: 'Moyenne',
      render: (r) => (
        <span>
          {formatMoyenneDisplay(r.moyenne, r.scale_max)}
          {r.incomplete ? (
            <span className="ml-2 text-xs text-texte-secondaire">(incomplet)</span>
          ) : null}
        </span>
      ),
    },
    {
      key: 'coef',
      header: 'Coef. matière',
      render: (r) => (r.coefficient != null ? Number(r.coefficient).toFixed(2) : '—'),
    },
    {
      key: 'ruleset',
      header: 'Ruleset',
      render: (r) => formatRulesetRef(r),
    },
    {
      key: 'source',
      header: 'Source',
      render: (r) => formatResultSource(r.source),
    },
    {
      key: 'stale',
      header: 'État',
      render: (r) =>
        r.is_stale ? (
          <span className="badge-warning text-xs">À recalculer</span>
        ) : (
          <span className="badge-success text-xs">À jour</span>
        ),
    },
  ];

  const filtersReady = Boolean(idClasse && idPeriod && idEleve);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Notes & bulletins"
        title="Résultats académiques"
        subtitle="Consultation des moyennes calculées par le moteur de règles (aucun calcul côté navigateur)"
        actions={
          canRecalc && (
            <button
              type="button"
              className="btn-primary"
              disabled={!filtersReady || recalculating}
              onClick={handleRecalculer}
            >
              {recalculating ? 'Calcul…' : 'Recalculer'}
            </button>
          )
        }
      />

      {loadingMeta ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-or-cachet-clair border-t-or-cachet" />
        </div>
      ) : (
        <div className="card grid gap-4 md:grid-cols-3">
          <FormField
            label="Classe"
            name="id_classe"
            type="select"
            value={idClasse}
            onChange={(e) => setIdClasse(e.target.value)}
            options={classes.map((c) => ({
              value: String(c.id),
              label: c.libelle || c.nom,
            }))}
          />
          <FormField
            label="Période"
            name="id_period"
            type="select"
            value={idPeriod}
            onChange={(e) => setIdPeriod(e.target.value)}
            options={trimestres.map((t) => ({
              value: String(t.id),
              label: t.label || `Trimestre ${t.numero}`,
            }))}
          />
          <FormField
            label="Élève"
            name="id_eleve"
            type="select"
            value={idEleve}
            onChange={(e) => setIdEleve(e.target.value)}
            options={eleves.map((el) => ({
              value: String(el.id),
              label: `${el.prenom || ''} ${el.nom || ''}`.trim() || el.matricule || el.id,
            }))}
          />
        </div>
      )}

      {hasStale && filtersReady ? (
        <p className="text-sm text-texte-secondaire">
          Des résultats sont obsolètes après une modification de notes — utilisez « Recalculer ».
        </p>
      ) : null}

      {!filtersReady ? (
        <p className="text-sm text-texte-secondaire">
          Sélectionnez une classe, une période et un élève pour consulter les résultats.
        </p>
      ) : (
        <Table
          columns={columns}
          data={results}
          loading={loading || recalculating}
          emptyIcon={emptyIcons.evaluations}
          emptyMessage="Aucun résultat persisté — cliquez sur Recalculer pour lancer le moteur."
        />
      )}

      {selectedMatiere && (
        <div className="card space-y-4">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-lg font-medium text-encre">
              Évaluations & notes —{' '}
              {results.find((r) => String(r.id_matiere) === String(selectedMatiere))
                ?.matiere_libelle || 'Matière'}
            </h2>
            <button
              type="button"
              className="text-sm text-texte-secondaire hover:underline"
              onClick={() => setSelectedMatiere(null)}
            >
              Fermer
            </button>
          </div>
          {evalsForMatiere.length === 0 ? (
            <p className="text-sm text-texte-secondaire">
              Aucune évaluation pour cette matière sur la période.
            </p>
          ) : (
            <ul className="divide-y divide-bordure">
              {evalsForMatiere.map((ev) => {
                const note = notesByEval[ev.id];
                let noteLabel = '…';
                if (note === null) noteLabel = '—';
                else if (note) {
                  if (note.absent) noteLabel = 'Absent';
                  else if (note.valeur_note == null) noteLabel = '—';
                  else noteLabel = String(note.valeur_note);
                }
                return (
                  <li key={ev.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                    <div>
                      <p className="font-medium">
                        {ev.libelle || ev.type_evaluation}{' '}
                        <span className="text-xs text-texte-secondaire">({ev.type_evaluation})</span>
                      </p>
                      <p className="text-xs text-texte-secondaire">{ev.date_evaluation}</p>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-sm">
                        Note : <strong>{noteLabel}</strong>
                      </span>
                      <Link
                        to={`/notes/saisie/${ev.id}`}
                        className="text-sm text-or-cachet hover:underline"
                      >
                        Saisie →
                      </Link>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
          <p className="text-xs text-texte-secondaire">
            Les poids (ex. devoir / composition) viennent du Ruleset actif — pas de % hardcodés ici.
          </p>
        </div>
      )}
    </div>
  );
}
