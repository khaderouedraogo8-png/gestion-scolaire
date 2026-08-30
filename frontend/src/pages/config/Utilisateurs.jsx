import { useEffect, useRef, useState } from 'react';
import { usersApi } from '../../services/api/users';
import Table from '../../components/Table';
import { emptyIcons } from '../../utils/emptyIcons';
import FormField from '../../components/FormField';
import Modal from '../../components/Modal';
import PageHeader from '../../components/PageHeader';
import { useToast } from '../../components/Toast';

const ROLES = [
  { value: 'administrateur', label: 'Administrateur' },
  { value: 'directeur', label: 'Directeur' },
  { value: 'secretariat', label: 'Secrétariat' },
  { value: 'enseignant', label: 'Enseignant' },
  { value: 'agent_comptable', label: 'Comptable' },
  { value: 'parent', label: 'Parent' },
];

export default function Utilisateurs() {
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;

  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [editModal, setEditModal] = useState(false);
  const [editUser, setEditUser] = useState(null);
  const [form, setForm] = useState({
    nom: '',
    prenom: '',
    email: '',
    telephone: '',
    role: 'secretariat',
    password: '',
  });

  const load = async () => {
    setLoading(true);
    try {
      const data = await usersApi.list();
      setUsers(data);
    } catch {
      toastRef.current.error('Impossible de charger les utilisateurs. Réessayez.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await usersApi.create(form);
      toast.success('Utilisateur créé');
      setModal(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur lors de la création');
    }
  };

  const handleReset = async (id) => {
    try {
      const res = await usersApi.resetPassword(id);
      toast.success(`MDP temporaire : ${res.mot_de_passe_temporaire}`);
    } catch {
      toast.error('Impossible de réinitialiser le mot de passe');
    }
  };

  const toggleActif = async (user) => {
    try {
      await usersApi.update(user.id, { actif: !user.actif });
      load();
    } catch {
      toast.error('Impossible de mettre à jour le statut');
    }
  };

  const openEdit = (user) => {
    setEditUser({
      id: user.id,
      nom: user.nom,
      prenom: user.prenom,
      email: user.email,
      telephone: user.telephone || '',
      role: user.role,
    });
    setEditModal(true);
  };

  const handleEdit = async (e) => {
    e.preventDefault();
    try {
      await usersApi.update(editUser.id, {
        nom: editUser.nom,
        prenom: editUser.prenom,
        email: editUser.email,
        telephone: editUser.telephone,
        role: editUser.role,
      });
      toast.success('Utilisateur mis à jour');
      setEditModal(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Erreur lors de la mise à jour');
    }
  };

  const columns = [
    {
      key: 'nom',
      header: 'Nom',
      render: (r) => (
        <span className="font-medium">
          {r.prenom} {r.nom}
        </span>
      ),
    },
    { key: 'email', header: 'Email' },
    {
      key: 'role',
      header: 'Rôle',
      render: (r) => <span className="capitalize">{r.role?.replace('_', ' ')}</span>,
    },
    {
      key: 'statut',
      header: 'Statut',
      render: (r) => (
        <span className={r.actif ? 'badge-success' : 'badge-neutral'}>
          {r.actif ? 'Actif' : 'Inactif'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      render: (r) => (
        <div className="space-x-2 text-right text-sm">
          <button type="button" onClick={() => openEdit(r)} className="text-texte-secondaire hover:underline">
            Modifier
          </button>
          <button type="button" onClick={() => handleReset(r.id)} className="text-or-cachet hover:underline">
            Réinit. MDP
          </button>
          <button type="button" onClick={() => toggleActif(r)} className="text-texte-secondaire hover:underline">
            {r.actif ? 'Désactiver' : 'Activer'}
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Configuration"
        title="Utilisateurs"
        subtitle="Comptes et rôles d'accès"
        actions={
          <button type="button" onClick={() => setModal(true)} className="btn-primary">
            + Nouvel utilisateur
          </button>
        }
      />

      <Table
        columns={columns}
        data={users}
        loading={loading}
        emptyIcon={emptyIcons.utilisateurs}
        emptyMessage="Aucun utilisateur pour l'instant — créez un compte via le bouton ci-dessus."
      />

      <Modal isOpen={modal} onClose={() => setModal(false)} title="Nouvel utilisateur">
        <form onSubmit={handleCreate} className="space-y-4">
          <FormField label="Nom" value={form.nom} onChange={(e) => setForm({ ...form, nom: e.target.value })} required />
          <FormField label="Prénom" value={form.prenom} onChange={(e) => setForm({ ...form, prenom: e.target.value })} required />
          <FormField label="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          <FormField label="Téléphone" value={form.telephone} onChange={(e) => setForm({ ...form, telephone: e.target.value })} />
          <FormField label="Rôle" type="select" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} options={ROLES} required />
          <FormField label="Mot de passe" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
          <button type="submit" className="btn-primary w-full">
            Créer
          </button>
        </form>
      </Modal>

      <Modal isOpen={editModal} onClose={() => setEditModal(false)} title="Modifier utilisateur">
        {editUser && (
          <form onSubmit={handleEdit} className="space-y-4">
            <FormField label="Nom" value={editUser.nom} onChange={(e) => setEditUser({ ...editUser, nom: e.target.value })} required />
            <FormField label="Prénom" value={editUser.prenom} onChange={(e) => setEditUser({ ...editUser, prenom: e.target.value })} required />
            <FormField label="Email" type="email" value={editUser.email} onChange={(e) => setEditUser({ ...editUser, email: e.target.value })} required />
            <FormField label="Téléphone" value={editUser.telephone} onChange={(e) => setEditUser({ ...editUser, telephone: e.target.value })} />
            <FormField label="Rôle" type="select" value={editUser.role} onChange={(e) => setEditUser({ ...editUser, role: e.target.value })} options={ROLES} required />
            <button type="submit" className="btn-primary w-full">
              Enregistrer
            </button>
          </form>
        )}
      </Modal>
    </div>
  );
}
