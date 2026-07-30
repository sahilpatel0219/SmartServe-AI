import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';
import { Field } from '../components/ui';

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '', phone: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await register(form);
      // Registration always lands on onboarding — there's no workspace yet.
      navigate('/onboarding', { replace: true });
    } catch (err) {
      setError(err.message || 'Could not create your account.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page glow-wrap">
      <div className="glow-blob" style={{ bottom: '-25%', right: '-10%' }} />
      <div className="auth-card">
        <div className="auth-logo">
          <div className="logo-mark">S</div>
          <div>
            <div className="logo-text">Create your account</div>
            <div className="logo-sub">Then set up your business workspace</div>
          </div>
        </div>

        {error && (
          <div className="alert alert-danger">
            <i className="bi bi-exclamation-octagon-fill" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={onSubmit}>
          <div className="grid grid-2 gap-3">
            <Field label="First name">
              <input className="form-control" value={form.first_name} onChange={set('first_name')} required autoFocus />
            </Field>
            <Field label="Last name">
              <input className="form-control" value={form.last_name} onChange={set('last_name')} />
            </Field>
          </div>
          <Field label="Email">
            <input type="email" className="form-control" value={form.email} onChange={set('email')} autoComplete="email" required />
          </Field>
          <Field label="Phone">
            <input className="form-control" value={form.phone} onChange={set('phone')} autoComplete="tel" />
          </Field>
          <Field label="Password" hint="At least 8 characters.">
            <input
              type="password"
              className="form-control"
              value={form.password}
              onChange={set('password')}
              autoComplete="new-password"
              minLength={8}
              required
            />
          </Field>

          <button type="submit" className="btn btn-primary btn-lg w-full" disabled={busy}>
            {busy ? <span className="spinner" /> : <>Create account <i className="bi bi-arrow-right" /></>}
          </button>
        </form>

        <hr className="divider" />
        <p className="text-sm text-muted text-center mb-0">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
