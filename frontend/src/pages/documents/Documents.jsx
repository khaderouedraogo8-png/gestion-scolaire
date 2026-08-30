import { useCallback, useEffect, useState } from 'react';
import { documentsApi } from '../../services/api/documents';
import { configApi } from '../../services/api/config';
import { elevesApi } from '../../services/api/eleves';
import Table from '../../components/Table';
import { emptyIcons } from '../../utils/emptyIcons';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';

const DOC_TYPES = {
  attestation_scolarite: 'Attestation de scolarité',
  carte_scolaire: 'Carte scolaire',
  certificat: 'Certificat',
  diplome: 'Diplôme',
};

export default function Documents() {
  const toast = useToast();

  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [docType, setDocType] = useState('attestation_scolarite');
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');
  const [eleves, setEleves] = useState([]);
  const [annees, setAnnees] = useState([]);
  const [form, setForm] = useState({
    id_eleve: '',
    id_annee: '',
    date_expiration: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await documentsApi.list({
        type_document: typeFilter || undefined,
      });
      setDocuments(data.items || data || []);
    } catch {
      toast.error('Erreur lors du chargement des documents');
    } finally {
      setLoading(false);
    }
  }, [typeFilter, toast]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    configApi.listAnnees().then((d) => {
      const list = d.items || d || [];
      setAnnees(list);
      const active = list.find((a) => a.est_active);
      if (active) setForm((f) => ({ ...f, id_annee: String(active.id) }));
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (search.length < 2) {
      setEleves([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const data = await elevesApi.list({ q: search, statut: 'inscrit', per_page: 10 });
        setEleves(data.items || data.eleves || data || []);
      } catch {
        /* ignore */
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!form.id_eleve) {
      toast.error('Veuillez sélectionner un élève');
      return;
    }
    setSaving(true);
    try {
      const payload = {
        id_eleve: form.id_eleve,
        id_annee: form.id_annee || undefined,
        date_expiration: form.date_expiration || undefined,
      };
      if (docType === 'carte_scolaire') {
        await documentsApi.genererCarte(payload);
      } else if (docType === 'certificat') {
        await documentsApi.genererCertificat(payload);
      } else if (docType === 'diplome') {
        await documentsApi.genererDiplome(payload);
      } else {
        await documentsApi.genererAttestation(payload);
      }
      toast.success('Document généré avec succès');
      setModalOpen(false);
      setSearch('');
      setForm({ id_eleve: '', id_annee: form.id_annee, date_expiration: '' });
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur lors de la génération');
    } finally {
      setSaving(false);
    }
  };

  const handleDownload = async (id, type) => {
    try {
      const blob = await documentsApi.download(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${type || 'document'}-${id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('Erreur lors du téléchargement');
    }
  };

  const columns = [
    {
      key: 'type',
      header: 'Type',
      render: (r) => (
        <span className="font-medium">{DOC_TYPES[r.type_document] || r.type_document}</span>
      ),
    },
    {
      key: 'eleve',
      header: 'Élève',
      render: (r) => `${r.eleve?.prenom || r.prenom || ''} ${r.eleve?.nom || r.nom || ''}`,
    },
    { key: 'date', header: 'Émission', render: (r) => r.date_emission || '—' },
    { key: 'expiration', header: 'Expiration', render: (r) => r.date_expiration || '—' },
    {
      key: 'actions',
      header: '',
      render: (r) => (
        <button
          type="button"
          onClick={() => handleDownload(r.id, r.type_document)}
          className="text-sm font-medium text-or-cachet hover:underline"
        >
          Télécharger PDF
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Documents"
        title="Documents administratifs"
        subtitle="Génération d'attestations, cartes et certificats"
        actions={
          <button type="button" onClick={() => setModalOpen(true)} className="btn-primary">
            + Générer un document
          </button>
        }
      />

      <Table
        columns={columns}
        data={documents}
        loading={loading}
        filters={
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="input w-auto"
          >
            <option value="">Tous les types</option>
            {Object.entries(DOC_TYPES).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        }
        emptyIcon={emptyIcons.documents}
        emptyMessage="Aucun document pour l'instant — utilisez le formulaire ci-dessus pour en générer un."
      />

      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Générer un document"
        size="lg"
        footer={
          <>
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary">
              Annuler
            </button>
            <button type="submit" form="doc-form" disabled={saving} className="btn-primary">
              {saving ? 'Génération...' : 'Générer'}
            </button>
          </>
        }
      >
        <form id="doc-form" onSubmit={handleGenerate} className="space-y-4">
          <FormField
            label="Type de document"
            name="docType"
            type="select"
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
            options={[
              { value: 'attestation_scolarite', label: 'Attestation de scolarité' },
              { value: 'carte_scolaire', label: 'Carte scolaire' },
              { value: 'certificat', label: 'Certificat de scolarité' },
            ]}
          />
          <div className="relative">
            <FormField
              label="Rechercher un élève"
              name="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Nom, prénom ou matricule..."
              required
            />
            {eleves.length > 0 && (
              <ul className="absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-lg border border-bordure bg-blanc ">
                {eleves.map((el) => (
                  <li key={el.id}>
                    <button
                      type="button"
                      onClick={() => {
                        setForm({ ...form, id_eleve: el.id });
                        setSearch(`${el.prenom} ${el.nom}`);
                        setEleves([]);
                      }}
                      className="w-full px-4 py-2 text-left text-sm hover:bg-craie"
                    >
                      <span className="font-medium">{el.prenom} {el.nom}</span>
                      <span className="ml-2 text-texte-secondaire">{el.matricule}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <FormField
            label="Année scolaire"
            name="id_annee"
            type="select"
            value={form.id_annee}
            onChange={(e) => setForm({ ...form, id_annee: e.target.value })}
            options={annees.map((a) => ({ value: String(a.id), label: a.libelle }))}
          />
          {docType === 'carte_scolaire' && (
            <FormField
              label="Date d'expiration"
              name="date_expiration"
              type="date"
              value={form.date_expiration}
              onChange={(e) => setForm({ ...form, date_expiration: e.target.value })}
            />
          )}
        </form>
      </Modal>
    </div>
  );
}
