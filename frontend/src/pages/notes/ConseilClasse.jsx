import { useCallback, useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import { conseilClasseApi } from '../../services/api/conseilClasse';
import { configApi } from '../../services/api/config';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';
import { emptyIcons } from '../../utils/emptyIcons';

const DECISIONS = [
  { value: 'passe', label: 'Passe' },
  { value: 'redouble', label: 'Redouble' },
  { value: 'oriente', label: 'Orienté' },
  { value: 'exclu', label: 'Exclu' },
  { value: 'ajourne', label: 'Ajourné' },
  { value: 'autre', label: 'Autre' },
];

export default function ConseilClasse() {
  const toast = useToast();
  const [sessions, setSessions] = useState([]);
  const [decisions, setDecisions] = useState([]);
  const [classes, setClasses] = useState([]);
  const [annees, setAnnees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sessionForm, setSessionForm] = useState({
    id_classe: '',
    id_annee: '',
    date_session: '',
    statut: 'planifie',
    notes: '',
  });
  const [decisionForm, setDecisionForm] = useState({
    id_eleve: '',
    id_annee: '',
    id_session: '',
    decision: 'passe',
    mention: '',
    commentaire: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, d] = await Promise.all([
        conseilClasseApi.listSessions(),
        conseilClasseApi.listDecisions(),
      ]);
      setSessions(Array.isArray(s) ? s : []);
      setDecisions(Array.isArray(d) ? d : []);
    } catch {
      toast.error('Impossible de charger le conseil de classe');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
    Promise.all([configApi.listClasses?.() || Promise.resolve([]), configApi.listAnnees()])
      .then(([c, a]) => {
        setClasses(Array.isArray(c) ? c : c.items || []);
        const anneesList = Array.isArray(a) ? a : a.items || [];
        setAnnees(anneesList);
        const active = anneesList.find((x) => x.est_active);
        if (active) {
          setSessionForm((f) => ({ ...f, id_annee: String(active.id) }));
          setDecisionForm((f) => ({ ...f, id_annee: String(active.id) }));
        }
      })
      .catch(() => {});
  }, [load]);

  const createSession = async (e) => {
    e.preventDefault();
    try {
      await conseilClasseApi.createSession({
        id_classe: sessionForm.id_classe,
        id_annee: sessionForm.id_annee || null,
        date_session: sessionForm.date_session,
        statut: sessionForm.statut,
        notes: sessionForm.notes || null,
      });
      toast.success('Session créée');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur session');
    }
  };

  const createDecision = async (e) => {
    e.preventDefault();
    try {
      await conseilClasseApi.createDecision({
        id_eleve: decisionForm.id_eleve,
        id_annee: decisionForm.id_annee,
        id_session: decisionForm.id_session || null,
        decision: decisionForm.decision,
        mention: decisionForm.mention || null,
        commentaire: decisionForm.commentaire || null,
      });
      toast.success('Décision enregistrée');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur décision');
    }
  };

  const classeLabel = (id) => {
    const c = classes.find((x) => String(x.id) === String(id));
    return c?.libelle || String(id).slice(0, 8);
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Notes"
        title="Conseil de classe"
        subtitle="Sessions et décisions de passage"
      />

      <form onSubmit={createSession} className="card-premium grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4">
        <FormField
          label="Classe"
          name="id_classe"
          type="select"
          value={sessionForm.id_classe}
          onChange={(e) => setSessionForm((f) => ({ ...f, id_classe: e.target.value }))}
          options={classes.map((c) => ({ value: String(c.id), label: c.libelle }))}
          required
        />
        <FormField
          label="Date"
          name="date_session"
          type="date"
          value={sessionForm.date_session}
          onChange={(e) => setSessionForm((f) => ({ ...f, date_session: e.target.value }))}
          required
        />
        <FormField
          label="Année"
          name="id_annee"
          type="select"
          value={sessionForm.id_annee}
          onChange={(e) => setSessionForm((f) => ({ ...f, id_annee: e.target.value }))}
          options={annees.map((a) => ({ value: String(a.id), label: a.libelle }))}
        />
        <div className="flex items-end">
          <button type="submit" className="btn-primary w-full">
            <Plus className="h-4 w-4" /> Session
          </button>
        </div>
      </form>

      <Table
        columns={[
          {
            key: 'classe',
            header: 'Classe',
            render: (r) => classeLabel(r.id_classe),
          },
          { key: 'date_session', header: 'Date' },
          { key: 'statut', header: 'Statut' },
          { key: 'notes', header: 'Notes', render: (r) => r.notes || '—' },
        ]}
        data={sessions}
        loading={loading}
        emptyIcon={emptyIcons.notes}
        emptyMessage="Aucune session planifiée."
      />

      <form onSubmit={createDecision} className="card-premium grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-3">
        <h3 className="section-title sm:col-span-2 lg:col-span-3 !text-base">Nouvelle décision</h3>
        <FormField
          label="ID élève"
          name="id_eleve"
          value={decisionForm.id_eleve}
          onChange={(e) => setDecisionForm((f) => ({ ...f, id_eleve: e.target.value }))}
          required
        />
        <FormField
          label="Session"
          name="id_session"
          type="select"
          value={decisionForm.id_session}
          onChange={(e) => setDecisionForm((f) => ({ ...f, id_session: e.target.value }))}
          options={sessions.map((s) => ({
            value: String(s.id),
            label: `${classeLabel(s.id_classe)} — ${s.date_session}`,
          }))}
        />
        <FormField
          label="Décision"
          name="decision"
          type="select"
          value={decisionForm.decision}
          onChange={(e) => setDecisionForm((f) => ({ ...f, decision: e.target.value }))}
          options={DECISIONS}
        />
        <FormField
          label="Mention"
          name="mention"
          value={decisionForm.mention}
          onChange={(e) => setDecisionForm((f) => ({ ...f, mention: e.target.value }))}
        />
        <FormField
          label="Commentaire"
          name="commentaire"
          value={decisionForm.commentaire}
          onChange={(e) => setDecisionForm((f) => ({ ...f, commentaire: e.target.value }))}
        />
        <div className="flex items-end">
          <button type="submit" className="btn-secondary w-full">
            Enregistrer
          </button>
        </div>
      </form>

      <Table
        columns={[
          { key: 'id_eleve', header: 'Élève', render: (r) => String(r.id_eleve).slice(0, 8) },
          { key: 'decision', header: 'Décision' },
          { key: 'mention', header: 'Mention', render: (r) => r.mention || '—' },
          { key: 'commentaire', header: 'Commentaire', render: (r) => r.commentaire || '—' },
        ]}
        data={decisions}
        loading={false}
        emptyMessage="Aucune décision enregistrée."
      />
    </div>
  );
}
