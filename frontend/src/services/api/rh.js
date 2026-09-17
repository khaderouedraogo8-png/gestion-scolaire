import apiClient from './client';

export const rhApi = {
  listContrats: async (params = {}) => {
    const { data } = await apiClient.get('/rh/contrats', { params });
    return data;
  },
  alertesExpirationContrats: async (params = {}) => {
    const { data } = await apiClient.get('/rh/contrats/alertes-expiration', { params });
    return data;
  },
  getContrat: async (id) => {
    const { data } = await apiClient.get(`/rh/contrats/${id}`);
    return data;
  },
  createContrat: async (payload) => {
    const { data } = await apiClient.post('/rh/contrats', payload);
    return data;
  },
  updateContrat: async (id, payload) => {
    const { data } = await apiClient.put(`/rh/contrats/${id}`, payload);
    return data;
  },
  removeContrat: async (id) => {
    const { data } = await apiClient.delete(`/rh/contrats/${id}`);
    return data;
  },

  listConges: async (params = {}) => {
    const { data } = await apiClient.get('/rh/conges', { params });
    return data;
  },
  createConge: async (payload) => {
    const { data } = await apiClient.post('/rh/conges', payload);
    return data;
  },
  updateConge: async (id, payload) => {
    const { data } = await apiClient.put(`/rh/conges/${id}`, payload);
    return data;
  },
  removeConge: async (id) => {
    const { data } = await apiClient.delete(`/rh/conges/${id}`);
    return data;
  },
  patchCongeStatut: async (id, statut) => {
    const { data } = await apiClient.patch(`/rh/conges/${id}/statut`, { statut });
    return data;
  },
};
