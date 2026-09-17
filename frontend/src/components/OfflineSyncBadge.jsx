import { useCallback, useEffect, useState } from 'react';
import { CloudOff, RefreshCw } from 'lucide-react';
import {
  getOfflineConflictCount,
  getOfflineQueueCount,
  syncOfflineQueue,
} from '../utils/offlineQueue';

/** Badge shell — file hors-ligne + Sync now. */
export default function OfflineSyncBadge() {
  const [pending, setPending] = useState(0);
  const [conflicts, setConflicts] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [online, setOnline] = useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  );

  const refresh = useCallback(async () => {
    try {
      const [p, c] = await Promise.all([getOfflineQueueCount(), getOfflineConflictCount()]);
      setPending(p);
      setConflicts(c);
    } catch {
      setPending(0);
      setConflicts(0);
    }
  }, []);

  useEffect(() => {
    refresh();
    const onChange = () => refresh();
    const onOnline = () => {
      setOnline(true);
      refresh();
    };
    const onOffline = () => setOnline(false);
    window.addEventListener('gs-offline-queue-changed', onChange);
    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);
    const t = setInterval(refresh, 15000);
    return () => {
      window.removeEventListener('gs-offline-queue-changed', onChange);
      window.removeEventListener('online', onOnline);
      window.removeEventListener('offline', onOffline);
      clearInterval(t);
    };
  }, [refresh]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await syncOfflineQueue();
      await refresh();
    } finally {
      setSyncing(false);
    }
  };

  if (online && pending === 0 && conflicts === 0) {
    return null;
  }

  return (
    <div
      className="flex items-center gap-2 rounded-input border border-bordure/70 bg-blanc px-2.5 py-1.5 text-xs text-encre shadow-soft"
      role="status"
      aria-live="polite"
    >
      <CloudOff className="h-3.5 w-3.5 shrink-0 text-texte-secondaire" strokeWidth={1.75} />
      <span className="tabular-nums">
        {!online ? 'Hors ligne' : null}
        {!online && pending > 0 ? ' · ' : null}
        {pending > 0 ? `${pending} en attente` : null}
        {conflicts > 0 ? `${pending > 0 || !online ? ' · ' : ''}${conflicts} conflit(s)` : null}
      </span>
      <button
        type="button"
        className="inline-flex items-center gap-1 rounded-input bg-craie px-2 py-0.5 font-medium text-or-cachet hover:bg-or-cachet-clair disabled:opacity-50"
        onClick={handleSync}
        disabled={syncing || !online || (pending === 0 && conflicts === 0)}
      >
        <RefreshCw className={`h-3 w-3 ${syncing ? 'animate-spin' : ''}`} strokeWidth={2} />
        Sync now
      </button>
    </div>
  );
}
