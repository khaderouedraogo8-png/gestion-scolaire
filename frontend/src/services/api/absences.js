import apiClient from './client';

export const absencesApi = {
  list: async (params = {}) => {
    const { data } = await apiClient.get('/absences', { params });
    return data;
  },

  create: async (payload) => {
    const { data } = await apiClient.post('/absences', payload);
    return data;
  },

  update: async (id, payload) => {
    const { data } = await apiClient.put(`/absences/${id}`, payload);
    return data;
  },

  justifier: async (id, payload) => {
    const { data } = await apiClient.put(`/absences/${id}`, {
      justifiee: true,
      motif: payload.motif,
    });
    return data;
  },

  listIncidents: async (params = {}) => {
    const { data } = await apiClient.get('/absences/discipline', { params });
    return data;
  },

  listDiscipline: async (params = {}) => {
    const { data } = await apiClient.get('/absences/discipline', { params });
    return data;
  },

  createIncident: async (payload) => {
    const { data } = await apiClient.post('/absences/discipline', payload);
    return data;
  },
};
