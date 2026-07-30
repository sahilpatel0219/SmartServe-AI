import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';

import { auth as authApi, businesses as businessesApi } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useToast } from '../context/ToastContext';
import { Badge, Card, DataTable, Field, PageHeader } from '../components/ui';

const BUSINESS_TYPES = [
  ['restaurant', 'Restaurant'], ['cafe', 'Café'], ['bakery', 'Bakery'], ['food_stall', 'Food Stall'],
  ['cloud_kitchen', 'Cloud Kitchen'], ['juice_bar', 'Juice Bar'], ['fast_food', 'Fast Food'], ['food_truck', 'Food Truck'],
];

export default function Settings() {
  const { user, business, role, isManager, memberships, refresh, switchBusiness } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { toast } = useToast();

  const [profile, setProfile] = useState({
    first_name: user?.first_name || '', last_name: user?.last_name || '',
    phone: user?.phone || '', email: user?.email || '',
  });
  const [bizForm, setBizForm] = useState({
    name: business?.name || '', business_type: business?.business_type || 'restaurant',
  });

  const historyQuery = useQuery({ queryKey: ['login-history'], queryFn: authApi.loginHistory });

  const profileMutation = useMutation({
    mutationFn: () => authApi.updateProfile(profile),
    onSuccess: async () => {
      toast.success('Profile updated.');
      await refresh();
    },
    onError: (err) => toast.error(err.message),
  });

  const businessMutation = useMutation({
    mutationFn: () => businessesApi.update(business.id, bizForm),
    onSuccess: async () => {
      toast.success('Business details updated.');
      await refresh();
    },
    onError: (err) => toast.error(err.message),
  });

  const setP = (key) => (e) => setProfile((f) => ({ ...f, [key]: e.target.value }));
  const setB = (key) => (e) => setBizForm((f) => ({ ...f, [key]: e.target.value }));

  return (
    <>
      <PageHeader title="Settings" subtitle="Your account, workspace, and appearance." />

      <div className="flex flex-col gap-4" style={{ maxWidth: 640, margin: '0 auto' }}>
        <Card title="Account">
          <div className="grid grid-2 gap-3">
            <Field label="First name">
              <input className="form-control" value={profile.first_name} onChange={setP('first_name')} />
            </Field>
            <Field label="Last name">
              <input className="form-control" value={profile.last_name} onChange={setP('last_name')} />
            </Field>
          </div>
          <Field label="Email">
            <input type="email" className="form-control" value={profile.email} onChange={setP('email')} />
          </Field>
          <Field label="Phone">
            <input className="form-control" value={profile.phone} onChange={setP('phone')} />
          </Field>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => profileMutation.mutate()}
            disabled={profileMutation.isPending}
          >
            {profileMutation.isPending ? <span className="spinner" /> : 'Save profile'}
          </button>
        </Card>

        <Card title="Business" subtitle={isManager ? undefined : 'Only the owner or a manager can edit these.'}>
          <Field label="Business name">
            <input className="form-control" value={bizForm.name} onChange={setB('name')} disabled={!isManager} />
          </Field>
          <Field label="Business type">
            <select className="form-control" value={bizForm.business_type} onChange={setB('business_type')} disabled={!isManager}>
              {BUSINESS_TYPES.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </Field>
          <div className="flex gap-2 items-center mb-4">
            <span className="text-sm text-muted">Your role:</span>
            <Badge variant="brand">{role}</Badge>
          </div>
          {isManager && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => businessMutation.mutate()}
              disabled={businessMutation.isPending}
            >
              {businessMutation.isPending ? <span className="spinner" /> : 'Save business'}
            </button>
          )}
        </Card>

        <Card title="Appearance">
          <p className="text-sm text-muted mb-4">
            Dark (Ember) is the default. Light (Orchard) is the green alternate. Your choice is remembered on this device.
          </p>
          <button type="button" className="btn btn-outline" onClick={toggleTheme}>
            <i className={`bi ${theme === 'dark' ? 'bi-sun' : 'bi-moon-stars'}`} />
            Change Theme — currently {theme}
          </button>
        </Card>

        {memberships?.length > 1 && (
          <Card title="Workspaces">
            {memberships.map((m) => (
              <div key={m.id} className="flex items-center justify-between" style={{ padding: 'var(--space-3) 0', borderBottom: '1px solid var(--hairline)' }}>
                <div>
                  <div className="text-sm fw-medium">{m.business.name}</div>
                  <div className="text-xs text-muted">{m.role}</div>
                </div>
                {m.business.id === business?.id ? (
                  <Badge variant="success">Active</Badge>
                ) : (
                  <button type="button" className="btn btn-sm btn-outline" onClick={() => switchBusiness(m.business.id)}>
                    Switch
                  </button>
                )}
              </div>
            ))}
          </Card>
        )}

        <Card title="Recent sign-ins">
          <DataTable
            columns={[
              {
                key: 'logged_in_at',
                label: 'When',
                render: (r) => (r.logged_in_at ? new Date(r.logged_in_at).toLocaleString() : '—'),
              },
              { key: 'ip_address', label: 'IP', render: (r) => r.ip_address || '—' },
              {
                key: 'success',
                label: 'Result',
                render: (r) => <Badge variant={r.success ? 'success' : 'danger'}>{r.success ? 'Success' : 'Failed'}</Badge>,
              },
            ]}
            rows={(historyQuery.data || []).map((h, i) => ({ ...h, id: i }))}
            empty="No sign-in history yet."
          />
        </Card>

        <Card title="About">
          <div className="flex items-center gap-3 mb-4">
            <div className="logo-mark">S</div>
            <div>
              <div className="fw-semi">SmartServe AI</div>
              <div className="text-xs text-muted">Version 1.0.0</div>
            </div>
          </div>
          <p className="text-sm text-muted mb-4">
            An AI-powered operating system for food businesses — orders, inventory, staff, suppliers,
            analytics, and forecasting in one place. Every insight is computed from your own uploaded
            data; nothing is simulated or guessed.
          </p>
          <div className="flex flex-wrap gap-2 mb-4">
            <Badge variant="neutral">React + Vite</Badge>
            <Badge variant="neutral">Django REST Framework</Badge>
            <Badge variant="neutral">MongoDB</Badge>
            <Badge variant="neutral">XGBoost</Badge>
          </div>
          <p className="text-xs text-faint mb-0">© {new Date().getFullYear()} SmartServe AI. All rights reserved.</p>
        </Card>
      </div>
    </>
  );
}
