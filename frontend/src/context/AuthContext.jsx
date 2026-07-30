/**
 * Auth + active-business state.
 *
 * The role here is used ONLY to hide controls in the UI. Every permission is
 * re-checked server-side, so hiding a button is a convenience, never a security
 * boundary.
 */
import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { auth, tokenStore, businessStore } from '../api/endpoints';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [membership, setMembership] = useState(null);
  const [memberships, setMemberships] = useState([]);
  const [loading, setLoading] = useState(true);

  const clearSession = useCallback(() => {
    tokenStore.clear();
    setUser(null);
    setMembership(null);
    setMemberships([]);
  }, []);

  const loadMe = useCallback(async () => {
    const data = await auth.me();
    setUser(data.user);
    setMembership(data.active_membership);
    setMemberships(data.memberships || []);
    // Pin the resolved business so later requests carry X-Business-Id explicitly.
    if (data.active_membership?.business?.id) {
      businessStore.set(data.active_membership.business.id);
    }
    return data;
  }, []);

  // Restore a session on first load if a token is present.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!tokenStore.getAccess()) {
        setLoading(false);
        return;
      }
      try {
        await loadMe();
      } catch {
        if (!cancelled) clearSession();
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadMe, clearSession]);

  // A failed token refresh in the API layer means a hard logout.
  useEffect(() => {
    const onExpired = () => clearSession();
    window.addEventListener('smartserve:session-expired', onExpired);
    return () => window.removeEventListener('smartserve:session-expired', onExpired);
  }, [clearSession]);

  const login = useCallback(
    async (email, password) => {
      const data = await auth.login(email, password);
      tokenStore.set({ access: data.access, refresh: data.refresh });
      return loadMe();
    },
    [loadMe],
  );

  const register = useCallback(
    async (payload) => {
      const data = await auth.register(payload);
      tokenStore.set({ access: data.access, refresh: data.refresh });
      return loadMe();
    },
    [loadMe],
  );

  const logout = useCallback(() => clearSession(), [clearSession]);

  const switchBusiness = useCallback(
    async (businessId) => {
      businessStore.set(businessId);
      return loadMe();
    },
    [loadMe],
  );

  const role = membership?.role || null;

  const value = {
    user,
    membership,
    memberships,
    business: membership?.business || null,
    role,
    isManager: role === 'owner' || role === 'manager',
    isOwner: role === 'owner',
    isAuthenticated: Boolean(user),
    hasBusiness: Boolean(membership),
    loading,
    login,
    register,
    logout,
    switchBusiness,
    refresh: loadMe,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
