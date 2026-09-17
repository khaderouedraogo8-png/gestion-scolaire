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

  listRemises: async (params = {}) => {
    const { data } = await apiClient.get('/elearning/remises', { params });
    return data;
  },
  createRemise: async (payload) => {
    const { data } = await apiClient.post('/elearning/remises', payload);
    return data;
  },
  updateRemise: async (id, payload) => {
    const { data } = await apiClient.put(`/elearning/remises/${id}`, payload);
    return data;
  },

  listQuiz: async (params = {}) => {
    const { data } = await apiClient.get('/elearning/quiz', { params });
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
};
