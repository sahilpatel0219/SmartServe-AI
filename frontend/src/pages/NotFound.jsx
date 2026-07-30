import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="auth-page glow-wrap">
      <div className="glow-blob" style={{ top: '-20%', left: '-10%' }} />
      <div className="auth-card text-center">
        <div className="empty-icon" style={{ margin: '0 auto var(--space-5)' }}>
          <i className="bi bi-compass" />
        </div>
        <h1 className="empty-title">Page not found</h1>
        <p className="empty-desc">That route doesn’t exist in SmartServe AI.</p>
        <Link to="/dashboard" className="btn btn-primary">
          <i className="bi bi-arrow-left" /> Back to dashboard
        </Link>
      </div>
    </div>
  );
}
