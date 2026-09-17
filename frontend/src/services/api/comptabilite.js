import apiClient from './client';

export const comptabiliteApi = {
  listEcritures: async (params = {}) => {
    const { data } = await apiClient.get('/comptabilite/ecritures', { params });
    return data;
  },
  getEcriture: async (id) => {
    const { data } = await apiClient.get(`/comptabilite/ecritures/${id}`);
    return data;
  },
  createEcriture: async (payload) => {
    const { data } = await apiClient.post('/comptabilite/ecritures', payload);
    return data;
  },
  updateEcriture: async (id, payload) => {
    const { data } = await apiClient.put(`/comptabilite/ecritures/${id}`, payload);
    return data;
  },
  removeEcriture: async (id) => {
    const { data } = await apiClient.delete(`/comptabilite/ecritures/${id}`);
    return data;
  },

  getBalance: async (params = {}) => {
    const { data } = await apiClient.get('/comptabilite/etats/balance', { params });
    return data;
  },
  getBilan: async (params = {}) => {
    const { data } = await apiClient.get('/comptabilite/etats/bilan', { params });
    return data;
  },

  listPaiePeriodes: async () => {
    const { data } = await apiClient.get('/comptabilite/paie/periodes');
    return data;
  },
  createPaiePeriode: async (payload) => {
    const { data } = await apiClient.post('/comptabilite/paie/periodes', payload);
    return data;
  },
  cloturerPaiePeriode: async (id) => {
    const { data } = await apiClient.post(`/comptabilite/paie/periodes/${id}/cloturer`);
    return data;
  },
  listPaieLignes: async (params = {}) => {
    const { data } = await apiClient.get('/comptabilite/paie/lignes', { params });
    return data;
  },
  createPaieLigne: async (payload) => {
    const { data } = await apiClient.post('/comptabilite/paie/lignes', payload);
    return data;
  },
};
