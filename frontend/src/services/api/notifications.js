import apiClient from './client';

export const notificationsApi = {
  list: async (params = {}) => {
    const { data } = await apiClient.get('/notifications', { params });
    return data;
  },

  create: async (payload) => {
    const { data } = await apiClient.post('/notifications/', payload);
    return data;
  },

  send: async (payload) => {
    const { data } = await apiClient.post('/notifications/', payload);
    return data;
  },

  traiterFile: async () => {
    const { data } = await apiClient.post('/notifications/traiter');
    return data;
  },

  retry: async (id) => {
    const { data } = await apiClient.post(`/notifications/${id}/retry`);
    return data;
  },
};
