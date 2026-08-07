import apiClient from './client';

export const elevesApi = {
  list: async (params = {}) => {
    const { data } = await apiClient.get('/eleves', { params });
    return data;
  },

  get: async (id) => {
    const { data } = await apiClient.get(`/eleves/${id}`);
    return data;
  },

  create: async (payload) => {
    const { data } = await apiClient.post('/eleves', payload);
    return data;
  },

  update: async (id, payload) => {
    const { data } = await apiClient.put(`/eleves/${id}`, payload);
    return data;
  },

  inscrire: async (idEleve, payload) => {
    const { data } = await apiClient.post(`/eleves/${idEleve}/inscriptions`, payload);
    return data;
  },

  getInscriptions: async (id) => {
    const { data } = await apiClient.get(`/eleves/${id}/inscriptions`);
    return data;
  },

  updateInscriptionStatut: async (idInscription, statut) => {
    const { data } = await apiClient.patch(`/eleves/inscriptions/${idInscription}/statut`, {
      statut,
    });
    return data;
  },

  uploadDocument: async (id, file, type = 'autre') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', type);
    const { data } = await apiClient.post(`/eleves/${id}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  uploadPhoto: async (id, file) => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await apiClient.post(`/eleves/${id}/photo`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  getPhotoBlob: async (id) => {
    const { data } = await apiClient.get(`/eleves/${id}/photo`, { responseType: 'blob' });
    return data;
  },
};
