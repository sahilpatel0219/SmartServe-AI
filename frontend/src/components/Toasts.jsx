import { useToast } from '../context/ToastContext';

const ICONS = {
  success: 'bi-check-circle-fill',
  danger: 'bi-exclamation-octagon-fill',
  warning: 'bi-exclamation-triangle-fill',
  info: 'bi-info-circle-fill',
};

export default function Toasts() {
  const { toasts, dismiss } = useToast();
  if (!toasts.length) return null;

  return (
    <div className="toast-container" role="status" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.variant}`}>
          <i className={`bi ${ICONS[t.variant] || ICONS.info}`} style={{ color: `var(--${t.variant === 'danger' ? 'danger' : t.variant})` }} />
          <span>{t.message}</span>
          <button type="button" className="toast__close" onClick={() => dismiss(t.id)} aria-label="Dismiss">
            <i className="bi bi-x" />
          </button>
        </div>
      ))}
    </div>
  );
}
