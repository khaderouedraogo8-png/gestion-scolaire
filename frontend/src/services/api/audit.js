import apiClient from './client';

export const auditApi = {
  list: async (params = {}) => {
    const { data } = await apiClient.get('/audit', { params });
    return data;
  },
};
