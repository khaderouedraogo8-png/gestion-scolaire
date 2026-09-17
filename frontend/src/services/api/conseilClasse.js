import apiClient from './client';

export const conseilClasseApi = {
  listSessions: async (params = {}) => {
    const { data } = await apiClient.get('/conseil-classe/sessions', { params });
    return data;
  },

  getSession: async (id) => {
    const { data } = await apiClient.get(`/conseil-classe/sessions/${id}`);
    return data;
  },

  createSession: async (payload) => {
    const { data } = await apiClient.post('/conseil-classe/sessions', payload);
    return data;
  },

  updateSession: async (id, payload) => {
    const { data } = await apiClient.put(`/conseil-classe/sessions/${id}`, payload);
    return data;
  },

  removeSession: async (id) => {
    const { data } = await apiClient.delete(`/conseil-classe/sessions/${id}`);
    return data;
  },

  listDecisions: async (params = {}) => {
    const { data } = await apiClient.get('/conseil-classe/decisions', { params });
    return data;
  },

  createDecision: async (payload) => {
    const { data } = await apiClient.post('/conseil-classe/decisions', payload);
    return data;
  },

  updateDecision: async (id, payload) => {
    const { data } = await apiClient.put(`/conseil-classe/decisions/${id}`, payload);
    return data;
  },

  removeDecision: async (id) => {
    const { data } = await apiClient.delete(`/conseil-classe/decisions/${id}`);
    return data;
  },
};
