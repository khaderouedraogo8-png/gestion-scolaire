import apiClient from './client';

export const vieScolaireApi = {
  listCantineAbonnements: async (params = {}) => {
    const { data } = await apiClient.get('/vie-scolaire/cantine/abonnements', { params });
    return data;
  },
  createCantineAbonnement: async (payload) => {
    const { data } = await apiClient.post('/vie-scolaire/cantine/abonnements', payload);
    return data;
  },
  listCantinePresences: async (params = {}) => {
    const { data } = await apiClient.get('/vie-scolaire/cantine/presences', { params });
    return data;
  },
  createCantinePresence: async (payload) => {
    const { data } = await apiClient.post('/vie-scolaire/cantine/presences', payload);
    return data;
  },

  listTransportItineraires: async () => {
    const { data } = await apiClient.get('/vie-scolaire/transport/itineraires');
    return data;
  },
  createTransportItineraire: async (payload) => {
    const { data } = await apiClient.post('/vie-scolaire/transport/itineraires', payload);
    return data;
  },
  listTransportArrets: async (params = {}) => {
    const { data } = await apiClient.get('/vie-scolaire/transport/arrets', { params });
    return data;
  },
  createTransportArret: async (payload) => {
    const { data } = await apiClient.post('/vie-scolaire/transport/arrets', payload);
    return data;
  },
  listTransportEleves: async () => {
    const { data } = await apiClient.get('/vie-scolaire/transport/eleves');
    return data;
  },
  createTransportEleve: async (payload) => {
    const { data } = await apiClient.post('/vie-scolaire/transport/eleves', payload);
    return data;
  },

  listInternatChambres: async () => {
    const { data } = await apiClient.get('/vie-scolaire/internat/chambres');
    return data;
  },
  createInternatChambre: async (payload) => {
    const { data } = await apiClient.post('/vie-scolaire/internat/chambres', payload);
    return data;
  },
  listInternatAffectations: async () => {
    const { data } = await apiClient.get('/vie-scolaire/internat/affectations');
    return data;
  },
  createInternatAffectation: async (payload) => {
    const { data } = await apiClient.post('/vie-scolaire/internat/affectations', payload);
    return data;
  },

  listInfirmerieSoins: async (params = {}) => {
    const { data } = await apiClient.get('/vie-scolaire/infirmiere/soins', { params });
    return data;
  },
  createInfirmerieSoin: async (payload) => {
    const { data } = await apiClient.post('/vie-scolaire/infirmiere/soins', payload);
    return data;
  },

  listBibliothequeLivres: async () => {
    const { data } = await apiClient.get('/vie-scolaire/bibliotheque/livres');
    return data;
  },
  createBibliothequeLivre: async (payload) => {
    const { data } = await apiClient.post('/vie-scolaire/bibliotheque/livres', payload);
    return data;
  },
  listBibliothequePrets: async () => {
    const { data } = await apiClient.get('/vie-scolaire/bibliotheque/prets');
    return data;
  },
  createBibliothequePret: async (payload) => {
    const { data } = await apiClient.post('/vie-scolaire/bibliotheque/prets', payload);
    return data;
  },
  retourBibliothequePret: async (id) => {
    const { data } = await apiClient.post(`/vie-scolaire/bibliotheque/prets/${id}/retour`);
    return data;
  },
};
