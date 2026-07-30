import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { inventory as inventoryApi } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import {
  Badge, Card, DataTable, ErrorState, Field, Loading, Modal, PageHeader, StatCard, UploadPrompt, rupees,
} from '../components/ui';

const BLANK = {
  item_name: '', quantity: '', unit: '', cost_per_unit: '', reorder_level: '',
  expiry_date: '', category: '', supplier: '',
};

export default function Inventory() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { isManager } = useAuth();
  const [editing, setEditing] = useState(null); // item object or BLANK

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['inventory'],
    queryFn: inventoryApi.list,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['inventory'] });
    queryClient.invalidateQueries({ queryKey: ['dashboard'] });
  };

  const saveMutation = useMutation({
    mutationFn: (item) => (item.id ? inventoryApi.update(item.id, item) : inventoryApi.create(item)),
    onSuccess: () => {
      toast.success('Inventory saved.');
      setEditing(null);
      invalidate();
    },
    onError: (err) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: inventoryApi.remove,
    onSuccess: () => {
      toast.success('Item removed.');
      invalidate();
    },
    onError: (err) => toast.error(err.message),
  });

  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isLoading || !data) return <Loading rows={4} />;

  const columns = [
    { key: 'item_name', label: 'Item' },
    {
      key: 'quantity',
      label: 'Stock',
      align: 'right',
      render: (r) => (
        <span className={r.low_stock ? 'text-warning fw-semi' : ''}>
          {r.quantity} {r.unit}
        </span>
      ),
    },
    { key: 'cost_per_unit', label: 'Cost/unit', align: 'right', render: (r) => rupees(r.cost_per_unit) },
    { key: 'reorder_level', label: 'Reorder at', align: 'right' },
    {
      key: 'expiry',
      label: 'Expiry',
      render: (r) => {
        if (!r.expiry_date) return <span className="text-muted">—</span>;
        if (r.days_to_expiry === null) return r.expiry_date;
        if (r.days_to_expiry < 0) return <Badge variant="danger">Expired</Badge>;
        if (r.expiring_soon) return <Badge variant="warning">{r.days_to_expiry}d left</Badge>;
        return <span className="text-muted">{r.expiry_date}</span>;
      },
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
              onClick={() => {
                if (window.confirm(`Remove "${r.item_name}" from inventory?`)) deleteMutation.mutate(r.id);
              }}
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
      <PageHeader title="Inventory" subtitle="Stock levels, costs, and expiry — auto-deducted as orders are placed.">
        <button type="button" className="btn btn-primary" onClick={() => setEditing({ ...BLANK })}>
          <i className="bi bi-plus-lg" /> Add Stock
        </button>
      </PageHeader>

      {!data.items.length ? (
        <UploadPrompt
          title="No Inventory Yet"
          desc="Upload your inventory file, or add items one at a time to start tracking stock, costs, and expiry."
        />
      ) : (
        <>
          <div className="stat-grid mb-6">
            <StatCard label="Items Tracked" value={data.items.length} icon="bi-box-seam" tone="info" />
            <StatCard label="Low Stock" value={data.low_stock_count} icon="bi-exclamation-triangle" tone="warning" />
            <StatCard label="Expiring Soon" value={data.expiring_count} icon="bi-hourglass-split" tone="danger" />
          </div>

          <Card title="All stock">
            <DataTable columns={columns} rows={data.items} />
          </Card>
        </>
      )}

      {editing && (
        <StockModal
          item={editing}
          busy={saveMutation.isPending}
          onClose={() => setEditing(null)}
          onSave={(item) => saveMutation.mutate(item)}
        />
      )}
    </>
  );
}

function StockModal({ item, onSave, onClose, busy }) {
  const [form, setForm] = useState(item);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  return (
    <Modal
      title={item.id ? 'Edit stock item' : 'Add stock'}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn btn-outline" onClick={onClose} disabled={busy}>Cancel</button>
          <button type="button" className="btn btn-primary" onClick={() => onSave(form)} disabled={busy || !form.item_name?.trim()}>
            {busy ? <span className="spinner" /> : 'Save'}
          </button>
        </>
      }
    >
      <Field label="Item name">
        <input className="form-control" value={form.item_name || ''} onChange={set('item_name')} autoFocus />
      </Field>
      <div className="grid grid-2 gap-3">
        <Field label="Quantity">
          <input type="number" step="any" className="form-control" value={form.quantity ?? ''} onChange={set('quantity')} />
        </Field>
        <Field label="Unit" hint="kg, litre, piece…">
          <input className="form-control" value={form.unit || ''} onChange={set('unit')} />
        </Field>
      </div>
      <div className="grid grid-2 gap-3">
        <Field label="Cost per unit (₹)">
          <input type="number" step="any" className="form-control" value={form.cost_per_unit ?? ''} onChange={set('cost_per_unit')} />
        </Field>
        <Field label="Reorder level">
          <input type="number" step="any" className="form-control" value={form.reorder_level ?? ''} onChange={set('reorder_level')} />
        </Field>
      </div>
      <div className="grid grid-2 gap-3">
        <Field label="Expiry date">
          <input type="date" className="form-control" value={form.expiry_date || ''} onChange={set('expiry_date')} />
        </Field>
        <Field label="Category">
          <input className="form-control" value={form.category || ''} onChange={set('category')} />
        </Field>
      </div>
      {!item.id && (
        <p className="form-text">
          If an item with this name already exists, its stock will be updated instead of duplicated.
        </p>
      )}
    </Modal>
  );
}
