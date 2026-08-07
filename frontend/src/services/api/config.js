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

  listClasses: async (params = {}) => {
    const { data } = await apiClient.get('/etablissement/classes', { params });
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

  listNiveaux: async () => {
    const { data } = await apiClient.get('/etablissement/niveaux');
    return data;
  },

  createNiveau: async (payload) => {
    const { data } = await apiClient.post('/etablissement/niveaux', payload);
    return data;
  },
};
