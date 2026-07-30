import { Navigate, Route, Routes, useLocation } from 'react-router-dom';

import AppShell from './components/AppShell';
import ErrorBoundary from './components/ErrorBoundary';
import Toasts from './components/Toasts';
import { useAuth } from './context/AuthContext';

import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import CreateBusiness from './pages/CreateBusiness';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Menu from './pages/Menu';
import Inventory from './pages/Inventory';
import Orders from './pages/Orders';
import Customers from './pages/Customers';
import Staff from './pages/Staff';
import Suppliers from './pages/Suppliers';
import Analytics from './pages/Analytics';
import Report from './pages/Report';
import Reports from './pages/Reports';
import Assistant from './pages/Assistant';
import NotificationsPage from './pages/Notifications';
import Settings from './pages/Settings';
import NotFound from './pages/NotFound';

function FullPageSpinner() {
  return (
    <div className="auth-page">
      <span className="spinner" aria-label="Loading" />
    </div>
  );
}

/** Redirects to /login when there is no valid session. */
function Protected({ children, requireBusiness = true }) {
  const { isAuthenticated, hasBusiness, loading } = useAuth();
  const location = useLocation();

  if (loading) return <FullPageSpinner />;
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />;
  // A signed-in user with no workspace yet can only go to onboarding.
  if (requireBusiness && !hasBusiness) return <Navigate to="/onboarding" replace />;

  return (
    <AppShell>
      <ErrorBoundary>{children}</ErrorBoundary>
    </AppShell>
  );
}

/** Keeps signed-in users away from the login/register screens. */
function PublicOnly({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <FullPageSpinner />;
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  return children;
}

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<PublicOnly><Landing /></PublicOnly>} />
        <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
        <Route path="/register" element={<PublicOnly><Register /></PublicOnly>} />

        {/* Onboarding renders outside the shell — there is no workspace yet. */}
        <Route path="/onboarding" element={<CreateBusiness />} />

        <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
        <Route path="/analytics" element={<Protected><Analytics /></Protected>} />
        <Route path="/report" element={<Protected><Report /></Protected>} />
        <Route path="/orders" element={<Protected><Orders /></Protected>} />
        <Route path="/menu" element={<Protected><Menu /></Protected>} />
        <Route path="/inventory" element={<Protected><Inventory /></Protected>} />
        <Route path="/customers" element={<Protected><Customers /></Protected>} />
        <Route path="/staff" element={<Protected><Staff /></Protected>} />
        <Route path="/suppliers" element={<Protected><Suppliers /></Protected>} />
        <Route path="/assistant" element={<Protected><Assistant /></Protected>} />
        <Route path="/upload" element={<Protected><Upload /></Protected>} />
        <Route path="/reports" element={<Protected><Reports /></Protected>} />
        <Route path="/notifications" element={<Protected><NotificationsPage /></Protected>} />
        <Route path="/settings" element={<Protected><Settings /></Protected>} />

        <Route path="*" element={<NotFound />} />
      </Routes>
      <Toasts />
    </>
  );
}
