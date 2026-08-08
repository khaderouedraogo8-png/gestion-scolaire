import apiClient from './client';

const openPdf = (url, params = {}) => {
  const search = new URLSearchParams(params).toString();
  return apiClient.get(`${url}?${search}`, { responseType: 'blob' });
};

export const pedagogieApi = {
  listProgrammeDevoirs: async (params) => {
    const { data } = await apiClient.get('/pedagogie/programme-devoirs', { params });
    return data;
  },

  saveProgrammeDevoir: async (payload) => {
    const { data } = await apiClient.post('/pedagogie/programme-devoirs', payload);
    return data;
  },

  updateProgrammeDevoir: async (id, payload) => {
    const { data } = await apiClient.put(`/pedagogie/programme-devoirs/${id}`, payload);
    return data;
  },

  deleteProgrammeDevoir: async (id) => {
    const { data } = await apiClient.delete(`/pedagogie/programme-devoirs/${id}`);
    return data;
  },

  pdfProgrammeDevoirs: (params) => openPdf('/pedagogie/pdf/programme-devoirs', params),
  pdfCalendrierCompositions: (params) => openPdf('/pedagogie/pdf/calendrier-compositions', params),
  pdfListeEleves: (params) => openPdf('/pedagogie/pdf/liste-eleves', params),
  pdfFicheCorrection: (params) => openPdf('/pedagogie/pdf/fiche-correction', params),
  pdfFicheAppel: (params) => openPdf('/pedagogie/pdf/fiche-appel', params),
  pdfFicheScolarite: (params) => openPdf('/pedagogie/pdf/fiche-scolarite', params),
  pdfProgrammeTrimestriel: (params) => openPdf('/pedagogie/pdf/programme-trimestriel', params),

  getChargeTravail: async (params) => {
    const { data } = await apiClient.get('/pedagogie/charge-travail', { params });
    return data;
  },

  listSeances: async (params) => {
    const { data } = await apiClient.get('/pedagogie/seances', { params });
    return data;
  },

  saveSeance: async (payload) => {
    const { data } = await apiClient.post('/pedagogie/seances', payload);
    return data;
  },

  deleteSeance: async (id) => {
    const { data } = await apiClient.delete(`/pedagogie/seances/${id}`);
    return data;
  },
};

export const downloadBlob = (blob, filename) => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  window.URL.revokeObjectURL(url);
};
