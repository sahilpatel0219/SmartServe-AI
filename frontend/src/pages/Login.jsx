import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';
import { Field } from '../components/ui';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      const data = await login(email, password);
      // A brand-new account has no workspace yet — send it to onboarding.
      navigate(data.active_membership ? location.state?.from?.pathname || '/dashboard' : '/onboarding', { replace: true });
    } catch (err) {
      setError(err.message || 'Invalid email or password.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page glow-wrap">
      <div className="glow-blob" style={{ top: '-20%', left: '-10%' }} />
      <div className="auth-card">
        <div className="auth-logo">
          <div className="logo-mark">S</div>
          <div>
            <div className="logo-text">SmartServe AI</div>
            <div className="logo-sub">Sign in to your workspace</div>
          </div>
        </div>

        {error && (
          <div className="alert alert-danger">
            <i className="bi bi-exclamation-octagon-fill" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={onSubmit}>
          <Field label="Email">
            <input
              type="email"
              className="form-control"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
              autoFocus
            />
          </Field>
          <Field label="Password">
            <input
              type="password"
              className="form-control"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </Field>

          <button type="submit" className="btn btn-primary btn-lg w-full" disabled={busy}>
            {busy ? <span className="spinner" /> : <>Sign in <i className="bi bi-arrow-right" /></>}
          </button>
        </form>

        <hr className="divider" />
        <p className="text-sm text-muted text-center mb-0">
          New here? <Link to="/register">Create an account</Link>
        </p>
      </div>
    </div>
  );
}
