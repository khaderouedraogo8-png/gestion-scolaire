import apiClient from './client';

export const fratriesApi = {
  list: async () => {
    const { data } = await apiClient.get('/fratries/');
    return data;
  },

  get: async (id) => {
    const { data } = await apiClient.get(`/fratries/${id}`);
    return data;
  },

  create: async (payload) => {
    const { data } = await apiClient.post('/fratries/', payload);
    return data;
  },

  update: async (id, payload) => {
    const { data } = await apiClient.put(`/fratries/${id}`, payload);
    return data;
  },

  remove: async (id) => {
    const { data } = await apiClient.delete(`/fratries/${id}`);
    return data;
  },

  linkEleve: async (idFratrie, idEleve) => {
    const { data } = await apiClient.post(`/fratries/${idFratrie}/eleves`, { id_eleve: idEleve });
    return data;
  },

  unlinkEleve: async (idFratrie, idEleve) => {
    const { data } = await apiClient.delete(`/fratries/${idFratrie}/eleves/${idEleve}`);
    return data;
  },

  listRemises: async () => {
    const { data } = await apiClient.get('/fratries/remises');
    return data;
  },

  createRemise: async (payload) => {
    const { data } = await apiClient.post('/fratries/remises', payload);
    return data;
  },

  updateRemise: async (id, payload) => {
    const { data } = await apiClient.put(`/fratries/remises/${id}`, payload);
    return data;
  },

  removeRemise: async (id) => {
    const { data } = await apiClient.delete(`/fratries/remises/${id}`);
    return data;
  },
};
