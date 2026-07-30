import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { staff as staffApi } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import {
  Badge, Card, DataTable, ErrorState, Field, Loading, Modal, PageHeader, rupees,
} from '../components/ui';

const BLANK = { name: '', role: '', phone: '', email: '', salary: '', join_date: '', status: 'active' };
const ATTENDANCE_OPTIONS = ['present', 'absent', 'half_day', 'leave'];

export default function Staff() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { isManager } = useAuth();
  const [editing, setEditing] = useState(null);
  const [markingAttendance, setMarkingAttendance] = useState(false);

  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['staff'], queryFn: staffApi.list });

  const saveMutation = useMutation({
    mutationFn: (emp) => (emp.id ? staffApi.update(emp.id, emp) : staffApi.create(emp)),
    onSuccess: () => {
      toast.success('Employee saved.');
      setEditing(null);
      queryClient.invalidateQueries({ queryKey: ['staff'] });
    },
    onError: (err) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: staffApi.remove,
    onSuccess: () => {
      toast.success('Employee removed.');
      queryClient.invalidateQueries({ queryKey: ['staff'] });
    },
    onError: (err) => toast.error(err.message),
  });

  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isLoading || !data) return <Loading rows={4} />;

  const columns = [
    { key: 'name', label: 'Name' },
    { key: 'role', label: 'Role', render: (r) => r.role || '—' },
    { key: 'phone', label: 'Phone', render: (r) => r.phone || '—' },
    // Salary is sensitive — only managers/owners see the column contents.
    {
      key: 'salary',
      label: 'Salary',
      align: 'right',
      render: (r) => (isManager ? rupees(r.salary) : <span className="text-muted">Hidden</span>),
    },
    { key: 'join_date', label: 'Joined', render: (r) => r.join_date || '—' },
    {
      key: 'status',
      label: 'Status',
      render: (r) => <Badge variant={r.status === 'active' ? 'success' : 'neutral'}>{r.status}</Badge>,
    },
    {
      key: 'actions',
      label: '',
      align: 'right',
      render: (r) => (
        <div className="flex gap-2 justify-end">
          <button type="button" className="btn btn-sm btn-outline" onClick={() => setEditing(r)}>
            <i className="bi bi-pencil" />
          </button>
          {isManager && (
            <button
              type="button"
              className="btn btn-sm btn-ghost"
              onClick={() => { if (window.confirm(`Remove ${r.name}?`)) deleteMutation.mutate(r.id); }}
            >
              <i className="bi bi-trash" />
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <>
      <PageHeader title="Staff" subtitle="Your team, roles, and daily attendance.">
        <button type="button" className="btn btn-outline" onClick={() => setMarkingAttendance(true)}>
          <i className="bi bi-calendar-check" /> Attendance
        </button>
        <button type="button" className="btn btn-primary" onClick={() => setEditing({ ...BLANK })}>
          <i className="bi bi-plus-lg" /> Add Employee
        </button>
      </PageHeader>

      <Card title={`${data.employees.length} employee(s)`}>
        <DataTable columns={columns} rows={data.employees} empty="No employees added yet." />
      </Card>

      {editing && (
        <EmployeeModal
          employee={editing}
          canEditSalary={isManager}
          busy={saveMutation.isPending}
          onClose={() => setEditing(null)}
          onSave={(emp) => saveMutation.mutate(emp)}
        />
      )}
      {markingAttendance && <AttendanceModal onClose={() => setMarkingAttendance(false)} />}
    </>
  );
}

function EmployeeModal({ employee, onSave, onClose, busy, canEditSalary }) {
  const [form, setForm] = useState(employee);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  return (
    <Modal
      title={employee.id ? 'Edit employee' : 'Add employee'}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-outline" onClick={onClose} disabled={busy}>Cancel</button>
          <button type="button" className="btn btn-primary" onClick={() => onSave(form)} disabled={busy || !form.name?.trim()}>
            {busy ? <span className="spinner" /> : 'Save'}
          </button>
        </>
      }
    >
      <Field label="Name">
        <input className="form-control" value={form.name || ''} onChange={set('name')} autoFocus />
      </Field>
      <div className="grid grid-2 gap-3">
        <Field label="Role" hint="Chef, server, cashier…">
          <input className="form-control" value={form.role || ''} onChange={set('role')} />
        </Field>
        <Field label="Status">
          <select className="form-control" value={form.status || 'active'} onChange={set('status')}>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </Field>
      </div>
      <div className="grid grid-2 gap-3">
        <Field label="Phone">
          <input className="form-control" value={form.phone || ''} onChange={set('phone')} />
        </Field>
        <Field label="Email">
          <input type="email" className="form-control" value={form.email || ''} onChange={set('email')} />
        </Field>
      </div>
      <div className="grid grid-2 gap-3">
        {canEditSalary && (
          <Field label="Salary (₹)">
            <input type="number" step="any" className="form-control" value={form.salary ?? ''} onChange={set('salary')} />
          </Field>
        )}
        <Field label="Join date">
          <input type="date" className="form-control" value={form.join_date || ''} onChange={set('join_date')} />
        </Field>
      </div>
    </Modal>
  );
}

function AttendanceModal({ onClose }) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [statuses, setStatuses] = useState({});

  const { data, isLoading } = useQuery({ queryKey: ['attendance'], queryFn: staffApi.attendance });

  // Seed the form with whatever is already marked for today.
  useEffect(() => {
    if (!data?.employees) return;
    const seeded = {};
    data.employees.forEach((emp) => {
      seeded[emp.id] = emp.att_status || 'present';
    });
    setStatuses(seeded);
  }, [data]);

  const markMutation = useMutation({
    mutationFn: () => staffApi.markAttendance(statuses),
    onSuccess: (result) => {
      toast.success(`Attendance marked for ${result.date}.`);
      queryClient.invalidateQueries({ queryKey: ['attendance'] });
      onClose();
    },
    onError: (err) => toast.error(err.message),
  });

  return (
    <Modal
      title={`Attendance — ${data?.today || 'today'}`}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-outline" onClick={onClose} disabled={markMutation.isPending}>Cancel</button>
          <button type="button" className="btn btn-primary" onClick={() => markMutation.mutate()} disabled={markMutation.isPending || isLoading}>
            {markMutation.isPending ? <span className="spinner" /> : 'Save attendance'}
          </button>
        </>
      }
    >
      {isLoading && <Loading rows={3} />}
      {!isLoading && !data?.employees?.length && (
        <p className="text-sm text-muted">No active employees to mark.</p>
      )}
      {data?.employees?.map((emp) => (
        <div key={emp.id} className="flex items-center gap-3" style={{ padding: '8px 0', borderBottom: '1px solid var(--hairline)' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="text-sm fw-medium truncate">{emp.name}</div>
            <div className="text-xs text-muted">{emp.role || '—'}</div>
          </div>
          <select
            className="form-control"
            style={{ maxWidth: 140, minHeight: 36 }}
            value={statuses[emp.id] || 'present'}
            onChange={(e) => setStatuses((s) => ({ ...s, [emp.id]: e.target.value }))}
          >
            {ATTENDANCE_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>{opt.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>
      ))}
    </Modal>
  );
}
