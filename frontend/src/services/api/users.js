import apiClient from './client';

export const usersApi = {
  list: async () => {
    const { data } = await apiClient.get('/users');
    return data;
  },

  create: async (payload) => {
    const { data } = await apiClient.post('/users', payload);
    return data;
  },

  update: async (id, payload) => {
    const { data } = await apiClient.patch(`/users/${id}`, payload);
    return data;
  },

  resetPassword: async (id) => {
    const { data } = await apiClient.post(`/users/${id}/reset-password`);
    return data;
  },

  forgotPassword: async (email) => {
    const { data } = await apiClient.post('/users/forgot-password', { email });
    return data;
  },

  resetPasswordWithToken: async (token, nouveau_mot_de_passe) => {
    const { data } = await apiClient.post('/users/reset-password', { token, nouveau_mot_de_passe });
    return data;
  },
};
