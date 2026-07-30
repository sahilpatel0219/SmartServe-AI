/**
 * Shared presentational primitives, all reading from the design tokens.
 */
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

// ── Cards / bento ─────────────────────────────────────────────────────────────
export function Card({ title, subtitle, icon, iconColor, actions, children, className = '' }) {
  return (
    <div className={`card ${className}`}>
      {(title || actions) && (
        <div className="card-header">
          <div style={{ minWidth: 0 }}>
            {title && <span className="card-title">{title}</span>}
            {subtitle && <div className="text-muted text-sm mt-2">{subtitle}</div>}
          </div>
          {actions}
          {icon && !actions && (
            <i className={`bi ${icon}`} style={{ fontSize: '1.4rem', color: iconColor || 'var(--brand)' }} />
          )}
        </div>
      )}
      <div className="card-body">{children}</div>
    </div>
  );
}

export function BentoCell({ span = 3, rows = 1, variant, children, className = '', style }) {
  const variantClass = variant ? `bento-cell--${variant}` : '';
  return (
    <div className={`bento-cell b-${span} ${rows === 2 ? 'b-rows-2' : ''} ${variantClass} ${className}`} style={style}>
      {children}
    </div>
  );
}

// ── KPI tile ──────────────────────────────────────────────────────────────────
/**
 * `value === null | undefined` means "no data yet" — we render a dash, never a
 * zero or a made-up number.
 */
export function StatCard({ label, value, icon, prefix = '', suffix = '', change, tone = 'muted', flat = false }) {
  const hasValue = value !== null && value !== undefined;
  const display = hasValue ? `${prefix}${formatNumber(value)}${suffix}` : '—';

  return (
    <div className={flat ? 'stat-card stat-card--flat' : 'stat-card'}>
      {icon && (
        <div className="stat-icon" style={tone !== 'muted' ? { background: `var(--${tone}-tint)`, color: `var(--${tone})` } : undefined}>
          <i className={`bi ${icon}`} />
        </div>
      )}
      <div style={{ minWidth: 0 }}>
        <div className="stat-value">{hasValue ? <CountUp value={value} prefix={prefix} suffix={suffix} /> : display}</div>
        <div className="stat-label">{label}</div>
        {change !== undefined && change !== null && (
          <div className={`stat-change ${change >= 0 ? 'up' : 'down'}`}>
            <i className={`bi ${change >= 0 ? 'bi-arrow-up-right' : 'bi-arrow-down-right'}`} />
            {Math.abs(change)}%
          </div>
        )}
      </div>
    </div>
  );
}

/** Count-up animation, skipped entirely under prefers-reduced-motion. */
export function CountUp({ value, prefix = '', suffix = '', duration = 700 }) {
  const numeric = Number(value) || 0;
  const [shown, setShown] = useState(() => (prefersReducedMotion() ? numeric : 0));
  const rafRef = useRef();

  useEffect(() => {
    if (prefersReducedMotion()) {
      setShown(numeric);
      return undefined;
    }
    const start = performance.now();
    const from = 0;
    const tick = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setShown(from + (numeric - from) * eased);
      if (progress < 1) rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    // Safety net: requestAnimationFrame never fires in some backgrounded/
    // non-compositing contexts, which would otherwise leave a real KPI number
    // stuck at 0 forever. Force the final value once duration has elapsed.
    const fallback = setTimeout(() => setShown(numeric), duration + 50);
    return () => {
      cancelAnimationFrame(rafRef.current);
      clearTimeout(fallback);
    };
  }, [numeric, duration]);

  return (
    <span>
      {prefix}
      {formatNumber(shown)}
      {suffix}
    </span>
  );
}

function prefersReducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function formatNumber(n) {
  const num = Number(n);
  if (!Number.isFinite(num)) return '—';
  if (Number.isInteger(num)) return num.toLocaleString('en-IN');
  return num.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

export const rupees = (n) => (n === null || n === undefined ? '—' : `₹${formatNumber(n)}`);

// ── Empty state ───────────────────────────────────────────────────────────────
/**
 * The core product principle in component form: when there is no data, say so
 * and point at the upload flow. Never render placeholder metrics.
 */
export function EmptyState({ icon = 'bi-inbox', title, desc, actionLabel, actionTo, onAction }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <i className={`bi ${icon}`} />
      </div>
      <h3 className="empty-title">{title}</h3>
      {desc && <p className="empty-desc">{desc}</p>}
      {actionLabel && actionTo && (
        <Link to={actionTo} className="btn btn-primary">
          <i className="bi bi-upload" /> {actionLabel}
        </Link>
      )}
      {actionLabel && onAction && (
        <button type="button" className="btn btn-primary" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  );
}

export function UploadPrompt({ title = 'No Data Yet', desc }) {
  return (
    <EmptyState
      icon="bi-cloud-upload"
      title={title}
      desc={desc || 'Upload your business data to unlock this screen. Nothing here is simulated — every number comes from your own records.'}
      actionLabel="Upload Data"
      actionTo="/upload"
    />
  );
}

// ── Loading / error ───────────────────────────────────────────────────────────
export function Loading({ label = 'Loading…', rows = 3 }) {
  return (
    <div aria-busy="true" aria-label={label}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton" style={{ height: 64, marginBottom: 12 }} />
      ))}
    </div>
  );
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="alert alert-danger">
      <i className="bi bi-exclamation-octagon-fill" />
      <div style={{ flex: 1 }}>
        <div className="fw-semi">Couldn’t load this</div>
        <div className="text-sm">{error?.message || 'Unknown error.'}</div>
      </div>
      {onRetry && (
        <button type="button" className="btn btn-sm btn-outline" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

// ── Page header ───────────────────────────────────────────────────────────────
export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="page-header">
      <div>
        <h1 className="page-header__title">{title}</h1>
        {subtitle && <div className="page-header__sub">{subtitle}</div>}
      </div>
      {children && <div className="page-header__actions">{children}</div>}
    </div>
  );
}

// ── Table ─────────────────────────────────────────────────────────────────────
/**
 * columns: [{ key, label, render?(row), align? }]
 */
export function DataTable({ columns, rows, rowKey = 'id', empty = 'Nothing here yet.' }) {
  if (!rows?.length) return <p className="text-muted text-sm">{empty}</p>;
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} style={c.align ? { textAlign: c.align } : undefined}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row[rowKey]}>
              {columns.map((c) => (
                <td key={c.key} style={c.align ? { textAlign: c.align } : undefined}>
                  {c.render ? c.render(row) : row[c.key] ?? '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Modal ─────────────────────────────────────────────────────────────────────
export function Modal({ title, onClose, children, footer }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose?.();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div className="modal-panel" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-label={title}>
        <div className="card-header">
          <span className="card-title">{title}</span>
          <button type="button" className="topbar-icon-btn" onClick={onClose} aria-label="Close">
            <i className="bi bi-x-lg" />
          </button>
        </div>
        <div className="card-body">{children}</div>
        {footer && <div className="card-footer flex justify-end gap-2">{footer}</div>}
      </div>
    </div>
  );
}

// ── Form field ────────────────────────────────────────────────────────────────
export function Field({ label, error, hint, children }) {
  return (
    <div className="form-group">
      {label && <label className="form-label">{label}</label>}
      {children}
      {hint && <div className="form-text">{hint}</div>}
      {error && <div className="invalid-feedback">{error}</div>}
    </div>
  );
}

export function Badge({ variant = 'neutral', children }) {
  return <span className={`badge badge-${variant}`}>{children}</span>;
}

export function ProgressBar({ value, indeterminate }) {
  return (
    <div className={`progress-bar ${indeterminate ? 'indeterminate' : ''}`}>
      <div className="progress-fill" style={{ width: indeterminate ? undefined : `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  );
}
