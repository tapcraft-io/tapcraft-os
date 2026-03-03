import { useState, useEffect, useCallback, createContext, useContext, type ReactNode } from 'react';

interface ToastItem {
  id: number;
  type: 'success' | 'error' | 'info';
  message: string;
}

interface ToastContextValue {
  addToast: (type: ToastItem['type'], message: string) => void;
}

const ToastContext = createContext<ToastContextValue>({ addToast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback((type: ToastItem['type'], message: string) => {
    const id = nextId++;
    setToasts(prev => [...prev, { id, type, message }]);
  }, []);

  const removeToast = useCallback((id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
        {toasts.map(toast => (
          <ToastMessage key={toast.id} toast={toast} onDismiss={removeToast} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastMessage({ toast, onDismiss }: { toast: ToastItem; onDismiss: (id: number) => void }) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(toast.id), 4000);
    return () => clearTimeout(timer);
  }, [toast.id, onDismiss]);

  const icon = toast.type === 'success' ? 'check_circle' : toast.type === 'error' ? 'error' : 'info';
  const colors = toast.type === 'success'
    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
    : toast.type === 'error'
      ? 'bg-red-500/10 border-red-500/20 text-red-400'
      : 'bg-sky-500/10 border-sky-500/20 text-sky-400';

  return (
    <div
      className={`pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-lg border backdrop-blur-sm shadow-lg min-w-[280px] max-w-[400px] animate-in slide-in-from-right ${colors}`}
    >
      <span className="material-symbols-outlined text-[18px] icon-filled shrink-0">{icon}</span>
      <span className="text-sm font-medium flex-1">{toast.message}</span>
      <button
        onClick={() => onDismiss(toast.id)}
        className="text-zinc-500 hover:text-zinc-300 transition-colors shrink-0"
      >
        <span className="material-symbols-outlined text-[16px]">close</span>
      </button>
    </div>
  );
}
