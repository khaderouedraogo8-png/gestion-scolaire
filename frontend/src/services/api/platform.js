import apiClient from './client';

export const platformApi = {
  listSchools: async (params = {}) => {
    const { data } = await apiClient.get('/platform/schools', { params });
    return data;
  },

  getSchool: async (id) => {
    const { data } = await apiClient.get(`/platform/schools/${id}`);
    return data;
  },

  updateSchool: async (id, payload) => {
    const { data } = await apiClient.patch(`/platform/schools/${id}`, payload);
    return data;
  },

  activateSchool: async (id) => {
    const { data } = await apiClient.post(`/platform/schools/${id}/activate`);
    return data;
  },

  deactivateSchool: async (id) => {
    const { data } = await apiClient.post(`/platform/schools/${id}/deactivate`);
    return data;
  },

  onboardSchool: async (payload) => {
    const { data } = await apiClient.post('/platform/schools/onboard', payload);
    return data;
  },

  listSchoolUsers: async (id, params = {}) => {
    const { data } = await apiClient.get(`/platform/schools/${id}/users`, { params });
    return data;
  },

  createSchoolAdmin: async (id, payload) => {
    const { data } = await apiClient.post(`/platform/schools/${id}/admins`, payload);
    return data;
  },

  enterSchoolContext: async (schoolId) => {
    const { data } = await apiClient.put('/platform/context/school', { school_id: schoolId });
    return data;
  },

  exitSchoolContext: async () => {
    const { data } = await apiClient.delete('/platform/context/school');
    return data;
  },
};
