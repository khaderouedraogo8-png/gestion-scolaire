/**
 * Client API Rulesets de notation (Step 3).
 * Configuration uniquement — aucun calcul de moyenne côté client.
 */
import apiClient from './client';

export const gradingApi = {
  listEvaluationTypes: async (params = {}) => {
    const { data } = await apiClient.get('/evaluation-types', { params });
    return data;
  },

  createEvaluationType: async (payload) => {
    const { data } = await apiClient.post('/evaluation-types', payload);
    return data;
  },

  activateEvaluationType: async (id) => {
    const { data } = await apiClient.post(`/evaluation-types/${id}/activate`);
    return data;
  },

  deactivateEvaluationType: async (id) => {
    const { data } = await apiClient.post(`/evaluation-types/${id}/deactivate`);
    return data;
  },

  listRulesets: async (params = {}) => {
    const { data } = await apiClient.get('/grading-rulesets', { params });
    return data;
  },

  getRuleset: async (id) => {
    const { data } = await apiClient.get(`/grading-rulesets/${id}`);
    return data;
  },

  createRuleset: async (payload) => {
    const { data } = await apiClient.post('/grading-rulesets', payload);
    return data;
  },

  updateRuleset: async (id, payload) => {
    const { data } = await apiClient.patch(`/grading-rulesets/${id}`, payload);
    return data;
  },

  activateRuleset: async (id) => {
    const { data } = await apiClient.post(`/grading-rulesets/${id}/activate`);
    return data;
  },

  archiveRuleset: async (id) => {
    const { data } = await apiClient.post(`/grading-rulesets/${id}/archive`);
    return data;
  },

  addComponent: async (rulesetId, payload) => {
    const { data } = await apiClient.post(`/grading-rulesets/${rulesetId}/components`, payload);
    return data;
  },

  updateComponent: async (rulesetId, componentId, payload) => {
    const { data } = await apiClient.patch(
      `/grading-rulesets/${rulesetId}/components/${componentId}`,
      payload
    );
    return data;
  },

  deleteComponent: async (rulesetId, componentId) => {
    const { data } = await apiClient.delete(
      `/grading-rulesets/${rulesetId}/components/${componentId}`
    );
    return data;
  },

  resolve: async (payload) => {
    const { data } = await apiClient.post('/grading-rulesets/resolve', payload);
    return data;
  },
};

export default gradingApi;
