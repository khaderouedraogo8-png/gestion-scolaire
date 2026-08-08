import { useEffect } from 'react';
import { useRoutes, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import { ToastProvider } from './components/Toast';
import { routes } from './routes';

export default function App() {
  const element = useRoutes(routes);
  const initialize = useAuthStore((s) => s.initialize);
  const isInitializing = useAuthStore((s) => s.isInitializing);

  useEffect(() => {
    initialize();
  }, [initialize]);

  if (isInitializing) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-craie">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-or-cachet-clair border-t-or-cachet" />
          <p className="mt-4 text-sm text-texte-secondaire">Chargement...</p>
        </div>
      </div>
    );
  }

  if (!element) {
    return <Navigate to="/dashboard" replace />;
  }

  return <ToastProvider>{element}</ToastProvider>;
}

export function RedirectToDashboard() {
  return <Navigate to="/dashboard" replace />;
}
