import { Link } from 'react-router-dom';
import { BookOpen, ClipboardList, FileText } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import useAuth from '../../hooks/useAuth';

/** Stub portail élève — espace lecture notes / devoirs. */
export default function EleveHome() {
  const { user } = useAuth();

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Espace élève"
        title={`Bonjour${user?.prenom ? `, ${user.prenom}` : ''}`}
        subtitle="Consultez vos notes, devoirs et absences"
      />

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

      <div className="rounded-lg border border-bordure/60 bg-craie/50 px-4 py-3 text-sm text-texte-secondaire">
        Portail élève en cours d&apos;enrichissement — les modules ci-dessus dépendent des droits
        attribués à votre compte.
      </div>
    </div>
  );
}
