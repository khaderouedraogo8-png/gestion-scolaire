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

  listPlans: async () => {
    const { data } = await apiClient.get('/platform/billing/plans');
    return data;
  },
  billingOps: async () => {
    const { data } = await apiClient.get('/platform/billing/ops');
    return data;
  },
  listSubscriptions: async (params = {}) => {
    const { data } = await apiClient.get('/platform/billing/subscriptions', { params });
    return data;
  },
  assignPlan: async (schoolId, payload) => {
    const { data } = await apiClient.put(`/platform/billing/schools/${schoolId}/subscription`, payload);
    return data;
  },
  listInvoices: async (schoolId) => {
    const { data } = await apiClient.get(`/platform/billing/schools/${schoolId}/invoices`);
    return data;
  },
  issueInvoice: async (schoolId, payload = {}) => {
    const { data } = await apiClient.post(`/platform/billing/schools/${schoolId}/invoices`, payload);
    return data;
  },
  payInvoice: async (invoiceId, payload = {}) => {
    const { data } = await apiClient.post(`/platform/billing/invoices/${invoiceId}/pay`, payload);
    return data;
  },
  expireSubscriptions: async () => {
    const { data } = await apiClient.post('/platform/billing/expire');
    return data;
  },
};
