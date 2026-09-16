import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { configApi } from '../../services/api/config';
import Badge from '../../components/Badge';
import Breadcrumb from '../../components/Breadcrumb';
import Card from '../../components/Card';
import DetailHeader from '../../components/DetailHeader';
import StructureAcademiqueNav from '../../components/StructureAcademiqueNav';
import TabBar from '../../components/TabBar';
import Table from '../../components/Table';
import { useToast } from '../../components/Toast';
import { emptyIcons } from '../../utils/emptyIcons';
import {
  apiErrorMessage,
  asList,
  isGeneralProgram,
  periodTypeLabel,
  programTypeLabel,
} from '../../utils/academicLabels';

const TABS = [
  { id: 'overview', label: 'Vue d’ensemble' },
  { id: 'periodes', label: 'Périodes' },
  { id: 'niveaux', label: 'Niveaux' },
  { id: 'classes', label: 'Classes' },
];

export default function ProgrammeDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;

  const [program, setProgram] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState('overview');
  const [periodes, setPeriodes] = useState([]);
  const [niveaux, setNiveaux] = useState([]);
  const [classes, setClasses] = useState([]);
  const [tabLoading, setTabLoading] = useState(false);
  const [annees, setAnnees] = useState([]);
  const [anneeId, setAnneeId] = useState('');

  const loadProgram = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await configApi.getProgram(id);
      setProgram(data);
    } catch (err) {
      const msg = apiErrorMessage(err, 'Programme introuvable.');
      setError(msg);
      if (err.response?.status === 403 || err.response?.status === 404) {
        toastRef.current.error(msg);
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadProgram();
  }, [loadProgram]);

  useEffect(() => {
    configApi
      .listAnnees()
      .then((data) => {
        const list = asList(data);
        setAnnees(list);
        const active = list.find((a) => a.est_active) || list[0];
        if (active) setAnneeId(String(active.id));
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!program || tab === 'overview') return undefined;
    let cancelled = false;
    const run = async () => {
      setTabLoading(true);
      try {
        if (tab === 'periodes') {
          const params = { id_program: program.id };
          if (anneeId) params.id_annee = anneeId;
          const data = await configApi.listPeriodes(params);
          if (!cancelled) setPeriodes(asList(data));
        } else if (tab === 'niveaux') {
          const data = await configApi.listNiveaux({ id_program: program.id });
          if (!cancelled) setNiveaux(asList(data));
        } else if (tab === 'classes') {
          const params = { id_program: program.id };
          if (anneeId) params.id_annee = anneeId;
          const data = await configApi.listClasses(params);
          if (!cancelled) setClasses(asList(data));
        }
      } catch (err) {
        toastRef.current.error(apiErrorMessage(err, 'Chargement impossible'));
      } finally {
        if (!cancelled) setTabLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [program, tab, anneeId]);

  if (loading) {
    return (
      <div className="space-y-6">
        <StructureAcademiqueNav />
        <div className="flex items-center gap-2 py-16 text-sm text-texte-secondaire">
          <div className="loading-ring h-5 w-5" />
          Chargement du programme…
        </div>
      </div>
    );
  }

  if (error || !program) {
    return (
      <div className="space-y-6">
        <StructureAcademiqueNav />
        <div
          role="alert"
          className="rounded-card border border-brique/30 bg-brique-clair px-4 py-8 text-center"
        >
          <p className="text-sm text-brique">{error || 'Programme introuvable.'}</p>
          <button
            type="button"
            className="btn-secondary mt-4"
            onClick={() => navigate('/etablissement/programmes')}
          >
            Retour aux programmes
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <DetailHeader
        breadcrumb={
          <Breadcrumb
            items={[
              { label: 'Programmes', to: '/etablissement/programmes' },
              { label: program.name },
            ]}
          />
        }
        eyebrow="Structure académique"
        title={program.name}
        subtitle={
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm text-texte-secondaire">{program.code}</span>
            <Badge variant="info">{programTypeLabel(program.program_type)}</Badge>
            {program.is_active ? (
              <Badge variant="success">Actif</Badge>
            ) : (
              <Badge variant="neutral">Inactif</Badge>
            )}
            {isGeneralProgram(program) && (
              <Badge variant="warning">Compatibilité historique</Badge>
            )}
          </div>
        }
        actions={
          <Link
            to={`/etablissement/periodes?program=${program.id}`}
            className="btn-secondary"
          >
            Gérer les périodes
          </Link>
        }
      />

      <StructureAcademiqueNav />

      <TabBar tabs={TABS} active={tab} onChange={setTab} />

      {tab === 'overview' && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card premium className="p-5">
            <p className="text-xs font-medium uppercase tracking-wide text-texte-secondaire">
              Périodes (défaut)
            </p>
            <p className="mt-2 font-display text-2xl text-encre">
              {periodTypeLabel(program.period_type_default)}
            </p>
          </Card>
          <Card premium className="p-5">
            <p className="text-xs font-medium uppercase tracking-wide text-texte-secondaire">
              Niveaux
            </p>
            <p className="mt-2 font-display text-2xl text-encre">
              {typeof program.levels_count === 'number' ? program.levels_count : '—'}
            </p>
          </Card>
          <Card premium className="p-5">
            <p className="text-xs font-medium uppercase tracking-wide text-texte-secondaire">
              Classes
            </p>
            <p className="mt-2 font-display text-2xl text-encre">
              {typeof program.classes_count === 'number' ? program.classes_count : '—'}
            </p>
          </Card>
          <Card premium className="p-5">
            <p className="text-xs font-medium uppercase tracking-wide text-texte-secondaire">
              Périodes enregistrées
            </p>
            <p className="mt-2 font-display text-2xl text-encre">
              {typeof program.periods_count === 'number' ? program.periods_count : '—'}
            </p>
          </Card>
          {program.description && (
            <Card className="p-5 sm:col-span-2 lg:col-span-4">
              <p className="text-xs font-medium uppercase tracking-wide text-texte-secondaire">
                Description
              </p>
              <p className="mt-2 text-sm leading-relaxed text-encre">{program.description}</p>
            </Card>
          )}
          {isGeneralProgram(program) && (
            <Card className="border-or-cachet/30 bg-or-cachet-doux p-5 sm:col-span-2 lg:col-span-4">
              <p className="text-sm text-encre">
                Programme <strong>GENERAL</strong> : référentiel historique permanent de
                l’école. Il ne peut pas être désactivé. Les niveaux et classes sans filière
                explicite y sont rattachés pour la compatibilité.
              </p>
            </Card>
          )}
        </div>
      )}

      {tab === 'periodes' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-sm text-texte-secondaire" htmlFor="detail-annee">
              Année scolaire
            </label>
            <select
              id="detail-annee"
              className="input w-auto"
              value={anneeId}
              onChange={(e) => setAnneeId(e.target.value)}
            >
              {annees.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.libelle}
                  {a.est_active ? ' (active)' : ''}
                </option>
              ))}
            </select>
          </div>
          <Table
            columns={[
              { key: 'sequence', header: 'Séquence', render: (r) => r.sequence },
              { key: 'label', header: 'Libellé', render: (r) => r.label || r.code },
              {
                key: 'period_type',
                header: 'Type',
                render: (r) => periodTypeLabel(r.period_type),
              },
              { key: 'date_debut', header: 'Début' },
              { key: 'date_fin', header: 'Fin' },
              {
                key: 'status',
                header: 'Statut',
                render: (r) =>
                  r.is_active !== false ? (
                    <Badge variant="success">Active</Badge>
                  ) : (
                    <Badge variant="neutral">Inactive</Badge>
                  ),
              },
            ]}
            data={periodes}
            loading={tabLoading}
            emptyIcon={emptyIcons.trimestres}
            emptyMessage="Aucune période pour ce programme et cette année."
          />
        </div>
      )}

      {tab === 'niveaux' && (
        <Table
          columns={[
            { key: 'ordre', header: 'Ordre' },
            {
              key: 'libelle',
              header: 'Niveau',
              render: (r) => (
                <span className="font-medium">
                  {r.libelle} · {program.name}
                </span>
              ),
            },
            {
              key: 'cycle',
              header: 'Cycle',
              render: (r) => (r.cycle === 'second' ? 'Second cycle' : 'Premier cycle'),
            },
          ]}
          data={niveaux}
          loading={tabLoading}
          emptyIcon={emptyIcons.niveaux}
          emptyMessage="Aucun niveau rattaché à ce programme."
        />
      )}

      {tab === 'classes' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-sm text-texte-secondaire" htmlFor="detail-annee-cl">
              Année scolaire
            </label>
            <select
              id="detail-annee-cl"
              className="input w-auto"
              value={anneeId}
              onChange={(e) => setAnneeId(e.target.value)}
            >
              {annees.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.libelle}
                </option>
              ))}
            </select>
          </div>
          <Table
            columns={[
              {
                key: 'libelle',
                header: 'Classe',
                render: (r) => <span className="font-medium">{r.libelle}</span>,
              },
              {
                key: 'niveau',
                header: 'Niveau',
                render: (r) =>
                  r.niveau?.libelle ||
                  niveaux.find((n) => String(n.id) === String(r.id_niveau))?.libelle ||
                  '—',
              },
            ]}
            data={classes}
            loading={tabLoading}
            emptyIcon={emptyIcons.classes}
            emptyMessage="Aucune classe pour ce programme."
          />
        </div>
      )}
    </div>
  );
}
