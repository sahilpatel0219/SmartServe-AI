import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { menu as menuApi } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import {
  Badge, Card, DataTable, ErrorState, Field, Loading, Modal, PageHeader, UploadPrompt, rupees,
} from '../components/ui';

const BLANK = {
  name: '', category: '', price: '', cost: '', description: '', is_available: true, recipe: [],
};

export default function Menu() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { isManager } = useAuth();
  const [category, setCategory] = useState('');
  const [editing, setEditing] = useState(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['menu', category],
    queryFn: () => menuApi.list(category),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['menu'] });

  const saveMutation = useMutation({
    mutationFn: (item) => (item.id ? menuApi.update(item.id, item) : menuApi.create(item)),
    onSuccess: () => { toast.success('Menu item saved.'); setEditing(null); invalidate(); },
    onError: (err) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: menuApi.remove,
    onSuccess: () => { toast.success('Item deleted.'); invalidate(); },
    onError: (err) => toast.error(err.message),
  });

  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isLoading || !data) return <Loading rows={4} />;

  const columns = [
    { key: 'name', label: 'Item' },
    { key: 'category', label: 'Category', render: (r) => r.category ? <Badge variant="neutral">{r.category}</Badge> : '—' },
    { key: 'price', label: 'Price', align: 'right', render: (r) => rupees(r.price) },
    { key: 'cost', label: 'Cost', align: 'right', render: (r) => rupees(r.cost) },
    {
      key: 'margin',
      label: 'Margin',
      align: 'right',
      render: (r) => {
        if (!r.price) return '—';
        const margin = ((r.price - (r.cost || 0)) / r.price) * 100;
        return <span className={margin < 30 ? 'text-warning' : 'text-success'}>{margin.toFixed(0)}%</span>;
      },
    },
    {
      key: 'recipe',
      label: 'Recipe',
      render: (r) => (r.recipe?.length ? `${r.recipe.length} ingredient(s)` : <span className="text-muted">Not mapped</span>),
    },
    {
      key: 'is_available',
      label: 'Status',
      render: (r) => <Badge variant={r.is_available ? 'success' : 'neutral'}>{r.is_available ? 'Available' : 'Hidden'}</Badge>,
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
              onClick={() => { if (window.confirm(`Delete "${r.name}"?`)) deleteMutation.mutate(r.id); }}
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
      <PageHeader title="Menu" subtitle="Items, pricing, and the recipes that drive inventory auto-deduction.">
        <button type="button" className="btn btn-primary" onClick={() => setEditing({ ...BLANK })}>
          <i className="bi bi-plus-lg" /> Add Item
        </button>
      </PageHeader>

      {!data.items.length && !category ? (
        <UploadPrompt title="No Menu Yet" desc="Upload your menu file, or add items manually to enable profitability analytics." />
      ) : (
        <>
          {data.categories?.length > 0 && (
            <div className="flex gap-2 flex-wrap mb-6">
              <button type="button" className={`btn btn-sm ${!category ? 'btn-primary' : 'btn-outline'}`} onClick={() => setCategory('')}>
                All
              </button>
              {data.categories.map((c) => (
                <button key={c} type="button" className={`btn btn-sm ${category === c ? 'btn-primary' : 'btn-outline'}`} onClick={() => setCategory(c)}>
                  {c}
                </button>
              ))}
            </div>
          )}

          <Card title={`${data.items.length} item(s)`}>
            <DataTable columns={columns} rows={data.items} empty="No items in this category." />
          </Card>
        </>
      )}

      {editing && (
        <MenuItemModal
          item={editing}
          categories={data.categories || []}
          busy={saveMutation.isPending}
          onClose={() => setEditing(null)}
          onSave={(item) => saveMutation.mutate(item)}
        />
      )}
    </>
  );
}

function MenuItemModal({ item, categories, onSave, onClose, busy }) {
  const [form, setForm] = useState({ ...item, recipe: item.recipe || [] });
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const setRecipeRow = (index, key, value) =>
    setForm((f) => {
      const recipe = [...f.recipe];
      recipe[index] = { ...recipe[index], [key]: value };
      return { ...f, recipe };
    });

  const addRow = () => setForm((f) => ({ ...f, recipe: [...f.recipe, { ingredient: '', quantity: '', unit: '' }] }));
  const removeRow = (index) => setForm((f) => ({ ...f, recipe: f.recipe.filter((_, i) => i !== index) }));

  return (
    <Modal
      title={item.id ? 'Edit menu item' : 'Add menu item'}
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
      <Field label="Item name">
        <input className="form-control" value={form.name || ''} onChange={set('name')} autoFocus />
      </Field>
      <Field label="Category">
        <input className="form-control" value={form.category || ''} onChange={set('category')} list="menu-categories" />
        <datalist id="menu-categories">
          {categories.map((c) => <option key={c} value={c} />)}
        </datalist>
      </Field>
      <div className="grid grid-2 gap-3">
        <Field label="Price (₹)">
          <input type="number" step="any" className="form-control" value={form.price ?? ''} onChange={set('price')} />
        </Field>
        <Field label="Cost (₹)">
          <input type="number" step="any" className="form-control" value={form.cost ?? ''} onChange={set('cost')} />
        </Field>
      </div>
      <Field label="Description">
        <textarea className="form-control" value={form.description || ''} onChange={set('description')} />
      </Field>
      <Field>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={Boolean(form.is_available)}
            onChange={(e) => setForm((f) => ({ ...f, is_available: e.target.checked }))}
          />
          Available for ordering
        </label>
      </Field>

      <hr className="divider" />
      <div className="flex justify-between items-center mb-4">
        <span className="fw-semi text-sm">Recipe</span>
        <button type="button" className="btn btn-sm btn-outline" onClick={addRow}>
          <i className="bi bi-plus" /> Ingredient
        </button>
      </div>
      <p className="form-text mb-4">
        Mapping ingredients here is what lets stock auto-deduct when this item sells.
      </p>
      {form.recipe.map((row, i) => (
        <div key={i} className="flex gap-2 items-end mb-2">
          <input
            className="form-control" placeholder="Ingredient" value={row.ingredient || ''}
            onChange={(e) => setRecipeRow(i, 'ingredient', e.target.value)}
          />
          <input
            className="form-control" style={{ maxWidth: 90 }} type="number" step="any" placeholder="Qty"
            value={row.quantity ?? ''} onChange={(e) => setRecipeRow(i, 'quantity', e.target.value)}
          />
          <input
            className="form-control" style={{ maxWidth: 90 }} placeholder="Unit"
            value={row.unit || ''} onChange={(e) => setRecipeRow(i, 'unit', e.target.value)}
          />
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => removeRow(i)} aria-label="Remove ingredient">
            <i className="bi bi-x-lg" />
          </button>
        </div>
      ))}
    </Modal>
  );
}
