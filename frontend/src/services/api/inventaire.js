import apiClient from './client';

export const inventaireApi = {
  listArticles: async (params = {}) => {
    const { data } = await apiClient.get('/inventaire/articles', { params });
    return data;
  },
  getArticle: async (id) => {
    const { data } = await apiClient.get(`/inventaire/articles/${id}`);
    return data;
  },
  createArticle: async (payload) => {
    const { data } = await apiClient.post('/inventaire/articles', payload);
    return data;
  },
  updateArticle: async (id, payload) => {
    const { data } = await apiClient.put(`/inventaire/articles/${id}`, payload);
    return data;
  },
  removeArticle: async (id) => {
    const { data } = await apiClient.delete(`/inventaire/articles/${id}`);
    return data;
  },

  listMouvements: async (params = {}) => {
    const { data } = await apiClient.get('/inventaire/mouvements', { params });
    return data;
  },
  createMouvement: async (payload) => {
    const { data } = await apiClient.post('/inventaire/mouvements', payload);
    return data;
  },
  listAlertes: async () => {
    const { data } = await apiClient.get('/inventaire/alertes');
    return data;
  },
  inventaireAnnuelEcarts: async (payload) => {
    const { data } = await apiClient.post('/inventaire/inventaire-annuel/ecarts', payload);
    return data;
  },
};
