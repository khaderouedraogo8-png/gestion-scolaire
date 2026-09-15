import apiClient from './client';

export const configApi = {
  getEtablissement: async () => {
    const { data } = await apiClient.get('/etablissement');
    return data;
  },

  updateEtablissement: async (payload) => {
    const { data } = await apiClient.put('/etablissement', payload);
    return data;
  },

  createEtablissement: async (payload) => {
    const { data } = await apiClient.post('/etablissement', payload);
    return data;
  },

  listAnnees: async () => {
    const { data } = await apiClient.get('/etablissement/annees');
    return data;
  },

  createAnnee: async (payload) => {
    const { data } = await apiClient.post('/etablissement/annees', payload);
    return data;
  },

  updateAnnee: async (id, payload) => {
    const { data } = await apiClient.put(`/etablissement/annees/${id}`, payload);
    return data;
  },

  setAnneeActive: async (id, annee) => {
    const { data } = await apiClient.put(`/etablissement/annees/${id}`, {
      libelle: annee.libelle,
      date_debut: annee.date_debut,
      date_fin: annee.date_fin,
      est_active: true,
    });
    return data;
  },

  listTrimestres: async (idAnnee) => {
    const { data } = await apiClient.get('/etablissement/trimestres', {
      params: { id_annee: idAnnee },
    });
    return data;
  },

  createTrimestre: async (payload) => {
    const { data } = await apiClient.post('/etablissement/trimestres', payload);
    return data;
  },

  updateTrimestre: async (id, payload) => {
    const { data } = await apiClient.put(`/etablissement/trimestres/${id}`, payload);
    return data;
  },

  deleteTrimestre: async (id) => {
    const { data } = await apiClient.delete(`/etablissement/trimestres/${id}`);
    return data;
  },

  // --- Programmes (PR11) ---
  listPrograms: async (params = {}) => {
    const { data } = await apiClient.get('/etablissement/programs', { params });
    return data;
  },

  getProgram: async (id) => {
    const { data } = await apiClient.get(`/etablissement/programs/${id}`);
    return data;
  },

  createProgram: async (payload) => {
    const { data } = await apiClient.post('/etablissement/programs', payload);
    return data;
  },

  updateProgram: async (id, payload) => {
    const { data } = await apiClient.patch(`/etablissement/programs/${id}`, payload);
    return data;
  },

  deactivateProgram: async (id) => {
    const { data } = await apiClient.post(`/etablissement/programs/${id}/deactivate`);
    return data;
  },

  // --- Périodes (canonique, même service que /trimestres) ---
  listPeriodes: async (params = {}) => {
    const { data } = await apiClient.get('/etablissement/periodes', { params });
    return data;
  },

  getPeriode: async (id) => {
    const { data } = await apiClient.get(`/etablissement/periodes/${id}`);
    return data;
  },

  createPeriode: async (payload) => {
    const { data } = await apiClient.post('/etablissement/periodes', payload);
    return data;
  },

  updatePeriode: async (id, payload) => {
    const { data } = await apiClient.patch(`/etablissement/periodes/${id}`, payload);
    return data;
  },

  deactivatePeriode: async (id) => {
    const { data } = await apiClient.post(`/etablissement/periodes/${id}/deactivate`);
    return data;
  },

  listClasses: async (params = {}) => {
    const { data } = await apiClient.get('/etablissement/classes', { params });
    return data;
  },

  listClassesNav: async (params = {}) => {
    const { data } = await apiClient.get('/etablissement/classes', {
      params: { enriched: true, ...params },
    });
    return data;
  },

  createClasse: async (payload) => {
    const { data } = await apiClient.post('/etablissement/classes', payload);
    return data;
  },

  updateClasse: async (id, payload) => {
    const { data } = await apiClient.put(`/etablissement/classes/${id}`, payload);
    return data;
  },

  listNiveaux: async (params = {}) => {
    const { data } = await apiClient.get('/etablissement/niveaux', { params });
    return data;
  },

  createNiveau: async (payload) => {
    const { data } = await apiClient.post('/etablissement/niveaux', payload);
    return data;
  },

  updateNiveau: async (id, payload) => {
    const { data } = await apiClient.put(`/etablissement/niveaux/${id}`, payload);
    return data;
  },

  listCalendrier: async (idAnnee) => {
    const { data } = await apiClient.get('/etablissement/calendrier', {
      params: { id_annee: idAnnee },
    });
    return data;
  },

  createEvenementCalendrier: async (payload) => {
    const { data } = await apiClient.post('/etablissement/calendrier', payload);
    return data;
  },

  updateEvenementCalendrier: async (id, payload) => {
    const { data } = await apiClient.put(`/etablissement/calendrier/${id}`, payload);
    return data;
  },

  deleteEvenementCalendrier: async (id) => {
    const { data } = await apiClient.delete(`/etablissement/calendrier/${id}`);
    return data;
  },
};
