import { useCallback, useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import { fratriesApi } from '../../services/api/fratries';
import { elevesApi } from '../../services/api/eleves';
import { financeApi } from '../../services/api/finance';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';
import { emptyIcons } from '../../utils/emptyIcons';

export default function Fratries() {
  const toast = useToast();
  const [fratries, setFratries] = useState([]);
  const [remises, setRemises] = useState([]);
  const [loading, setLoading] = useState(true);
  const [libelle, setLibelle] = useState('');
  const [linkFratrie, setLinkFratrie] = useState('');
  const [matricule, setMatricule] = useState('');
  const [remiseForm, setRemiseForm] = useState({
    code: '',
    libelle: '',
    type_remise: 'pourcent',
    valeur: '',
    condition_type: 'fratrie',
    condition_valeur: '2',
  });
  const [applyForm, setApplyForm] = useState({ id_eleve: '', id_frais: '', id_remise_regle: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [f, r] = await Promise.all([fratriesApi.list(), fratriesApi.listRemises()]);
      setFratries(Array.isArray(f) ? f : []);
      setRemises(Array.isArray(r) ? r : []);
    } catch {
      toast.error('Impossible de charger les fratries');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const createFratrie = async (e) => {
    e.preventDefault();
    try {
      await fratriesApi.create({ libelle: libelle.trim() || null });
      setLibelle('');
      toast.success('Fratrie créée');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur création');
    }
  };

  const linkEleve = async (e) => {
    e.preventDefault();
    if (!linkFratrie || !matricule.trim()) return;
    try {
      const found = await elevesApi.list({ q: matricule.trim(), per_page: 5 });
      const items = found.items || found || [];
      const eleve = items.find(
        (x) => String(x.matricule).toLowerCase() === matricule.trim().toLowerCase()
      ) || items[0];
      if (!eleve) {
        toast.error('Élève introuvable');
        return;
      }
      await fratriesApi.linkEleve(linkFratrie, eleve.id);
      toast.success('Élève lié');
      setMatricule('');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Liaison impossible');
    }
  };

  const createRemise = async (e) => {
    e.preventDefault();
    try {
      await fratriesApi.createRemise({
        ...remiseForm,
        valeur: String(remiseForm.valeur),
      });
      toast.success('Règle de remise créée');
      setRemiseForm({
        code: '',
        libelle: '',
        type_remise: 'pourcent',
        valeur: '',
        condition_type: 'fratrie',
        condition_valeur: '2',
      });
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur remise');
    }
  };

  const appliquer = async (e) => {
    e.preventDefault();
    try {
      const res = await financeApi.appliquerRemise(applyForm);
      toast.success(
        `Remise appliquée — net ${Number(res.montant_net).toLocaleString('fr-FR')} FCFA`
      );
    } catch (err) {
      toast.error(err.response?.data?.message || 'Application impossible');
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Élèves"
        title="Fratries & remises"
        subtitle="Regrouper les frères et sœurs et appliquer des réductions"
      />

      <form onSubmit={createFratrie} className="card-premium flex flex-wrap items-end gap-3 p-5">
        <div className="min-w-[12rem] flex-1">
          <FormField
            label="Nouvelle fratrie"
            name="libelle"
            value={libelle}
            onChange={(e) => setLibelle(e.target.value)}
            placeholder="Famille Koné"
          />
        </div>
        <button type="submit" className="btn-primary mb-0.5">
          <Plus className="h-4 w-4" /> Créer
        </button>
      </form>

      <Table
        columns={[
          { key: 'libelle', header: 'Libellé', render: (r) => r.libelle || '—' },
          {
            key: 'eleves',
            header: 'Élèves',
            render: (r) =>
              (r.eleves || [])
                .map((e) => `${e.prenom} ${e.nom}`)
                .join(', ') || '—',
          },
          {
            key: 'count',
            header: 'Effectif',
            render: (r) => (r.eleves || []).length,
          },
        ]}
        data={fratries}
        loading={loading}
        emptyIcon={emptyIcons.eleves}
        emptyMessage="Aucune fratrie enregistrée."
      />

      <form onSubmit={linkEleve} className="card-premium grid gap-3 p-5 sm:grid-cols-3">
        <FormField
          label="Fratrie"
          name="linkFratrie"
          type="select"
          value={linkFratrie}
          onChange={(e) => setLinkFratrie(e.target.value)}
          options={fratries.map((f) => ({
            value: String(f.id),
            label: f.libelle || String(f.id).slice(0, 8),
          }))}
        />
        <FormField
          label="Matricule élève"
          name="matricule"
          value={matricule}
          onChange={(e) => setMatricule(e.target.value)}
        />
        <div className="flex items-end">
          <button type="submit" className="btn-secondary w-full">
            Lier l’élève
          </button>
        </div>
      </form>

      <div>
        <h2 className="dashboard-section-label">Règles de remise</h2>
        <Table
          columns={[
            { key: 'code', header: 'Code' },
            { key: 'libelle', header: 'Libellé' },
            {
              key: 'valeur',
              header: 'Valeur',
              render: (r) =>
                r.type_remise === 'pourcent' ? `${r.valeur} %` : `${r.valeur} FCFA`,
            },
            {
              key: 'actif',
              header: 'Actif',
              render: (r) => (r.actif ? 'Oui' : 'Non'),
            },
          ]}
          data={remises}
          loading={false}
          emptyMessage="Aucune règle de remise."
        />
      </div>

      <form onSubmit={createRemise} className="card-premium grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-3">
        <FormField
          label="Code"
          name="code"
          value={remiseForm.code}
          onChange={(e) => setRemiseForm((f) => ({ ...f, code: e.target.value }))}
          required
        />
        <FormField
          label="Libellé"
          name="libelle_remise"
          value={remiseForm.libelle}
          onChange={(e) => setRemiseForm((f) => ({ ...f, libelle: e.target.value }))}
          required
        />
        <FormField
          label="Type"
          name="type_remise"
          type="select"
          value={remiseForm.type_remise}
          onChange={(e) => setRemiseForm((f) => ({ ...f, type_remise: e.target.value }))}
          options={[
            { value: 'pourcent', label: 'Pourcentage' },
            { value: 'montant', label: 'Montant fixe' },
          ]}
        />
        <FormField
          label="Valeur"
          name="valeur"
          value={remiseForm.valeur}
          onChange={(e) => setRemiseForm((f) => ({ ...f, valeur: e.target.value }))}
          required
        />
        <div className="flex items-end sm:col-span-2">
          <button type="submit" className="btn-primary">
            Ajouter la règle
          </button>
        </div>
      </form>

      <form onSubmit={appliquer} className="card-premium grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4">
        <h3 className="section-title sm:col-span-2 lg:col-span-4 !text-base">Appliquer une remise</h3>
        <FormField
          label="ID élève"
          name="id_eleve"
          value={applyForm.id_eleve}
          onChange={(e) => setApplyForm((f) => ({ ...f, id_eleve: e.target.value }))}
        />
        <FormField
          label="ID frais"
          name="id_frais"
          value={applyForm.id_frais}
          onChange={(e) => setApplyForm((f) => ({ ...f, id_frais: e.target.value }))}
        />
        <FormField
          label="Règle"
          name="id_remise_regle"
          type="select"
          value={applyForm.id_remise_regle}
          onChange={(e) => setApplyForm((f) => ({ ...f, id_remise_regle: e.target.value }))}
          options={remises.map((r) => ({ value: String(r.id), label: r.libelle }))}
        />
        <div className="flex items-end">
          <button type="submit" className="btn-secondary w-full">
            Appliquer
          </button>
        </div>
      </form>
    </div>
  );
}
