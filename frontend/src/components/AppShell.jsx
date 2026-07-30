import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { notifications as notificationsApi } from '../api/endpoints';

/** Nav is grouped the same way the old Django sidebar was. */
const NAV_SECTIONS = [
  {
    label: 'Overview',
    items: [
      { to: '/dashboard', icon: 'bi-grid-1x2', label: 'Dashboard' },
      { to: '/analytics', icon: 'bi-bar-chart-line', label: 'Analytics' },
      { to: '/report', icon: 'bi-cpu', label: 'AI Report' },
    ],
  },
  {
    label: 'Operations',
    items: [
      { to: '/orders', icon: 'bi-receipt', label: 'Orders' },
      { to: '/menu', icon: 'bi-journal-text', label: 'Menu' },
      { to: '/inventory', icon: 'bi-box-seam', label: 'Inventory' },
    ],
  },
  {
    label: 'People',
    items: [
      { to: '/customers', icon: 'bi-people', label: 'Customers' },
      { to: '/staff', icon: 'bi-person-badge', label: 'Staff' },
      { to: '/suppliers', icon: 'bi-truck', label: 'Suppliers' },
    ],
  },
  {
    label: 'Tools',
    items: [
      { to: '/assistant', icon: 'bi-chat-dots', label: 'AI Assistant' },
      { to: '/upload', icon: 'bi-cloud-upload', label: 'Upload Data' },
      { to: '/reports', icon: 'bi-file-earmark-arrow-down', label: 'Reports' },
    ],
  },
];

export default function AppShell({ children }) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();

  // Close the mobile drawer on navigation.
  useEffect(() => setDrawerOpen(false), [location.pathname]);

  return (
    <>
      <Sidebar open={drawerOpen} />
      {drawerOpen && (
        <button
          type="button"
          className="sidebar-overlay active"
          aria-label="Close navigation"
          onClick={() => setDrawerOpen(false)}
        />
      )}
      <Topbar onMenuClick={() => setDrawerOpen((v) => !v)} />
      <main className="main-content">{children}</main>
    </>
  );
}

function Sidebar({ open }) {
  const { business } = useAuth();
  return (
    <aside className={`sidebar ${open ? 'open' : ''}`}>
      <div className="sidebar-logo">
        <div className="logo-mark">S</div>
        <div style={{ minWidth: 0 }}>
          <div className="logo-text">SmartServe AI</div>
          <div className="logo-sub truncate">{business?.name || 'No workspace'}</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV_SECTIONS.map((section) => (
          <div className="nav-section" key={section.label}>
            <div className="nav-section-label">{section.label}</div>
            {section.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              >
                <i className={`bi ${item.icon}`} />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <NavLink to="/settings" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <i className="bi bi-gear" />
          <span>Settings</span>
        </NavLink>
      </div>
    </aside>
  );
}

function Topbar({ onMenuClick }) {
  const { user, business, role, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  const { data: notifData } = useQuery({
    queryKey: ['notifications'],
    queryFn: notificationsApi.list,
    // Alerts are regenerated server-side on read; don't hammer it.
    staleTime: 120_000,
  });
  const unread = notifData?.unread || 0;

  useEffect(() => {
    const onClickAway = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener('mousedown', onClickAway);
    return () => document.removeEventListener('mousedown', onClickAway);
  }, []);

  const initials = `${user?.first_name?.[0] || ''}${user?.last_name?.[0] || ''}`.toUpperCase() || 'U';

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button type="button" className="topbar-icon-btn shell-menu-btn" onClick={onMenuClick} aria-label="Toggle navigation">
          <i className="bi bi-list" />
        </button>
        <span className="topbar-title truncate">{business?.name || 'SmartServe AI'}</span>
      </div>

      <div className="topbar-right">
        <button
          type="button"
          className="topbar-icon-btn"
          onClick={toggleTheme}
          aria-label={`Change theme (currently ${theme})`}
          title="Change Theme"
        >
          <i className={`bi ${theme === 'dark' ? 'bi-sun' : 'bi-moon-stars'}`} />
        </button>

        <Link to="/notifications" className="topbar-icon-btn" aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`}>
          <i className="bi bi-bell" />
          {unread > 0 && <span className="notif-dot" />}
        </Link>

        <div style={{ position: 'relative' }} ref={menuRef}>
          <button type="button" className="topbar-avatar" onClick={() => setMenuOpen((v) => !v)} aria-label="Account menu">
            {initials}
          </button>
          {menuOpen && (
            <div className="menu-panel">
              <div className="menu-label">
                {user?.first_name} {user?.last_name}
              </div>
              <div className="menu-label" style={{ paddingTop: 0 }}>
                {role}
              </div>
              <hr className="divider" style={{ margin: '8px 0' }} />
              <button type="button" className="menu-item" onClick={() => { setMenuOpen(false); navigate('/settings'); }}>
                <i className="bi bi-person" /> Profile & settings
              </button>
              <button type="button" className="menu-item" onClick={() => { logout(); navigate('/login'); }}>
                <i className="bi bi-box-arrow-right" /> Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
