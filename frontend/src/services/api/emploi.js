import apiClient from './client';

export const emploiApi = {
  listEnseignants: async () => {
    const { data } = await apiClient.get('/emploi-temps/enseignants');
    return data;
  },

  createEnseignant: async (payload) => {
    const { data } = await apiClient.post('/emploi-temps/enseignants', payload);
    return data;
  },

  listMatieres: async () => {
    const { data } = await apiClient.get('/notes/matieres');
    return data;
  },

  listAffectations: async (params = {}) => {
    const { data } = await apiClient.get('/emploi-temps/affectations', { params });
    return data;
  },

  createAffectation: async (payload) => {
    const { data } = await apiClient.post('/emploi-temps/affectations', payload);
    return data;
  },

  deleteAffectation: async (id) => {
    const { data } = await apiClient.delete(`/emploi-temps/affectations/${id}`);
    return data;
  },

  listSalles: async () => {
    const { data } = await apiClient.get('/emploi-temps/salles');
    return data;
  },

  createSalle: async (payload) => {
    const { data } = await apiClient.post('/emploi-temps/salles', payload);
    return data;
  },

  listCreneaux: async (params = {}) => {
    const { data } = await apiClient.get('/emploi-temps/creneaux', { params });
    return data;
  },

  createCreneau: async (payload) => {
    const { data } = await apiClient.post('/emploi-temps/creneaux', payload);
    return data;
  },

  updateCreneau: async (id, payload) => {
    const { data } = await apiClient.put(`/emploi-temps/creneaux/${id}`, payload);
    return data;
  },

  deleteCreneau: async (id) => {
    const { data } = await apiClient.delete(`/emploi-temps/creneaux/${id}`);
    return data;
  },

  updateEnseignant: async (id, payload) => {
    const { data } = await apiClient.put(`/emploi-temps/enseignants/${id}`, payload);
    return data;
  },
};
