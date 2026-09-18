import apiClient from './client';

export const elearningApi = {
  listDevoirs: async (params = {}) => {
    const { data } = await apiClient.get('/elearning/devoirs', { params });
    return data;
  },
  getDevoir: async (id) => {
    const { data } = await apiClient.get(`/elearning/devoirs/${id}`);
    return data;
  },
  createDevoir: async (payload) => {
    const { data } = await apiClient.post('/elearning/devoirs', payload);
    return data;
  },
  updateDevoir: async (id, payload) => {
    const { data } = await apiClient.put(`/elearning/devoirs/${id}`, payload);
    return data;
  },
  removeDevoir: async (id) => {
    const { data } = await apiClient.delete(`/elearning/devoirs/${id}`);
    return data;
  },
  devoirStats: async (id) => {
    const { data } = await apiClient.get(`/elearning/devoirs/${id}/stats`);
    return data;
  },

  listRemises: async (params = {}) => {
    const { data } = await apiClient.get('/elearning/remises', { params });
    return data;
  },
  submitRemise: async (payload) => {
    const { data } = await apiClient.post('/elearning/remises', payload);
    return data;
  },
  noteRemise: async (id, payload) => {
    const { data } = await apiClient.put(`/elearning/remises/${id}`, payload);
    return data;
  },

  listQuiz: async (params = {}) => {
    const { data } = await apiClient.get('/elearning/quiz', { params });
    return data;
  },
  getQuiz: async (id) => {
    const { data } = await apiClient.get(`/elearning/quiz/${id}`);
    return data;
  },
  createQuiz: async (payload) => {
    const { data } = await apiClient.post('/elearning/quiz', payload);
    return data;
  },
  updateQuiz: async (id, payload) => {
    const { data } = await apiClient.put(`/elearning/quiz/${id}`, payload);
    return data;
  },
  removeQuiz: async (id) => {
    const { data } = await apiClient.delete(`/elearning/quiz/${id}`);
    return data;
  },
  passerQuiz: async (id, payload) => {
    const { data } = await apiClient.post(`/elearning/quiz/${id}/passer`, payload);
    return data;
  },
  listTentatives: async (id, params = {}) => {
    const { data } = await apiClient.get(`/elearning/quiz/${id}/tentatives`, { params });
    return data;
  },

  listRessources: async (params = {}) => {
    const { data } = await apiClient.get('/elearning/ressources', { params });
    return data;
  },
  createRessource: async (payload) => {
    const { data } = await apiClient.post('/elearning/ressources', payload);
    return data;
  },
  updateRessource: async (id, payload) => {
    const { data } = await apiClient.put(`/elearning/ressources/${id}`, payload);
    return data;
  },
  removeRessource: async (id) => {
    const { data } = await apiClient.delete(`/elearning/ressources/${id}`);
    return data;
  },

  progression: async (params = {}) => {
    const { data } = await apiClient.get('/elearning/progression', { params });
    return data;
  },
};
