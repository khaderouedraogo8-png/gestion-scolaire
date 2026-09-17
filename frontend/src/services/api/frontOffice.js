import apiClient from './client';

export const frontOfficeApi = {
  listVisiteurs: async (params = {}) => {
    const { data } = await apiClient.get('/front-office/visiteurs', { params });
    return data;
  },
  createVisiteur: async (payload) => {
    const { data } = await apiClient.post('/front-office/visiteurs', payload);
    return data;
  },
  sortieVisiteur: async (id) => {
    const { data } = await apiClient.post(`/front-office/visiteurs/${id}/sortie`);
    return data;
  },

  listSorties: async (params = {}) => {
    const { data } = await apiClient.get('/front-office/sorties', { params });
    return data;
  },
  createSortie: async (payload) => {
    const { data } = await apiClient.post('/front-office/sorties', payload);
    return data;
  },
  validateSortie: async (id, payload) => {
    const { data } = await apiClient.patch(`/front-office/sorties/${id}/validate`, payload);
    return data;
  },
  retourSortie: async (id) => {
    const { data } = await apiClient.post(`/front-office/sorties/${id}/retour`);
    return data;
  },
};
