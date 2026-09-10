import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import { X } from 'lucide-react';

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
    success: 'border-feuille/40 bg-feuille-clair text-feuille',
    error: 'border-brique/40 bg-brique-clair text-brique',
    warning: 'border-ambre/40 bg-ambre-clair text-ambre',
    info: 'border-or-cachet/40 bg-or-cachet-clair text-or-cachet',
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="fixed bottom-5 right-5 z-[100] flex flex-col gap-2.5">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`toast-enter flex min-w-[280px] max-w-md items-center gap-3 rounded-card border px-4 py-3 shadow-soft ${typeStyles[t.type] || typeStyles.info}`}
          >
            <span className="flex-1 text-sm font-medium leading-snug">{t.message}</span>
            <button
              type="button"
              onClick={() => removeToast(t.id)}
              className="rounded-input p-1 opacity-70 transition-opacity hover:bg-black/5 hover:opacity-100"
              aria-label="Fermer"
            >
              <X className="h-4 w-4" strokeWidth={1.75} />
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
