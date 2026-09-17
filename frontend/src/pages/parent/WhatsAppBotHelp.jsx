import { Link } from 'react-router-dom';
import { MessageCircle, ArrowLeft } from 'lucide-react';
import PageHeader from '../../components/PageHeader';

const KEYWORDS = [
  {
    cmd: 'SOLDE',
    desc: 'Solde et arriérés de scolarité pour chaque enfant lié à votre numéro.',
  },
  {
    cmd: 'NOTES',
    desc: 'Dernières notes publiées (évaluations clôturées).',
  },
  {
    cmd: 'ECHEANCES',
    desc: 'Échéances de paiement à venir dans les 7 prochains jours.',
  },
  {
    cmd: 'ABSENCES',
    desc: 'Absences récentes (30 derniers jours), justifiées ou non.',
  },
  {
    cmd: 'AIDE',
    desc: 'Liste des commandes disponibles.',
  },
];

/** Aide bot WhatsApp parent — mots-clés. */
export default function WhatsAppBotHelp() {
  return (
    <div className="space-y-8">
      <Link to="/parent" className="inline-flex items-center gap-1 text-sm text-or-cachet hover:underline">
        <ArrowLeft className="h-4 w-4" strokeWidth={1.75} />
        Retour espace parent
      </Link>

      <PageHeader
        eyebrow="Messagerie"
        title="Bot WhatsApp parent"
        subtitle="Interrogez le solde, les notes et les absences par SMS WhatsApp"
      />

      <div className="flex items-start gap-3 rounded-lg border border-bordure/60 bg-craie/40 px-4 py-3 text-sm text-texte-secondaire">
        <MessageCircle className="mt-0.5 h-5 w-5 shrink-0 text-or-cachet" strokeWidth={1.75} />
        <p>
          Envoyez l&apos;un des mots-clés ci-dessous au numéro WhatsApp de l&apos;établissement.
          Votre téléphone doit être enregistré sur votre fiche parent (
          <span className="font-medium text-encre">ParentTuteur.telephone</span>
          ).
        </p>
      </div>

      <ul className="divide-y divide-bordure/50 overflow-hidden rounded-lg border border-bordure/60 bg-blanc">
        {KEYWORDS.map(({ cmd, desc }) => (
          <li key={cmd} className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-baseline sm:gap-6">
            <code className="shrink-0 font-mono text-sm font-semibold tracking-wide text-or-cachet">
              {cmd}
            </code>
            <p className="text-sm text-texte-secondaire">{desc}</p>
          </li>
        ))}
      </ul>

      <p className="text-xs text-texte-secondaire">
        Mode sandbox : l&apos;établissement peut tester via{' '}
        <code className="font-mono">POST /api/webhooks/whatsapp</code> avec un corps{' '}
        <code className="font-mono">{'{"{from, text}"}'}</code>.
      </p>
    </div>
  );
}
