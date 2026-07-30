/**
 * Every backend call the app can make, in one place.
 * See API.md at the repo root for the full request/response contract.
 */
import client, { BASE_URL, tokenStore, businessStore } from './client';

const unwrap = (promise) => promise.then((r) => r.data);

// ── Auth ──────────────────────────────────────────────────────────────────────
export const auth = {
  register: (payload) => unwrap(client.post('/auth/register/', payload)),
  login: (email, password) => unwrap(client.post('/auth/login/', { email, password })),
  me: () => unwrap(client.get('/auth/me/')),
  updateProfile: (payload) => unwrap(client.patch('/auth/me/', payload)),
  loginHistory: () => unwrap(client.get('/auth/login-history/')),
};

// ── Businesses ────────────────────────────────────────────────────────────────
export const businesses = {
  list: () => unwrap(client.get('/businesses/')),
  create: (payload) => unwrap(client.post('/businesses/', payload)),
  get: (id) => unwrap(client.get(`/businesses/${id}/`)),
  update: (id, payload) => unwrap(client.patch(`/businesses/${id}/`, payload)),
  activate: (id) => unwrap(client.post(`/businesses/${id}/activate/`)),
};

// ── Dashboard ─────────────────────────────────────────────────────────────────
export const dashboard = {
  get: () => unwrap(client.get('/dashboard/')),
};

// ── Data upload ───────────────────────────────────────────────────────────────
export const uploads = {
  center: () => unwrap(client.get('/uploads/')),
  /** Step 1 — validate a CSV/XLSX and get a preview + upload_token. */
  validate: (uploadType, file) => {
    const form = new FormData();
    form.append('file', file);
    return unwrap(
      client.post(`/uploads/${uploadType}/`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }),
    );
  },
  /** Step 2 — commit the previously validated rows. */
  confirm: (uploadType, uploadToken) =>
    unwrap(client.post(`/uploads/${uploadType}/`, { confirm: true, upload_token: uploadToken })),
  templateUrl: (uploadType) => `${BASE_URL}/uploads/${uploadType}/template/`,
};

// ── Menu ──────────────────────────────────────────────────────────────────────
export const menu = {
  list: (category) => unwrap(client.get('/menu/', { params: category ? { category } : {} })),
  create: (payload) => unwrap(client.post('/menu/', payload)),
  get: (id) => unwrap(client.get(`/menu/${id}/`)),
  update: (id, payload) => unwrap(client.patch(`/menu/${id}/`, payload)),
  remove: (id) => unwrap(client.delete(`/menu/${id}/`)),
};

// ── Inventory ─────────────────────────────────────────────────────────────────
export const inventory = {
  list: () => unwrap(client.get('/inventory/')),
  create: (payload) => unwrap(client.post('/inventory/', payload)),
  update: (id, payload) => unwrap(client.patch(`/inventory/${id}/`, payload)),
  remove: (id) => unwrap(client.delete(`/inventory/${id}/`)),
};

// ── Orders ────────────────────────────────────────────────────────────────────
export const orders = {
  list: (status) => unwrap(client.get('/orders/', { params: status ? { status } : {} })),
  create: (payload) => unwrap(client.post('/orders/', payload)),
  get: (id) => unwrap(client.get(`/orders/${id}/`)),
  setStatus: (id, status) => unwrap(client.patch(`/orders/${id}/status/`, { status })),
};

// ── Customers ─────────────────────────────────────────────────────────────────
export const customers = {
  list: (segment) => unwrap(client.get('/customers/', { params: segment ? { segment } : {} })),
  create: (payload) => unwrap(client.post('/customers/', payload)),
  get: (id) => unwrap(client.get(`/customers/${id}/`)),
  update: (id, payload) => unwrap(client.patch(`/customers/${id}/`, payload)),
};

// ── Staff ─────────────────────────────────────────────────────────────────────
export const staff = {
  list: () => unwrap(client.get('/staff/')),
  create: (payload) => unwrap(client.post('/staff/', payload)),
  update: (id, payload) => unwrap(client.patch(`/staff/${id}/`, payload)),
  remove: (id) => unwrap(client.delete(`/staff/${id}/`)),
  attendance: () => unwrap(client.get('/staff/attendance/')),
  markAttendance: (statuses) => unwrap(client.post('/staff/attendance/', { statuses })),
};

// ── Suppliers ─────────────────────────────────────────────────────────────────
export const suppliers = {
  list: () => unwrap(client.get('/suppliers/')),
  create: (payload) => unwrap(client.post('/suppliers/', payload)),
  update: (id, payload) => unwrap(client.patch(`/suppliers/${id}/`, payload)),
  remove: (id) => unwrap(client.delete(`/suppliers/${id}/`)),
  purchaseOrders: () => unwrap(client.get('/suppliers/purchase-orders/')),
  createPurchaseOrder: (payload) => unwrap(client.post('/suppliers/purchase-orders/', payload)),
};

// ── Analytics ─────────────────────────────────────────────────────────────────
export const analytics = {
  get: (period = '30') => unwrap(client.get('/analytics/', { params: { period } })),
};

// ── ML / forecasting ──────────────────────────────────────────────────────────
export const ml = {
  status: () => unwrap(client.get('/ml/status/')),
  run: () => unwrap(client.post('/ml/run/')),
  results: () => unwrap(client.get('/ml/results/')),
  insights: () => unwrap(client.get('/ml/insights/')),
};

// ── Assistant ─────────────────────────────────────────────────────────────────
export const assistant = {
  status: () => unwrap(client.get('/assistant/status/')),
  chat: (message) => unwrap(client.post('/assistant/chat/', { message })),
  feedback: (payload) => unwrap(client.post('/assistant/feedback/', payload)),
};

// ── Reports ───────────────────────────────────────────────────────────────────
export const reports = {
  status: () => unwrap(client.get('/reports/status/')),
  /**
   * Report exports are authenticated binary downloads, so they can't be a plain
   * <a href> (no Authorization header). Fetch as a blob, then trigger a save.
   */
  download: async (reportType, fmt, period) => {
    const response = await client.get(`/reports/export/${reportType}/${fmt}/`, {
      params: period ? { period } : {},
      responseType: 'blob',
    });
    const ext = fmt === 'excel' ? 'xlsx' : 'pdf';
    const url = URL.createObjectURL(response.data);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${reportType}_report.${ext}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },
};

// ── Notifications ─────────────────────────────────────────────────────────────
export const notifications = {
  list: () => unwrap(client.get('/notifications/')),
  markRead: (id) => unwrap(client.post(`/notifications/${id}/read/`)),
  markAllRead: () => unwrap(client.post('/notifications/mark-all-read/')),
};

export { tokenStore, businessStore };
