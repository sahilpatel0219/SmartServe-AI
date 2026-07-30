import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { menu as menuApi, orders as ordersApi } from '../api/endpoints';
import { useToast } from '../context/ToastContext';
import {
  Badge, Card, DataTable, ErrorState, Field, Loading, Modal, PageHeader, rupees,
} from '../components/ui';

const STATUS_TONE = {
  pending: 'warning',
  preparing: 'info',
  ready: 'brand',
  delivered: 'success',
  cancelled: 'danger',
};

const ORDER_TYPES = [
  ['dine_in', 'Dine In'],
  ['takeaway', 'Takeaway'],
  ['delivery', 'Delivery'],
  ['qr', 'QR Order'],
  ['phone', 'Phone'],
];

export default function Orders() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [statusFilter, setStatusFilter] = useState('');
  const [creating, setCreating] = useState(false);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['orders', statusFilter],
    queryFn: () => ordersApi.list(statusFilter),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['orders'] });
    // Creating an order deducts stock, so inventory is now stale too.
    queryClient.invalidateQueries({ queryKey: ['inventory'] });
    queryClient.invalidateQueries({ queryKey: ['dashboard'] });
  };

  const statusMutation = useMutation({
    mutationFn: ({ id, status }) => ordersApi.setStatus(id, status),
    onSuccess: () => invalidate(),
    onError: (err) => toast.error(err.message),
  });

  const createMutation = useMutation({
    mutationFn: ordersApi.create,
    onSuccess: (order) => {
      toast.success(`Order #${order.short_id} created — stock deducted.`);
      setCreating(false);
      invalidate();
    },
    onError: (err) => toast.error(err.message),
  });

  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isLoading || !data) return <Loading rows={4} />;

  const columns = [
    { key: 'short_id', label: 'Order', render: (r) => <span className="mono">#{r.short_id}</span> },
    {
      key: 'created_at',
      label: 'Placed',
      render: (r) => (r.created_at ? new Date(r.created_at).toLocaleString() : '—'),
    },
    { key: 'customer_name', label: 'Customer', render: (r) => r.customer_name || <span className="text-muted">Walk-in</span> },
    {
      key: 'items',
      label: 'Items',
      render: (r) => (Array.isArray(r.items) ? `${r.items.length} item(s)` : '—'),
    },
    { key: 'total_amount', label: 'Total', align: 'right', render: (r) => rupees(r.total_amount) },
    {
      key: 'order_type',
      label: 'Type',
      render: (r) => <Badge variant="neutral">{String(r.order_type || '').replace(/_/g, ' ')}</Badge>,
    },
    {
      key: 'status',
      label: 'Status',
      render: (r) => (
        <select
          className="form-control"
          style={{ minHeight: 34, padding: '4px 28px 4px 10px', fontSize: 'var(--text-xs)' }}
          value={r.status}
          onChange={(e) => statusMutation.mutate({ id: r.id, status: e.target.value })}
        >
          {data.statuses.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      ),
    },
  ];

  const hasOrders = data.orders.length > 0 || statusFilter;

  return (
    <>
      <PageHeader title="Orders" subtitle="Live order board. Placing an order deducts recipe ingredients from stock.">
        <button type="button" className="btn btn-primary" onClick={() => setCreating(true)}>
          <i className="bi bi-plus-lg" /> New Order
        </button>
      </PageHeader>

      <div className="flex gap-2 flex-wrap mb-6">
        <button type="button" className={`btn btn-sm ${!statusFilter ? 'btn-primary' : 'btn-outline'}`} onClick={() => setStatusFilter('')}>
          All
        </button>
        {data.statuses.map((s) => (
          <button
            key={s}
            type="button"
            className={`btn btn-sm ${statusFilter === s ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setStatusFilter(s)}
          >
            {s} <Badge variant={STATUS_TONE[s] || 'neutral'}>{data.counts[s]}</Badge>
          </button>
        ))}
      </div>

      {!hasOrders ? (
        <Card>
          <p className="text-muted text-sm mb-4">
            No orders yet. Create one from your menu, or upload historical orders for demand analysis.
          </p>
          <div className="flex gap-2">
            <button type="button" className="btn btn-primary btn-sm" onClick={() => setCreating(true)}>
              <i className="bi bi-plus-lg" /> New Order
            </button>
          </div>
        </Card>
      ) : (
        <Card title={`${data.orders.length} order(s)`}>
          <DataTable columns={columns} rows={data.orders} empty="No orders with this status." />
        </Card>
      )}

      {creating && (
        <NewOrderModal
          busy={createMutation.isPending}
          onClose={() => setCreating(false)}
          onSave={(payload) => createMutation.mutate(payload)}
        />
      )}
    </>
  );
}

function NewOrderModal({ onSave, onClose, busy }) {
  const [form, setForm] = useState({ order_type: 'dine_in', table_no: '', customer_name: '', notes: '' });
  const [quantities, setQuantities] = useState({}); // { menuItemId: qty }

  const { data, isLoading } = useQuery({ queryKey: ['menu', ''], queryFn: () => menuApi.list() });
  const available = (data?.items || []).filter((i) => i.is_available);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  const setQty = (id, value) => setQuantities((q) => ({ ...q, [id]: Math.max(0, Number(value) || 0) }));

  const lineItems = Object.entries(quantities)
    .filter(([, qty]) => qty > 0)
    .map(([item_id, quantity]) => ({ item_id, quantity }));

  const total = available.reduce((sum, item) => sum + (quantities[item.id] || 0) * (item.price || 0), 0);

  return (
    <Modal
      title="New order"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-outline" onClick={onClose} disabled={busy}>Cancel</button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => onSave({ ...form, items: lineItems })}
            disabled={busy || !lineItems.length}
          >
            {busy ? <span className="spinner" /> : `Create — ${rupees(total)}`}
          </button>
        </>
      }
    >
      <div className="grid grid-2 gap-3">
        <Field label="Order type">
          <select className="form-control" value={form.order_type} onChange={set('order_type')}>
            {ORDER_TYPES.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </Field>
        <Field label="Table no.">
          <input className="form-control" value={form.table_no} onChange={set('table_no')} />
        </Field>
      </div>
      <Field label="Customer name">
        <input className="form-control" value={form.customer_name} onChange={set('customer_name')} />
      </Field>
      <Field label="Notes">
        <textarea className="form-control" value={form.notes} onChange={set('notes')} />
      </Field>

      <hr className="divider" />
      <span className="fw-semi text-sm">Items</span>

      {isLoading && <Loading rows={2} />}
      {!isLoading && !available.length && (
        <p className="text-sm text-muted mt-4">
          No available menu items. Add items on the Menu screen first.
        </p>
      )}

      <div className="mt-4">
        {available.map((item) => (
          <div key={item.id} className="flex items-center gap-3" style={{ padding: '8px 0', borderBottom: '1px solid var(--hairline)' }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="text-sm fw-medium truncate">{item.name}</div>
              <div className="text-xs text-muted">{rupees(item.price)}</div>
            </div>
            <input
              type="number"
              min="0"
              className="form-control"
              style={{ maxWidth: 80, minHeight: 36 }}
              value={quantities[item.id] || ''}
              placeholder="0"
              onChange={(e) => setQty(item.id, e.target.value)}
            />
          </div>
        ))}
      </div>
    </Modal>
  );
}
