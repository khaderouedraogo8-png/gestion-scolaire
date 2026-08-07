import apiClient from './client';

export const documentsApi = {
  list: async (params = {}) => {
    const { data } = await apiClient.get('/documents', { params });
    return data;
  },

  genererCarteScolaire: async (payload) => {
    const { data } = await apiClient.post('/documents/carte-scolaire', payload);
    return data;
  },

  genererCarte: async (payload) => {
    const { data } = await apiClient.post('/documents/carte-scolaire', payload);
    return data;
  },

  genererAttestation: async (payload) => {
    const { data } = await apiClient.post('/documents/attestation', payload);
    return data;
  },

  genererCertificat: async (payload) => {
    const { data } = await apiClient.post('/documents/certificat', payload);
    return data;
  },

  genererDiplome: async (payload) => {
    const { data } = await apiClient.post('/documents/diplome', payload);
    return data;
  },

  verifierQr: async (qrData) => {
    const { data } = await apiClient.post('/documents/verifier-qr', { qr_data: qrData });
    return data;
  },

  download: async (id) => {
    const response = await apiClient.get(`/documents/${id}/pdf`, { responseType: 'blob' });
    return response.data;
  },
};
