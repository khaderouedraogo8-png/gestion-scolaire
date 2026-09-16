import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';

const ToastContext = createContext(null);

const TOAST_ICONS = {
  success: CheckCircle2,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

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
    success: 'border-feuille/40 bg-blanc text-feuille shadow-elevated',
    error: 'border-brique/40 bg-blanc text-brique shadow-elevated',
    warning: 'border-ambre/40 bg-blanc text-ambre shadow-elevated',
    info: 'border-or-cachet/40 bg-blanc text-or-cachet shadow-elevated',
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div
        className="fixed bottom-4 right-4 z-[100] flex max-w-[calc(100vw-2rem)] flex-col gap-2"
        aria-live="polite"
      >
        {toasts.map((t) => {
          const Icon = TOAST_ICONS[t.type] || Info;
          return (
            <div
              key={t.id}
              role="status"
              className={`toast-enter flex min-w-[280px] max-w-md items-start gap-3 rounded-card border px-4 py-3 ${typeStyles[t.type] || typeStyles.info}`}
            >
              <Icon className="mt-0.5 h-4 w-4 shrink-0" strokeWidth={2} aria-hidden="true" />
              <span className="flex-1 text-sm font-medium text-encre">{t.message}</span>
              <button
                type="button"
                onClick={() => removeToast(t.id)}
                className="rounded-md p-1 text-texte-secondaire transition-colors hover:bg-craie hover:text-encre"
                aria-label="Fermer"
              >
                <X className="h-3.5 w-3.5" strokeWidth={2} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
