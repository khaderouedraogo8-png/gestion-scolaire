import { Link } from 'react-router-dom';
import useAuth from '../../hooks/useAuth';

export default function ParentHome() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Espace parent</h1>
        <p className="page-subtitle">
          Bienvenue {user?.prenom} — consultez les informations de vos enfants
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Link to="/eleves" className="card hover:border-or-cachet/40 transition-colors">
          <span className="text-2xl">👨‍🎓</span>
          <h2 className="mt-2 font-semibold text-encre">Mes enfants</h2>
          <p className="page-subtitle">Fiches élèves et inscriptions</p>
        </Link>
        <Link to="/notes/bulletins" className="card hover:border-or-cachet/40 transition-colors">
          <span className="text-2xl">📝</span>
          <h2 className="mt-2 font-semibold text-encre">Bulletins</h2>
          <p className="page-subtitle">Bulletins publiés (PDF)</p>
        </Link>
        <Link to="/finance/paiements" className="card hover:border-or-cachet/40 transition-colors">
          <span className="text-2xl">💰</span>
          <h2 className="mt-2 font-semibold text-encre">Paiements</h2>
          <p className="page-subtitle">Historique et reçus</p>
        </Link>
        <Link to="/absences" className="card hover:border-or-cachet/40 transition-colors">
          <span className="text-2xl">📋</span>
          <h2 className="mt-2 font-semibold text-encre">Absences</h2>
          <p className="page-subtitle">Suivi des absences de vos enfants</p>
        </Link>
        <Link to="/parent/pedagogie" className="card hover:border-or-cachet/40 transition-colors">
          <span className="text-2xl">📚</span>
          <h2 className="mt-2 font-semibold text-encre">Programme pédagogique</h2>
          <p className="page-subtitle">Devoirs, compositions et cahier de texte</p>
        </Link>
      </div>
    </div>
  );
}
