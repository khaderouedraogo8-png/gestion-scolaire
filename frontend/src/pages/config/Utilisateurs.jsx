import { useEffect, useState } from 'react';
import { usersApi } from '../../services/api/users';
import FormField from '../../components/FormField';
import Modal from '../../components/Modal';
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
      toast.error('Erreur chargement utilisateurs');
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
      toast.error(err.response?.data?.message || 'Erreur création');
    }
  };

  const handleReset = async (id) => {
    try {
      const res = await usersApi.resetPassword(id);
      toast.success(`MDP temporaire : ${res.mot_de_passe_temporaire}`);
    } catch {
      toast.error('Erreur réinitialisation');
    }
  };

  const toggleActif = async (user) => {
    try {
      await usersApi.update(user.id, { actif: !user.actif });
      load();
    } catch {
      toast.error('Erreur mise à jour');
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
      toast.error(err.response?.data?.message || 'Erreur');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Utilisateurs</h1>
          <p className="text-sm text-slate-500">Comptes et rôles d'accès</p>
        </div>
        <button type="button" onClick={() => setModal(true)} className="btn-primary">
          + Nouvel utilisateur
        </button>
      </div>

      {loading ? (
        <p className="text-slate-500">Chargement...</p>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Nom</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Rôle</th>
                <th className="px-4 py-3">Statut</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t border-slate-100">
                  <td className="px-4 py-3">
                    {u.prenom} {u.nom}
                  </td>
                  <td className="px-4 py-3">{u.email}</td>
                  <td className="px-4 py-3 capitalize">{u.role?.replace('_', ' ')}</td>
                  <td className="px-4 py-3">
                    <span className={u.actif ? 'badge-success' : 'badge-neutral'}>
                      {u.actif ? 'Actif' : 'Inactif'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <button type="button" onClick={() => openEdit(u)} className="text-slate-600 hover:underline">
                      Modifier
                    </button>
                    <button type="button" onClick={() => handleReset(u.id)} className="text-primary-600 hover:underline">
                      Réinit. MDP
                    </button>
                    <button type="button" onClick={() => toggleActif(u)} className="text-slate-600 hover:underline">
                      {u.actif ? 'Désactiver' : 'Activer'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

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
