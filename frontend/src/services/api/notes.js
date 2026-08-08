import apiClient from './client';

export const notesApi = {
  listMatieres: async () => {
    const { data } = await apiClient.get('/notes/matieres');
    return data;
  },

  createMatiere: async (payload) => {
    const { data } = await apiClient.post('/notes/matieres', payload);
    return data;
  },

  listEvaluations: async (params = {}) => {
    const { data } = await apiClient.get('/notes/evaluations', { params });
    return data;
  },

  getEvaluation: async (id) => {
    const { data } = await apiClient.get(`/notes/evaluations/${id}`);
    return data;
  },

  createEvaluation: async (payload) => {
    const { data } = await apiClient.post('/notes/evaluations', payload);
    return data;
  },

  getNotesGrid: async (evaluationId) => {
    const { data } = await apiClient.get(`/notes/evaluations/${evaluationId}/notes`);
    return data;
  },

  saveNotes: async (evaluationId, notes) => {
    const { data } = await apiClient.post(`/notes/evaluations/${evaluationId}/notes`, {
      notes: notes.map((n) => ({
        id_eleve: n.id_eleve,
        valeur_note: n.absent ? null : n.valeur_note != null ? Number(n.valeur_note) : null,
        absent: Boolean(n.absent),
        appreciation: n.appreciation || null,
      })),
    });
    return data;
  },

  listBulletins: async (params = {}) => {
    const { data } = await apiClient.get('/notes/bulletins', { params });
    return data;
  },

  genererBulletinsClasse: async (payload) => {
    const { data } = await apiClient.post('/notes/bulletins/generer', payload);
    return data;
  },

  genererBulletin: async (payload) => {
    const { data } = await apiClient.post('/notes/bulletins/generer', payload);
    return data;
  },

  validerBulletin: async (id) => {
    const { data } = await apiClient.post(`/notes/bulletins/${id}/valider`);
    return data;
  },

  publierBulletin: async (id) => {
    const { data } = await apiClient.post(`/notes/bulletins/${id}/publier`);
    return data;
  },

  getBulletinPdf: async (id) => {
    const response = await apiClient.get(`/notes/bulletins/${id}/pdf`, { responseType: 'blob' });
    return response.data;
  },

  listCoefficients: async (params = {}) => {
    const { data } = await apiClient.get('/notes/coefficients', { params });
    return data;
  },

  saveCoefficient: async (payload) => {
    const { data } = await apiClient.post('/notes/coefficients', payload);
    return data;
  },

  deleteCoefficient: async (id) => {
    const { data } = await apiClient.delete(`/notes/coefficients/${id}`);
    return data;
  },

  updateMatiere: async (id, payload) => {
    const { data } = await apiClient.put(`/notes/matieres/${id}`, payload);
    return data;
  },

  deleteMatiere: async (id) => {
    const { data } = await apiClient.delete(`/notes/matieres/${id}`);
    return data;
  },

  updateBulletinAppreciation: async (id, appreciation_generale) => {
    const { data } = await apiClient.patch(`/notes/bulletins/${id}`, { appreciation_generale });
    return data;
  },

  publierEvaluation: async (id) => {
    const { data } = await apiClient.post(`/notes/evaluations/${id}/publier`);
    return data;
  },

  cloturerEvaluation: async (id) => {
    const { data } = await apiClient.post(`/notes/evaluations/${id}/cloturer`);
    return data;
  },

  rouvrirEvaluation: async (id) => {
    const { data } = await apiClient.post(`/notes/evaluations/${id}/rouvrir`);
    return data;
  },
};
