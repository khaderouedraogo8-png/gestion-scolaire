import { create } from 'zustand';
import { authApi } from '../services/api/auth';

let accessToken = null;
let initializePromise = null;

export function getAccessToken() {
  return accessToken;
}

export function setAccessToken(token) {
  accessToken = token;
}

export const useAuthStore = create((set, get) => ({
  user: null,
  isAuthenticated: false,
  isInitializing: true,
  isLoading: false,
  error: null,

  initialize: async () => {
    if (initializePromise) return initializePromise;

    initializePromise = (async () => {
      try {
        const data = await authApi.refresh();
        setAccessToken(data.access_token);
        const me = await authApi.me();
        set({
          user: me,
          isAuthenticated: true,
          isInitializing: false,
          error: null,
        });
      } catch {
        setAccessToken(null);
        set({
          user: null,
          isAuthenticated: false,
          isInitializing: false,
          error: null,
        });
      }
    })();

    return initializePromise;
  },

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const data = await authApi.login(email, password);
      setAccessToken(data.access_token);
      set({
        user: data.user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
      return data;
    } catch (err) {
      const message =
        err.response?.data?.message || 'Identifiants incorrects. Veuillez réessayer.';
      set({ isLoading: false, error: message });
      throw err;
    }
  },

  logout: async () => {
    initializePromise = null;
    try {
      await authApi.logout();
    } catch {
      /* ignore logout errors */
    } finally {
      setAccessToken(null);
      set({ user: null, isAuthenticated: false, error: null });
    }
  },

  refresh: async () => {
    const data = await authApi.refresh();
    setAccessToken(data.access_token);
    const me = await authApi.me();
    set({ user: me, isAuthenticated: true });
    return { ...data, user: me };
  },

  changePassword: async (currentPassword, newPassword) => {
    set({ isLoading: true, error: null });
    try {
      await authApi.changePassword(currentPassword, newPassword);
      const user = get().user;
      if (user) {
        set({ user: { ...user, doit_changer_mdp: false }, isLoading: false });
      } else {
        set({ isLoading: false });
      }
    } catch (err) {
      const message =
        err.response?.data?.message || 'Erreur lors du changement de mot de passe.';
      set({ isLoading: false, error: message });
      throw err;
    }
  },

  clearError: () => set({ error: null }),

  hasRole: (...roles) => {
    const { user } = get();
    if (!user?.role) return false;
    return roles.includes(user.role);
  },

  hasAnyRole: (roles) => {
    const { user } = get();
    if (!user?.role) return false;
    return roles.some((r) => r === user.role);
  },
}));
