import apiClient from './client';

export const schoolsApi = {
  getCurrent: async () => {
    const { data } = await apiClient.get('/schools/current');
    return data;
  },
};
