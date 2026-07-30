/**
 * The ONLY module that talks to the backend.
 *
 * Responsibilities:
 *  - attach the JWT access token to every request
 *  - attach the active business id (X-Business-Id) for tenant scoping
 *  - refresh the access token once on a 401 and replay the original request
 *  - normalize backend errors into a single Error with a readable .message
 *
 * Components never import axios directly — they use the helpers in endpoints.js.
 */
import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';

const ACCESS_KEY = 'smartserve-access';
const REFRESH_KEY = 'smartserve-refresh';
const BUSINESS_KEY = 'smartserve-business-id';

export const tokenStore = {
  getAccess: () => localStorage.getItem(ACCESS_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set: ({ access, refresh }) => {
    if (access) localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(BUSINESS_KEY);
  },
};

export const businessStore = {
  get: () => localStorage.getItem(BUSINESS_KEY),
  set: (id) => (id ? localStorage.setItem(BUSINESS_KEY, String(id)) : localStorage.removeItem(BUSINESS_KEY)),
  clear: () => localStorage.removeItem(BUSINESS_KEY),
};

const client = axios.create({ baseURL: BASE_URL });

client.interceptors.request.use((config) => {
  const token = tokenStore.getAccess();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  const businessId = businessStore.get();
  if (businessId) config.headers['X-Business-Id'] = businessId;
  return config;
});

/** Extract a human-readable message out of DRF's various error shapes. */
function readError(error) {
  const data = error.response?.data;
  if (!data) return error.message || 'Network error — is the backend running?';
  if (typeof data === 'string') return data;
  if (data.error) return data.error;
  if (data.detail) return data.detail;
  // serializer field errors: {email: ["already in use"]}
  const first = Object.entries(data)[0];
  if (first) {
    const [field, msgs] = first;
    const text = Array.isArray(msgs) ? msgs[0] : String(msgs);
    return field === 'non_field_errors' ? text : `${field}: ${text}`;
  }
  return 'Something went wrong.';
}

// ── Single-flight token refresh ────────────────────────────────────────────────
let refreshing = null;

async function refreshAccessToken() {
  const refresh = tokenStore.getRefresh();
  if (!refresh) throw new Error('Session expired. Please sign in again.');
  // Bare axios so this request doesn't re-enter the interceptors below.
  const { data } = await axios.post(`${BASE_URL}/auth/refresh/`, { refresh });
  tokenStore.set({ access: data.access });
  return data.access;
}

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const isAuthCall = original?.url?.includes('/auth/login') || original?.url?.includes('/auth/refresh');

    if (error.response?.status === 401 && !original._retried && !isAuthCall) {
      original._retried = true;
      try {
        refreshing = refreshing || refreshAccessToken();
        const access = await refreshing;
        refreshing = null;
        original.headers.Authorization = `Bearer ${access}`;
        return client(original);
      } catch (refreshError) {
        refreshing = null;
        tokenStore.clear();
        // Let the AuthContext react to a hard logout.
        window.dispatchEvent(new Event('smartserve:session-expired'));
        return Promise.reject(new Error('Session expired. Please sign in again.'));
      }
    }

    const normalized = new Error(readError(error));
    normalized.status = error.response?.status;
    normalized.data = error.response?.data;
    return Promise.reject(normalized);
  },
);

export default client;
export { BASE_URL };
