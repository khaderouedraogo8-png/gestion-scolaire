import apiClient from './client';

export const authApi = {
  login: async (email, password) => {
    const { data } = await apiClient.post('/login', { email, password });
    return data;
  },

  logout: async () => {
    const { data } = await apiClient.post('/logout');
    return data;
  },

  refresh: async () => {
    const { data } = await apiClient.post('/refresh');
    return data;
  },

  changePassword: async (ancien_mot_de_passe, nouveau_mot_de_passe) => {
    const { data } = await apiClient.post('/change-password', {
      ancien_mot_de_passe,
      nouveau_mot_de_passe,
    });
    return data;
  },

  me: async () => {
    const { data } = await apiClient.get('/me');
    return data;
  },
};
