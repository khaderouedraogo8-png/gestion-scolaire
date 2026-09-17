import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, ClipboardList, FileText } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import useAuth from '../../hooks/useAuth';
import { elevesApi } from '../../services/api/eleves';

/** Portail élève — données /eleves/me/portal si lien compte ; sinon liens lecture. */
export default function EleveHome() {
  const { user } = useAuth();
  const [portal, setPortal] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await elevesApi.getMePortal();
        if (!cancelled) setPortal(data);
      } catch {
        if (!cancelled) setPortal(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const eleve = portal?.eleve;
  const enfants = portal?.enfants || [];
  const isParentFallback = portal?.mode === 'parent';

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Espace élève"
        title={
          eleve
            ? `Bonjour, ${eleve.prenom}`
            : `Bonjour${user?.prenom ? `, ${user.prenom}` : ''}`
        }
        subtitle={
          eleve?.classe
            ? `Classe ${eleve.classe.libelle}`
            : isParentFallback
              ? 'Vue parent — enfants liés'
              : 'Consultez vos notes, devoirs et absences'
        }
      />

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="loading-ring" />
        </div>
      ) : null}

      {eleve && !loading ? (
        <section className="space-y-4">
          <h2 className="dashboard-section-label">Aperçu</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-bordure/60 bg-blanc p-4">
              <p className="text-xs uppercase tracking-wide text-texte-secondaire">Notes récentes</p>
              <ul className="mt-2 space-y-1.5 text-sm">
                {(eleve.notes_recentes || []).length === 0 ? (
                  <li className="text-texte-secondaire">Aucune note</li>
                ) : (
                  eleve.notes_recentes.map((n) => (
                    <li key={n.id} className="flex justify-between gap-2">
                      <span className="text-texte-secondaire">{n.absent ? 'Absent' : 'Note'}</span>
                      <span className="tabular-nums font-medium text-encre">
                        {n.absent ? '—' : n.valeur_note ?? '—'}
                      </span>
                    </li>
                  ))
                )}
              </ul>
            </div>
            <div className="rounded-lg border border-bordure/60 bg-blanc p-4">
              <p className="text-xs uppercase tracking-wide text-texte-secondaire">Absences</p>
              <ul className="mt-2 space-y-1.5 text-sm">
                {(eleve.absences_recentes || []).length === 0 ? (
                  <li className="text-texte-secondaire">Aucune absence récente</li>
                ) : (
                  eleve.absences_recentes.map((a) => (
                    <li key={a.id} className="flex justify-between gap-2">
                      <span>{a.date_absence}</span>
                      <span className="text-texte-secondaire">
                        {a.justifiee ? 'justifiée' : 'non justifiée'}
                      </span>
                    </li>
                  ))
                )}
              </ul>
            </div>
          </div>
        </section>
      ) : null}

      {isParentFallback && enfants.length > 0 && !loading ? (
        <section className="space-y-3">
          <h2 className="dashboard-section-label">Enfants liés</h2>
          <ul className="space-y-2">
            {enfants.map((e) => (
              <li
                key={e.id}
                className="flex items-center justify-between rounded-lg border border-bordure/60 bg-blanc px-4 py-3 text-sm"
              >
                <span className="font-medium text-encre">
                  {e.prenom} {e.nom}
                </span>
                <span className="text-texte-secondaire">
                  {e.classe?.libelle || e.matricule}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {portal?.mode === 'unlinked' && !loading ? (
        <div className="rounded-lg border border-bordure/60 bg-craie/50 px-4 py-3 text-sm text-texte-secondaire">
          {portal.message || 'Aucun élève lié à ce compte.'}
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-3">
        <Link to="/notes/resultats" className="card-premium block p-5 transition hover:border-or-cachet/40">
          <FileText className="mb-3 h-5 w-5 text-or-cachet" strokeWidth={1.75} />
          <p className="font-display text-base font-semibold text-encre">Mes résultats</p>
          <p className="mt-1 text-sm text-texte-secondaire">Notes et moyennes</p>
        </Link>
        <Link to="/elearning/devoirs" className="card-premium block p-5 transition hover:border-or-cachet/40">
          <BookOpen className="mb-3 h-5 w-5 text-or-cachet" strokeWidth={1.75} />
          <p className="font-display text-base font-semibold text-encre">Devoirs</p>
          <p className="mt-1 text-sm text-texte-secondaire">Travaux à rendre</p>
        </Link>
        <Link to="/absences" className="card-premium block p-5 transition hover:border-or-cachet/40">
          <ClipboardList className="mb-3 h-5 w-5 text-or-cachet" strokeWidth={1.75} />
          <p className="font-display text-base font-semibold text-encre">Absences</p>
          <p className="mt-1 text-sm text-texte-secondaire">Historique de présence</p>
        </Link>
      </div>
    </div>
  );
}
