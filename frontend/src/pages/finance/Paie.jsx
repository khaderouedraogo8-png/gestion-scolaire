import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { comptabiliteApi } from '../../services/api/comptabilite';
import Table from '../../components/Table';
import PageHeader from '../../components/PageHeader';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

export default function Paie() {
  const toast = useToast();
  const [periodes, setPeriodes] = useState([]);
  const [lignes, setLignes] = useState([]);
  const [idPeriode, setIdPeriode] = useState('');
  const [loading, setLoading] = useState(true);
  const [periodeForm, setPeriodeForm] = useState({
    libelle: '',
    date_debut: '',
    date_fin: '',
  });
  const [ligneForm, setLigneForm] = useState({
    id_utilisateur: '',
    matricule: '',
    brut: '',
    retenues: '',
    net: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const p = await comptabiliteApi.listPaiePeriodes();
      const list = Array.isArray(p) ? p : [];
      setPeriodes(list);
      if (!idPeriode && list[0]) setIdPeriode(String(list[0].id));
    } catch {
      toast.error('Impossible de charger la paie');
    } finally {
      setLoading(false);
    }
  }, [toast, idPeriode]);

  useEffect(() => {
    load();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!idPeriode) {
      setLignes([]);
      return;
    }
    comptabiliteApi
      .listPaieLignes({ id_periode: idPeriode })
      .then((d) => setLignes(Array.isArray(d) ? d : []))
      .catch(() => setLignes([]));
  }, [idPeriode]);

  const createPeriode = async (e) => {
    e.preventDefault();
    try {
      const created = await comptabiliteApi.createPaiePeriode(periodeForm);
      toast.success('Période créée');
      setIdPeriode(String(created.id));
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const createLigne = async (e) => {
    e.preventDefault();
    if (!idPeriode) return;
    const brut = Number(ligneForm.brut) || 0;
    const retenues = Number(ligneForm.retenues) || 0;
    const net = ligneForm.net !== '' ? Number(ligneForm.net) : brut - retenues;
    try {
      await comptabiliteApi.createPaieLigne({
        id_periode: idPeriode,
        id_utilisateur: ligneForm.id_utilisateur || null,
        matricule: ligneForm.matricule || null,
        brut: String(brut),
        retenues: String(retenues),
        net: String(net),
      });
      toast.success('Ligne ajoutée');
      const d = await comptabiliteApi.listPaieLignes({ id_periode: idPeriode });
      setLignes(Array.isArray(d) ? d : []);
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const cloturer = async () => {
    if (!idPeriode || !window.confirm('Clôturer cette période de paie ?')) return;
    try {
      await comptabiliteApi.cloturerPaiePeriode(idPeriode);
      toast.success('Période clôturée');
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="SYSCOHADA"
        title="Paie"
        subtitle="Périodes et bulletins de paie"
        actions={
          <Link to="/finance/ecritures" className="btn-secondary">
            Écritures
          </Link>
        }
      />

      <form onSubmit={createPeriode} className="card-premium grid gap-3 p-5 sm:grid-cols-4">
        <FormField label="Libellé" name="libelle" value={periodeForm.libelle} onChange={(e) => setPeriodeForm((f) => ({ ...f, libelle: e.target.value }))} required />
        <FormField label="Début" name="date_debut" type="date" value={periodeForm.date_debut} onChange={(e) => setPeriodeForm((f) => ({ ...f, date_debut: e.target.value }))} required />
        <FormField label="Fin" name="date_fin" type="date" value={periodeForm.date_fin} onChange={(e) => setPeriodeForm((f) => ({ ...f, date_fin: e.target.value }))} required />
        <div className="flex items-end">
          <button type="submit" className="btn-primary w-full">Nouvelle période</button>
        </div>
      </form>

      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[14rem]">
          <label className="label">Période active</label>
          <select className="input" value={idPeriode} onChange={(e) => setIdPeriode(e.target.value)}>
            <option value="">—</option>
            {periodes.map((p) => (
              <option key={p.id} value={String(p.id)}>
                {p.libelle} ({p.statut})
              </option>
            ))}
          </select>
        </div>
        {idPeriode && (
          <button type="button" className="btn-secondary" onClick={cloturer}>
            Clôturer
          </button>
        )}
      </div>

      {idPeriode && (
        <form onSubmit={createLigne} className="card-premium grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-5">
          <FormField label="ID utilisateur" name="id_utilisateur" value={ligneForm.id_utilisateur} onChange={(e) => setLigneForm((f) => ({ ...f, id_utilisateur: e.target.value }))} />
          <FormField label="Matricule" name="matricule" value={ligneForm.matricule} onChange={(e) => setLigneForm((f) => ({ ...f, matricule: e.target.value }))} />
          <FormField label="Brut" name="brut" value={ligneForm.brut} onChange={(e) => setLigneForm((f) => ({ ...f, brut: e.target.value }))} />
          <FormField label="Retenues" name="retenues" value={ligneForm.retenues} onChange={(e) => setLigneForm((f) => ({ ...f, retenues: e.target.value }))} />
          <div className="flex items-end">
            <button type="submit" className="btn-secondary w-full">Ajouter ligne</button>
          </div>
        </form>
      )}

      <Table
        columns={[
          { key: 'matricule', header: 'Matricule', render: (r) => r.matricule || '—' },
          {
            key: 'brut',
            header: 'Brut',
            render: (r) => `${Number(r.brut).toLocaleString('fr-FR')} FCFA`,
          },
          {
            key: 'retenues',
            header: 'Retenues',
            render: (r) => `${Number(r.retenues).toLocaleString('fr-FR')} FCFA`,
          },
          {
            key: 'net',
            header: 'Net',
            render: (r) => (
              <span className="font-semibold">{Number(r.net).toLocaleString('fr-FR')} FCFA</span>
            ),
          },
        ]}
        data={lignes}
        loading={loading}
        emptyMessage="Aucune ligne de paie pour cette période."
      />
    </div>
  );
}
