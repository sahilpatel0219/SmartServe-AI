/**
 * Toasts — the React replacement for django.contrib.messages, which no longer
 * has a place now that the backend returns JSON only.
 */
import { createContext, useContext, useState, useCallback } from 'react';

const ToastContext = createContext(null);
let nextId = 1;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (message, variant = 'info', ttl = 4500) => {
      const id = nextId++;
      setToasts((current) => [...current, { id, message, variant }]);
      if (ttl) setTimeout(() => dismiss(id), ttl);
      return id;
    },
    [dismiss],
  );

  const toast = {
    success: (m) => push(m, 'success'),
    error: (m) => push(m, 'danger', 7000),
    warning: (m) => push(m, 'warning'),
    info: (m) => push(m, 'info'),
  };

  return (
    <ToastContext.Provider value={{ toast, toasts, dismiss }}>{children}</ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used inside ToastProvider');
  return ctx;
}
