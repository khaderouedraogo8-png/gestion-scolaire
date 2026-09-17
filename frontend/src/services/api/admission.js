import apiClient from './client';

export const admissionApi = {
  list: async (params = {}) => {
    const { data } = await apiClient.get('/admission/', { params });
    return data;
  },

  get: async (id) => {
    const { data } = await apiClient.get(`/admission/${id}`);
    return data;
  },

  create: async (payload) => {
    const { data } = await apiClient.post('/admission/', payload);
    return data;
  },

  update: async (id, payload) => {
    const { data } = await apiClient.put(`/admission/${id}`, payload);
    return data;
  },

  remove: async (id) => {
    const { data } = await apiClient.delete(`/admission/${id}`);
    return data;
  },

  patchStatut: async (id, statut) => {
    const { data } = await apiClient.patch(`/admission/${id}/statut`, { statut });
    return data;
  },

  convertToEleve: async (id, payload) => {
    const { data } = await apiClient.post(`/admission/${id}/convert-to-eleve`, payload);
    return data;
  },
};
