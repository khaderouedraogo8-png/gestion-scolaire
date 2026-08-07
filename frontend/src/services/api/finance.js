import apiClient from './client';

export const financeApi = {
  listFrais: async (params = {}) => {
    const { data } = await apiClient.get('/finance/frais', { params });
    return data;
  },

  createFrais: async (payload) => {
    const { data } = await apiClient.post('/finance/frais', payload);
    return data;
  },

  getEcheances: async (params = {}) => {
    const { data } = await apiClient.get('/finance/echeances', { params });
    return data;
  },

  createEcheance: async (payload) => {
    const { data } = await apiClient.post('/finance/echeances', payload);
    return data;
  },

  encaisser: async (payload) => {
    const { data } = await apiClient.post('/finance/paiements', payload);
    return data;
  },

  listPaiements: async (params = {}) => {
    const { data } = await apiClient.get('/finance/paiements', { params });
    return data;
  },

  annulerPaiement: async (id, motif) => {
    const { data } = await apiClient.post(`/finance/paiements/${id}/annuler`, {
      motif_annulation: motif,
    });
    return data;
  },

  listArrieres: async (params = {}) => {
    const { data } = await apiClient.get('/finance/arrieres', { params });
    return data;
  },

  getRecuPdf: async (id) => {
    const response = await apiClient.get(`/finance/paiements/${id}/recu`, { responseType: 'blob' });
    return response.data;
  },

  exportArrieresExcel: async (idAnnee) => {
    const response = await apiClient.get('/finance/arrieres/export', {
      params: { id_annee: idAnnee },
      responseType: 'blob',
    });
    return response.data;
  },

  relancerArrieres: async (idAnnee, options = {}) => {
    const { data } = await apiClient.post('/finance/arrieres/relancer', {
      id_annee: idAnnee,
      canal: options.canal || 'email',
      auto_envoyer: options.autoEnvoyer !== false,
    });
    return data;
  },
};
