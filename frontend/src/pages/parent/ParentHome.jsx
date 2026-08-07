import { Link } from 'react-router-dom';
import useAuth from '../../hooks/useAuth';

export default function ParentHome() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Espace parent</h1>
        <p className="text-sm text-slate-500">
          Bienvenue {user?.prenom} — consultez les informations de vos enfants
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Link to="/eleves" className="card hover:border-primary-300 transition-colors">
          <span className="text-2xl">👨‍🎓</span>
          <h2 className="mt-2 font-semibold text-slate-900">Mes enfants</h2>
          <p className="text-sm text-slate-500">Fiches élèves et inscriptions</p>
        </Link>
        <Link to="/notes/bulletins" className="card hover:border-primary-300 transition-colors">
          <span className="text-2xl">📝</span>
          <h2 className="mt-2 font-semibold text-slate-900">Bulletins</h2>
          <p className="text-sm text-slate-500">Bulletins publiés (PDF)</p>
        </Link>
        <Link to="/finance/paiements" className="card hover:border-primary-300 transition-colors">
          <span className="text-2xl">💰</span>
          <h2 className="mt-2 font-semibold text-slate-900">Paiements</h2>
          <p className="text-sm text-slate-500">Historique et reçus</p>
        </Link>
        <Link to="/absences" className="card hover:border-primary-300 transition-colors">
          <span className="text-2xl">📋</span>
          <h2 className="mt-2 font-semibold text-slate-900">Absences</h2>
          <p className="text-sm text-slate-500">Suivi des absences de vos enfants</p>
        </Link>
      </div>
    </div>
  );
}
