import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Calendar, GraduationCap, UserCircle } from 'lucide-react';
import { emploiApi } from '../../services/api/emploi';
import { configApi } from '../../services/api/config';
import { downloadBlob } from '../../services/api/pedagogie';
import Breadcrumb from '../../components/Breadcrumb';
import DetailHeader from '../../components/DetailHeader';
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
      <div className="flex flex-col items-center justify-center gap-4 py-32">
        <div className="loading-ring" />
        <p className="text-sm text-texte-secondaire">Chargement de la fiche…</p>
      </div>
    );
  }

  if (!enseignant) {
    return (
      <div className="space-y-6">
        <Breadcrumb
          items={[
            { label: 'Enseignants', to: '/emploi/enseignants' },
            { label: 'Introuvable' },
          ]}
        />
        <p className="text-sm text-texte-secondaire">Enseignant introuvable.</p>
        <Link to="/emploi/enseignants" className="btn-secondary inline-flex">
          Retour aux enseignants
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <DetailHeader
        breadcrumb={
          <Breadcrumb
            items={[
              { label: 'Enseignants', to: '/emploi/enseignants' },
              { label: `${enseignant.prenom} ${enseignant.nom}` },
            ]}
          />
        }
        eyebrow="Emploi du temps"
        title={`${enseignant.prenom} ${enseignant.nom}`}
        subtitle={`${enseignant.specialite || '—'} — ${enseignant.type_contrat || '—'}`}
        media={
          <div className="stat-card-icon bg-or-cachet-clair text-or-cachet">
            <UserCircle className="h-[22px] w-[22px]" strokeWidth={1.75} />
          </div>
        }
        actions={
          <button type="button" className="btn-secondary" onClick={handlePrint}>
            Imprimer la fiche
          </button>
        }
      />

      <p className="text-sm text-encre">
        Volume horaire hebdomadaire :{' '}
        <strong className="tabular-nums">{Number(enseignant.volume_horaire_total || 0).toFixed(1)} h</strong>
      </p>

      <section>
        <h2 className="section-title !text-base">Affectations</h2>
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
          emptyIcon={GraduationCap}
          emptyMessage="Aucune affectation pour l'année en cours."
        />
      </section>

      <section>
        <h2 className="section-title !text-base">Emploi du temps</h2>
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
          emptyIcon={Calendar}
          emptyMessage="Aucun créneau planifié."
        />
      </section>
    </div>
  );
}
