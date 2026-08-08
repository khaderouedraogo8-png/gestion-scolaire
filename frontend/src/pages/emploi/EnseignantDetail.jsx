import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { emploiApi } from '../../services/api/emploi';
import { configApi } from '../../services/api/config';
import { downloadBlob } from '../../services/api/pedagogie';
import Table from '../../components/Table';
import { useToast } from '../../components/Toast';

export default function EnseignantDetail() {
  const { id } = useParams();
  const toast = useToast();
  const [enseignant, setEnseignant] = useState(null);
  const [idAnnee, setIdAnnee] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      try {
        const annees = await configApi.listAnnees();
        const list = Array.isArray(annees) ? annees : annees.items || [];
        const active = list.find((a) => a.est_active);
        if (!active) return;
        if (!cancelled) setIdAnnee(active.id);
        const data = await emploiApi.getEnseignant(id, { id_annee: active.id });
        if (!cancelled) setEnseignant(data);
      } catch {
        if (!cancelled) toast.error('Impossible de charger la fiche enseignant.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [id, toast]);

  const handlePrint = async () => {
    try {
      const blob = await emploiApi.getEnseignantPdf(id, { id_annee: idAnnee });
      downloadBlob(blob, `fiche_${enseignant?.nom || 'enseignant'}.pdf`);
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur PDF');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-or-cachet-clair border-t-or-cachet" />
      </div>
    );
  }

  if (!enseignant) {
    return (
      <div className="space-y-4">
        <Link to="/emploi/enseignants" className="text-sm text-or-cachet hover:underline">
          ← Retour aux enseignants
        </Link>
        <p className="text-sm text-texte-secondaire">Enseignant introuvable.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Link to="/emploi/enseignants" className="text-sm text-or-cachet hover:underline">
        ← Retour aux enseignants
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">
            {enseignant.prenom} {enseignant.nom}
          </h1>
          <p className="page-subtitle">
            {enseignant.specialite || '—'} — {enseignant.type_contrat || '—'}
          </p>
          <p className="mt-2 text-sm text-encre">
            Volume horaire hebdomadaire :{' '}
            <strong>{Number(enseignant.volume_horaire_total || 0).toFixed(1)} h</strong>
          </p>
        </div>
        <button type="button" className="btn-secondary" onClick={handlePrint}>
          Imprimer la fiche
        </button>
      </div>

      <div>
        <h2 className="mb-3 font-semibold text-encre">Affectations</h2>
        <Table
          columns={[
            { key: 'classe_nom', header: 'Classe' },
            { key: 'matiere_nom', header: 'Matière' },
            {
              key: 'volume_horaire_hebdo',
              header: 'Volume h/sem.',
              render: (r) => r.volume_horaire_hebdo ?? '—',
            },
          ]}
          data={enseignant.affectations || []}
          emptyMessage="Aucune affectation pour l'année en cours."
        />
      </div>

      <div>
        <h2 className="mb-3 font-semibold text-encre">Emploi du temps</h2>
        <Table
          columns={[
            { key: 'jour_libelle', header: 'Jour' },
            {
              key: 'horaire',
              header: 'Horaire',
              render: (r) => `${r.heure_debut || '—'} – ${r.heure_fin || '—'}`,
            },
            { key: 'classe_nom', header: 'Classe' },
            { key: 'matiere_nom', header: 'Matière' },
            { key: 'salle_libelle', header: 'Salle', render: (r) => r.salle_libelle || '—' },
          ]}
          data={enseignant.creneaux || []}
          emptyMessage="Aucun créneau planifié."
        />
      </div>
    </div>
  );
}
