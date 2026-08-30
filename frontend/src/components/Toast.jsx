import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';

const ToastContext = createContext(null);

let toastId = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const recentRef = useRef(new Map());

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (message, type = 'success', duration = 4000) => {
      const key = `${type}:${message}`;
      const now = Date.now();
      const last = recentRef.current.get(key);
      if (last && now - last < 2500) return null;

      recentRef.current.set(key, now);
      const id = ++toastId;
      setToasts((prev) => [...prev, { id, message, type }]);
      if (duration > 0) {
        setTimeout(() => removeToast(id), duration);
      }
      return id;
    },
    [removeToast]
  );

  const toast = useMemo(
    () => ({
      success: (msg) => addToast(msg, 'success'),
      error: (msg) => addToast(msg, 'error', 6000),
      info: (msg) => addToast(msg, 'info'),
      warning: (msg) => addToast(msg, 'warning'),
    }),
    [addToast]
  );

  const typeStyles = {
    success: 'border-feuille bg-feuille-clair text-feuille',
    error: 'border-brique bg-brique-clair text-brique',
    warning: 'border-ambre bg-ambre-clair text-ambre',
    info: 'border-or-cachet bg-or-cachet-clair text-or-cachet',
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`toast-enter flex min-w-[280px] max-w-md items-center gap-3 rounded-card border px-4 py-3 ${typeStyles[t.type] || typeStyles.info}`}
          >
            <span className="flex-1 text-sm font-medium">{t.message}</span>
            <button
              type="button"
              onClick={() => removeToast(t.id)}
              className="rounded p-1 hover:bg-black/5"
              aria-label="Fermer"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
