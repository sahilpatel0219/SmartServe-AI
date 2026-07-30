import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { businesses } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { Field } from '../components/ui';

const BUSINESS_TYPES = [
  ['restaurant', 'Restaurant'],
  ['cafe', 'Café'],
  ['bakery', 'Bakery'],
  ['food_stall', 'Food Stall'],
  ['cloud_kitchen', 'Cloud Kitchen'],
  ['juice_bar', 'Juice Bar'],
  ['fast_food', 'Fast Food'],
  ['food_truck', 'Food Truck'],
];

export default function CreateBusiness() {
  const { switchBusiness, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: '', business_type: 'restaurant', city: '', state: '', phone: '', email: '',
  });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  if (!loading && !isAuthenticated) {
    navigate('/login', { replace: true });
  }

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      const business = await businesses.create(form);
      await switchBusiness(business.id);
      // Data upload is the gate for every AI feature, so go straight there.
      navigate('/upload', { replace: true });
    } catch (err) {
      setError(err.message || 'Could not create the workspace.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page glow-wrap">
      <div className="glow-blob" style={{ top: '-15%', right: '-15%' }} />
      <div className="auth-card" style={{ maxWidth: 560 }}>
        <div className="auth-logo">
          <div className="logo-mark">S</div>
          <div>
            <div className="logo-text">Set up your workspace</div>
            <div className="logo-sub">All of your data stays scoped to this business</div>
          </div>
        </div>

        {error && (
          <div className="alert alert-danger">
            <i className="bi bi-exclamation-octagon-fill" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={onSubmit}>
          <Field label="Business name">
            <input className="form-control" value={form.name} onChange={set('name')} required autoFocus />
          </Field>
          <Field label="Business type">
            <select className="form-control" value={form.business_type} onChange={set('business_type')}>
              {BUSINESS_TYPES.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </Field>
          <div className="grid grid-2 gap-3">
            <Field label="City">
              <input className="form-control" value={form.city} onChange={set('city')} />
            </Field>
            <Field label="State">
              <input className="form-control" value={form.state} onChange={set('state')} />
            </Field>
          </div>
          <div className="grid grid-2 gap-3">
            <Field label="Phone">
              <input className="form-control" value={form.phone} onChange={set('phone')} />
            </Field>
            <Field label="Business email">
              <input type="email" className="form-control" value={form.email} onChange={set('email')} />
            </Field>
          </div>

          <button type="submit" className="btn btn-primary btn-lg w-full" disabled={busy}>
            {busy ? <span className="spinner" /> : <>Create workspace <i className="bi bi-arrow-right" /></>}
          </button>
        </form>
      </div>
    </div>
  );
}
