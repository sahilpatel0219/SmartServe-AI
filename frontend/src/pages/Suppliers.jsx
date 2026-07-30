import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { suppliers as suppliersApi } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import {
  Badge, Card, DataTable, ErrorState, Field, Loading, Modal, PageHeader, rupees,
} from '../components/ui';

const BLANK = { name: '', contact_person: '', phone: '', email: '', address: '', products: '', payment_terms: '' };
const BLANK_PO = { supplier_id: '', supplier_name: '', items: '', total_amount: '' };

export default function Suppliers() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { isManager } = useAuth();
  const [editing, setEditing] = useState(null);
  const [creatingPO, setCreatingPO] = useState(false);

  const suppliersQuery = useQuery({ queryKey: ['suppliers'], queryFn: suppliersApi.list });
  const posQuery = useQuery({ queryKey: ['purchase-orders'], queryFn: suppliersApi.purchaseOrders });

  const saveMutation = useMutation({
    mutationFn: (s) => (s.id ? suppliersApi.update(s.id, s) : suppliersApi.create(s)),
    onSuccess: () => {
      toast.success('Supplier saved.');
      setEditing(null);
      queryClient.invalidateQueries({ queryKey: ['suppliers'] });
    },
    onError: (err) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: suppliersApi.remove,
    onSuccess: () => {
      toast.success('Supplier removed.');
      queryClient.invalidateQueries({ queryKey: ['suppliers'] });
    },
    onError: (err) => toast.error(err.message),
  });

  const poMutation = useMutation({
    mutationFn: suppliersApi.createPurchaseOrder,
    onSuccess: () => {
      toast.success('Purchase order created.');
      setCreatingPO(false);
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
    },
    onError: (err) => toast.error(err.message),
  });

  if (suppliersQuery.isLoading) return <Loading rows={4} />;
  if (suppliersQuery.error) return <ErrorState error={suppliersQuery.error} onRetry={suppliersQuery.refetch} />;

  const supplierColumns = [
    { key: 'name', label: 'Supplier' },
    { key: 'contact_person', label: 'Contact', render: (r) => r.contact_person || '—' },
    { key: 'phone', label: 'Phone', render: (r) => r.phone || '—' },
    { key: 'products', label: 'Supplies', render: (r) => r.products || '—' },
    { key: 'payment_terms', label: 'Terms', render: (r) => r.payment_terms || '—' },
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

  const poColumns = [
    { key: 'supplier_name', label: 'Supplier', render: (r) => r.supplier_name || '—' },
    { key: 'items', label: 'Items', render: (r) => r.items || '—' },
    { key: 'total_amount', label: 'Total', align: 'right', render: (r) => rupees(r.total_amount) },
    { key: 'status', label: 'Status', render: (r) => <Badge variant="warning">{r.status}</Badge> },
    {
      key: 'created_at',
      label: 'Created',
      render: (r) => (r.created_at ? new Date(r.created_at).toLocaleDateString() : '—'),
    },
  ];

  return (
    <>
      <PageHeader title="Suppliers" subtitle="Vendors and purchase orders.">
        <button type="button" className="btn btn-outline" onClick={() => setCreatingPO(true)}>
          <i className="bi bi-file-earmark-plus" /> New PO
        </button>
        <button type="button" className="btn btn-primary" onClick={() => setEditing({ ...BLANK })}>
          <i className="bi bi-plus-lg" /> Add Supplier
        </button>
      </PageHeader>

      <Card title={`${suppliersQuery.data.suppliers.length} supplier(s)`} className="mb-6">
        <DataTable columns={supplierColumns} rows={suppliersQuery.data.suppliers} empty="No suppliers added yet." />
      </Card>

      <Card title="Purchase orders">
        {posQuery.isLoading ? (
          <Loading rows={2} />
        ) : (
          <DataTable columns={poColumns} rows={posQuery.data?.purchase_orders || []} empty="No purchase orders yet." />
        )}
      </Card>

      {editing && (
        <SupplierModal
          supplier={editing}
          busy={saveMutation.isPending}
          onClose={() => setEditing(null)}
          onSave={(s) => saveMutation.mutate(s)}
        />
      )}
      {creatingPO && (
        <PurchaseOrderModal
          suppliers={suppliersQuery.data.suppliers}
          busy={poMutation.isPending}
          onClose={() => setCreatingPO(false)}
          onSave={(po) => poMutation.mutate(po)}
        />
      )}
    </>
  );
}

function SupplierModal({ supplier, onSave, onClose, busy }) {
  const [form, setForm] = useState(supplier);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  return (
    <Modal
      title={supplier.id ? 'Edit supplier' : 'Add supplier'}
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
      <Field label="Supplier name">
        <input className="form-control" value={form.name || ''} onChange={set('name')} autoFocus />
      </Field>
      <div className="grid grid-2 gap-3">
        <Field label="Contact person">
          <input className="form-control" value={form.contact_person || ''} onChange={set('contact_person')} />
        </Field>
        <Field label="Phone">
          <input className="form-control" value={form.phone || ''} onChange={set('phone')} />
        </Field>
      </div>
      <Field label="Email">
        <input type="email" className="form-control" value={form.email || ''} onChange={set('email')} />
      </Field>
      <Field label="Address">
        <textarea className="form-control" value={form.address || ''} onChange={set('address')} />
      </Field>
      <div className="grid grid-2 gap-3">
        <Field label="Supplies" hint="What they provide.">
          <input className="form-control" value={form.products || ''} onChange={set('products')} />
        </Field>
        <Field label="Payment terms" hint="Net 30, COD…">
          <input className="form-control" value={form.payment_terms || ''} onChange={set('payment_terms')} />
        </Field>
      </div>
    </Modal>
  );
}

function PurchaseOrderModal({ suppliers, onSave, onClose, busy }) {
  const [form, setForm] = useState(BLANK_PO);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const onSupplierChange = (e) => {
    const id = e.target.value;
    const supplier = suppliers.find((s) => s.id === id);
    setForm((f) => ({ ...f, supplier_id: id, supplier_name: supplier?.name || '' }));
  };

  return (
    <Modal
      title="New purchase order"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-outline" onClick={onClose} disabled={busy}>Cancel</button>
          <button type="button" className="btn btn-primary" onClick={() => onSave(form)} disabled={busy || !form.supplier_id}>
            {busy ? <span className="spinner" /> : 'Create PO'}
          </button>
        </>
      }
    >
      <Field label="Supplier">
        <select className="form-control" value={form.supplier_id} onChange={onSupplierChange}>
          <option value="">Select a supplier…</option>
          {suppliers.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
      </Field>
      <Field label="Items" hint="Free text for now — one line per item works well.">
        <textarea className="form-control" value={form.items} onChange={set('items')} />
      </Field>
      <Field label="Total amount (₹)">
        <input type="number" step="any" className="form-control" value={form.total_amount} onChange={set('total_amount')} />
      </Field>
    </Modal>
  );
}
