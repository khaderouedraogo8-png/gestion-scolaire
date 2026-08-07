import apiClient from './client';

export const dashboardApi = {
  getStats: async (params = {}) => {
    const { data } = await apiClient.get('/dashboard/stats', { params });
    return data;
  },
};
