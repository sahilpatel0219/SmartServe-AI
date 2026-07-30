import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { customers as customersApi } from '../api/endpoints';
import { useToast } from '../context/ToastContext';
import {
  Badge, Card, DataTable, ErrorState, Field, Loading, Modal, PageHeader, UploadPrompt, rupees,
} from '../components/ui';

const SEGMENT_TONE = { VIP: 'brand', Regular: 'success', Inactive: 'neutral' };
const BLANK = { name: '', phone: '', email: '', notes: '' };

export default function Customers() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [segment, setSegment] = useState('');
  const [editing, setEditing] = useState(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['customers', segment],
    queryFn: () => customersApi.list(segment),
  });

  const saveMutation = useMutation({
    mutationFn: (c) => (c.id ? customersApi.update(c.id, c) : customersApi.create(c)),
    onSuccess: () => {
      toast.success('Customer saved.');
      setEditing(null);
      queryClient.invalidateQueries({ queryKey: ['customers'] });
    },
    onError: (err) => toast.error(err.message),
  });

  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isLoading || !data) return <Loading rows={4} />;

  const columns = [
    { key: 'name', label: 'Customer' },
    { key: 'phone', label: 'Phone', render: (r) => r.phone || '—' },
    { key: 'email', label: 'Email', render: (r) => r.email || '—' },
    { key: 'visit_count', label: 'Visits', align: 'right' },
    { key: 'total_spend', label: 'Total spend', align: 'right', render: (r) => rupees(r.total_spend) },
    {
      key: 'segment',
      label: 'Segment',
      render: (r) => <Badge variant={SEGMENT_TONE[r.segment] || 'neutral'}>{r.segment}</Badge>,
    },
    {
      key: 'actions',
      label: '',
      align: 'right',
      render: (r) => (
        <button type="button" className="btn btn-sm btn-outline" onClick={() => setEditing(r)}>
          <i className="bi bi-pencil" />
        </button>
      ),
    },
  ];

  return (
    <>
      <PageHeader title="Customers" subtitle="Visit counts and spend are derived from orders, not editable by hand.">
        <button type="button" className="btn btn-primary" onClick={() => setEditing({ ...BLANK })}>
          <i className="bi bi-plus-lg" /> Add Customer
        </button>
      </PageHeader>

      {!data.customers.length && !segment ? (
        <UploadPrompt title="No Customers Yet" desc="Upload your customer list for segmentation, or add customers one at a time." />
      ) : (
        <>
          <div className="flex gap-2 flex-wrap mb-6">
            <button type="button" className={`btn btn-sm ${!segment ? 'btn-primary' : 'btn-outline'}`} onClick={() => setSegment('')}>
              All
            </button>
            {data.segments.map((s) => (
              <button key={s} type="button" className={`btn btn-sm ${segment === s ? 'btn-primary' : 'btn-outline'}`} onClick={() => setSegment(s)}>
                {s}
              </button>
            ))}
          </div>

          <Card title={`${data.customers.length} customer(s)`}>
            <DataTable columns={columns} rows={data.customers} empty="No customers in this segment." />
          </Card>
        </>
      )}

      {editing && (
        <CustomerModal
          customer={editing}
          busy={saveMutation.isPending}
          onClose={() => setEditing(null)}
          onSave={(c) => saveMutation.mutate(c)}
        />
      )}
    </>
  );
}

function CustomerModal({ customer, onSave, onClose, busy }) {
  const [form, setForm] = useState(customer);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  return (
    <Modal
      title={customer.id ? 'Edit customer' : 'Add customer'}
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
        <Field label="Phone">
          <input className="form-control" value={form.phone || ''} onChange={set('phone')} />
        </Field>
        <Field label="Email">
          <input type="email" className="form-control" value={form.email || ''} onChange={set('email')} />
        </Field>
      </div>
      <Field label="Notes" hint="Preferences, allergies, anything worth remembering.">
        <textarea className="form-control" value={form.notes || ''} onChange={set('notes')} />
      </Field>
      {customer.id && (
        <p className="form-text">
          Visits ({customer.visit_count}) and spend ({rupees(customer.total_spend)}) are system-managed and can’t be edited here.
        </p>
      )}
    </Modal>
  );
}
