import apiClient from './client';

export const dashboardApi = {
  getStats: async (params = {}) => {
    const { data } = await apiClient.get('/dashboard/stats', { params });
    return data;
  },

  getAbsencesParClasse: async (params = {}) => {
    const { data } = await apiClient.get('/dashboard/absences-par-classe', { params });
    return data;
  },

  getEnseignant: async (params = {}) => {
    const { data } = await apiClient.get('/dashboard/enseignant', { params });
    return data;
  },

  getParentEvolution: async (params = {}) => {
    const { data } = await apiClient.get('/dashboard/parent-evolution', { params });
    return data;
  },

  getComptable: async (params = {}) => {
    const { data } = await apiClient.get('/dashboard/comptable', { params });
    return data;
  },

  getSurveillant: async (params = {}) => {
    const { data } = await apiClient.get('/dashboard/surveillant', { params });
    return data;
  },

  getSecretaire: async (params = {}) => {
    const { data } = await apiClient.get('/dashboard/secretaire', { params });
    return data;
  },
};
