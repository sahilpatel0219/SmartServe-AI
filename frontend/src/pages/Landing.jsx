import { Link } from 'react-router-dom';

import { useTheme } from '../context/ThemeContext';

const FEATURES = [
  { icon: 'bi-receipt', title: 'Order Management', desc: 'Counter, QR, delivery, phone — every order in one live board.' },
  { icon: 'bi-box-seam', title: 'Smart Inventory', desc: 'Stock auto-deducts as items sell. Alerts before you run out.' },
  { icon: 'bi-bar-chart-line', title: 'Real-Time Analytics', desc: 'Daily revenue, profit, top items, and busiest hours — from your own data.' },
  { icon: 'bi-cpu', title: 'AI Forecasting', desc: 'Demand forecasts, waste risk, and a health score — trained on your data.' },
  { icon: 'bi-chat-dots', title: 'AI Assistant', desc: 'Ask about your business in plain language. Answers straight from your data.' },
  { icon: 'bi-people', title: 'Team & Suppliers', desc: 'Staff shifts, attendance, suppliers, and purchase orders in one place.' },
];

export default function Landing() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div style={{ background: 'var(--bg-base)', minHeight: '100vh' }}>
      {/* Nav */}
      <header
        className="flex items-center justify-between"
        style={{
          padding: 'var(--space-4) var(--space-8)',
          borderBottom: '1px solid var(--hairline)',
        }}
      >
        <Link to="/" className="flex items-center gap-3" style={{ color: 'var(--text-primary)' }}>
          <div className="logo-mark">S</div>
          <div>
            <div className="logo-text">SmartServe AI</div>
            <div className="logo-sub">Operating system for food businesses</div>
          </div>
        </Link>
        <nav className="flex items-center gap-2">
          <button
            type="button"
            className="topbar-icon-btn"
            onClick={toggleTheme}
            aria-label={`Change theme (currently ${theme})`}
            title="Change Theme"
          >
            <i className={`bi ${theme === 'dark' ? 'bi-sun' : 'bi-moon-stars'}`} />
          </button>
          <Link to="/login" className="btn btn-ghost">Sign in</Link>
          <Link to="/register" className="btn btn-primary">Get started</Link>
        </nav>
      </header>

      {/* Hero */}
      <section
        className="glow-wrap text-center"
        style={{
          padding: 'var(--space-16) var(--space-8)',
          maxWidth: 900,
          margin: '0 auto',
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <div className="glow-blob" style={{ top: '-10%', left: '50%', transform: 'translateX(-50%)' }} />
        <span className="badge badge-brand" style={{ marginBottom: 'var(--space-5)' }}>
          <i className="bi bi-stars" /> Smarter Operations, Real Data
        </span>
        <h1 className="display-hero" style={{ marginBottom: 'var(--space-3)', maxWidth: 760 }}>
          Run your kitchen.
        </h1>
        <h2
          className="accent"
          style={{
            fontSize: 'clamp(1.5rem, 1rem + 2vw, 2.5rem)',
            fontWeight: 'var(--fw-black)',
            whiteSpace: 'nowrap',
            marginBottom: 'var(--space-5)',
          }}
        >
          Let the data run ahead of you.
        </h2>
        <p style={{ fontSize: '1.15rem', color: 'var(--text-muted)', maxWidth: 620, marginBottom: 'var(--space-8)' }}>
          No more juggling five different apps. Upload your sales data once, and get real forecasts,
          live inventory tracking, and answers to your questions — all from what actually happened in
          your business.
        </p>
        <div className="flex gap-3 flex-wrap justify-center">
          <Link to="/register" className="btn btn-primary btn-lg">
            Start free <i className="bi bi-arrow-right" />
          </Link>
          <Link to="/login" className="btn btn-outline btn-lg">
            Sign in
          </Link>
        </div>
      </section>

      {/* Features */}
      <section
        id="features"
        style={{ padding: 'var(--space-12) var(--space-8)', maxWidth: 1100, margin: '0 auto' }}
      >
        <h2 className="section-title mb-8 text-center">Built for the way food businesses actually work</h2>
        <div className="grid grid-3 gap-4">
          {FEATURES.map((f) => (
            <div key={f.title} className="card" style={{ padding: 'var(--space-6)' }}>
              <div
                style={{
                  width: 48, height: 48, borderRadius: 'var(--r-md)',
                  background: 'var(--brand-tint)', color: 'var(--brand)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '1.3rem', marginBottom: 'var(--space-4)',
                }}
              >
                <i className={`bi ${f.icon}`} />
              </div>
              <div className="fw-semi" style={{ fontSize: '1.0625rem', marginBottom: 'var(--space-2)' }}>
                {f.title}
              </div>
              <p className="text-sm text-muted mb-0">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section style={{ padding: 'var(--space-12) var(--space-8) var(--space-16)', maxWidth: 1100, margin: '0 auto' }}>
        <div
          className="bento-cell bento-cell--brand text-center"
          style={{ padding: 'var(--space-12)' }}
        >
          <h2 style={{ color: '#fff', marginBottom: 'var(--space-3)' }}>Set up your Workspace in under 5 minutes</h2>
          <p style={{ color: 'rgba(255,255,255,0.85)', maxWidth: 520, margin: '0 auto var(--space-6)' }}>
            Create your workspace, upload a CSV of sales history, and the dashboard is live.
          </p>
          <Link to="/register" className="btn btn-lg" style={{ background: '#fff', color: 'var(--brand)' }}>
            Create your workspace <i className="bi bi-arrow-right" />
          </Link>
        </div>
      </section>

      <footer
        className="text-center text-sm text-muted"
        style={{ padding: 'var(--space-6) var(--space-8)', borderTop: '1px solid var(--hairline)' }}
      >
        SmartServe AI · Built for cafés, restaurants, bakeries, and cloud kitchens.
      </footer>
    </div>
  );
}
