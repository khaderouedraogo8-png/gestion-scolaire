import { useEffect, useState } from 'react';
import { emploiApi } from '../../services/api/emploi';
import { usersApi } from '../../services/api/users';
import Table from '../../components/Table';
import Modal from '../../components/Modal';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';
import useAuth from '../../hooks/useAuth';

export default function Enseignants() {
  const toast = useToast();
  const { isAdmin } = useAuth();
  const [enseignants, setEnseignants] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState({
    nom: '',
    prenom: '',
    email: '',
    specialite: '',
    type_contrat: 'permanent',
    id_utilisateur: '',
  });

  const load = () => {
    setLoading(true);
    Promise.all([emploiApi.listEnseignants(), isAdmin ? usersApi.list() : Promise.resolve([])])
      .then(([ens, usr]) => {
        setEnseignants(Array.isArray(ens) ? ens : ens.items || []);
        setUsers(Array.isArray(usr) ? usr.filter((u) => u.role === 'enseignant') : []);
      })
      .catch(() => toast.error('Erreur chargement enseignants'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [toast, isAdmin]);

  const openCreate = () => {
    setEditId(null);
    setForm({
      nom: '',
      prenom: '',
      email: '',
      specialite: '',
      type_contrat: 'permanent',
      id_utilisateur: '',
    });
    setModalOpen(true);
  };

  const openEdit = (e) => {
    setEditId(e.id);
    setForm({
      nom: e.nom,
      prenom: e.prenom,
      email: e.email || '',
      specialite: e.specialite || '',
      type_contrat: e.type_contrat || 'permanent',
      id_utilisateur: e.id_utilisateur ? String(e.id_utilisateur) : '',
    });
    setModalOpen(true);
  };

  const handleSubmit = async (ev) => {
    ev.preventDefault();
    const payload = {
      ...form,
      id_utilisateur: form.id_utilisateur || null,
    };
    try {
      if (editId) {
        await emploiApi.updateEnseignant(editId, payload);
        toast.success('Enseignant mis à jour');
      } else {
        await emploiApi.createEnseignant(payload);
        toast.success('Enseignant ajouté');
      }
      setModalOpen(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  const columns = [
    { key: 'nom', header: 'Nom', render: (r) => `${r.prenom} ${r.nom}` },
    { key: 'specialite', header: 'Spécialité', render: (r) => r.specialite || '—' },
    { key: 'email', header: 'Email', render: (r) => r.email || '—' },
    { key: 'type_contrat', header: 'Contrat', render: (r) => r.type_contrat || '—' },
    {
      key: 'compte',
      header: 'Compte utilisateur',
      render: (r) => (r.id_utilisateur ? 'Lié' : '—'),
    },
    ...(isAdmin
      ? [
          {
            key: 'actions',
            header: '',
            render: (r) => (
              <button type="button" onClick={() => openEdit(r)} className="text-primary-600 hover:underline text-xs">
                Modifier
              </button>
            ),
          },
        ]
      : []),
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Enseignants</h1>
          <p className="text-sm text-slate-500">Personnel enseignant et lien compte utilisateur</p>
        </div>
        {isAdmin && (
          <button type="button" className="btn-primary" onClick={openCreate}>
            + Ajouter
          </button>
        )}
      </div>
      <Table columns={columns} data={enseignants} loading={loading} emptyMessage="Aucun enseignant" />
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editId ? 'Modifier enseignant' : 'Nouvel enseignant'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField
            label="Prénom"
            value={form.prenom}
            onChange={(e) => setForm({ ...form, prenom: e.target.value })}
            required
          />
          <FormField
            label="Nom"
            value={form.nom}
            onChange={(e) => setForm({ ...form, nom: e.target.value })}
            required
          />
          <FormField
            label="Email"
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
          <FormField
            label="Spécialité"
            value={form.specialite}
            onChange={(e) => setForm({ ...form, specialite: e.target.value })}
          />
          <FormField
            label="Type de contrat"
            name="type_contrat"
            type="select"
            value={form.type_contrat}
            onChange={(e) => setForm({ ...form, type_contrat: e.target.value })}
            options={[
              { value: 'permanent', label: 'Permanent' },
              { value: 'vacataire', label: 'Vacataire' },
              { value: 'CDD', label: 'CDD' },
            ]}
          />
          {isAdmin && (
            <FormField
              label="Compte utilisateur (enseignant)"
              name="id_utilisateur"
              type="select"
              value={form.id_utilisateur}
              onChange={(e) => setForm({ ...form, id_utilisateur: e.target.value })}
              options={[
                { value: '', label: '— Aucun —' },
                ...users.map((u) => ({
                  value: String(u.id),
                  label: `${u.prenom} ${u.nom} (${u.email})`,
                })),
              ]}
            />
          )}
          <button type="submit" className="btn-primary w-full">
            Enregistrer
          </button>
        </form>
      </Modal>
    </div>
  );
}
