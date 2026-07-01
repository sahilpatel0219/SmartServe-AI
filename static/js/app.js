/* SmartServe AI — global utilities v2 */

// ── Sidebar toggle (mobile) ──────────────────────────────────
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  const isOpen  = sidebar.classList.contains('open');
  sidebar.classList.toggle('open', !isOpen);
  if (overlay) overlay.classList.toggle('active', !isOpen);
  document.body.style.overflow = isOpen ? '' : 'hidden';
}

// Close sidebar on Escape key
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && document.getElementById('sidebar')?.classList.contains('open')) {
    toggleSidebar();
  }
});

// ── Toast notifications ──────────────────────────────────────
function showToast(message, type = 'success', duration = 4500) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const icons = {
    success: 'check-circle-fill',
    danger:  'x-circle-fill',
    warning: 'exclamation-triangle-fill',
    info:    'info-circle-fill',
  };

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.style.cssText = 'opacity:0;transform:translateX(20px);transition:opacity .25s,transform .25s;';
  toast.innerHTML = `
    <i class="bi bi-${icons[type] || 'info-circle-fill'}" style="font-size:1rem;flex-shrink:0;opacity:.85;"></i>
    <span style="flex:1;line-height:1.4;">${message}</span>
    <button onclick="this.parentElement.remove()"
      style="background:none;border:none;cursor:pointer;color:rgba(255,255,255,.6);padding:0;line-height:1;font-size:1.1rem;">
      <i class="bi bi-x"></i>
    </button>`;

  container.appendChild(toast);
  requestAnimationFrame(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateX(0)';
  });

  const timer = setTimeout(() => removeToast(toast), duration);
  toast.querySelector('button').addEventListener('click', () => clearTimeout(timer));
}

function removeToast(toast) {
  toast.style.opacity = '0';
  toast.style.transform = 'translateX(20px)';
  setTimeout(() => toast.remove(), 300);
}

// ── Confirm dialog ───────────────────────────────────────────
function confirmAction(message, callback) {
  if (window.confirm(message)) callback();
}

// ── DOMContentLoaded ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {

  // Convert Django flash messages to toasts
  document.querySelectorAll('.django-message[data-type]').forEach(el => {
    showToast(el.dataset.text, el.dataset.type);
    el.remove();
  });

  // Auto-dismiss .alert banners (keep them visible longer)
  document.querySelectorAll('.alert').forEach(el => {
    el.style.transition = 'opacity .5s,transform .5s';
    setTimeout(() => { el.style.opacity = '0'; el.style.transform = 'translateY(-4px)'; }, 5000);
    setTimeout(() => el.remove(), 5500);
  });

  // Dropzone drag-and-drop (click handled natively by <label> wrapper)
  document.querySelectorAll('.dropzone').forEach(zone => {
    zone.addEventListener('dragover',  e => { e.preventDefault(); zone.classList.add('dragging'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragging'));
    zone.addEventListener('drop', e => {
      e.preventDefault(); zone.classList.remove('dragging');
      const input = zone.querySelector('input[type=file]');
      if (input && e.dataTransfer.files.length) {
        const dt = new DataTransfer();
        dt.items.add(e.dataTransfer.files[0]);
        input.files = dt.files;
        input.dispatchEvent(new Event('change'));
      }
    });
  });

  // Active nav link highlight based on URL
  const path = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(link => {
    if (link.href && link.href !== window.location.origin + '/') {
      const linkPath = new URL(link.href).pathname;
      if (path.startsWith(linkPath)) link.classList.add('active');
    }
  });

  // Keep the active item visible: if the sidebar nav is scrollable, bring the
  // active link into view without scrolling the whole page (fixes the nav
  // appearing to "jump to the top" after navigating to a bottom item).
  const activeLink = document.querySelector('.sidebar-nav .nav-link.active');
  if (activeLink) activeLink.scrollIntoView({ block: 'nearest', inline: 'nearest' });

  // Sync the "Reduce motion" toggle label/icon with saved preference
  syncMotionToggle();

  // Sync the theme toggle icon/ARIA with the current theme
  syncThemeToggle();

  // Enable smooth theme color-transitions only AFTER first paint, so switching
  // themes animates but the initial load does not flash a transition.
  requestAnimationFrame(() => document.documentElement.classList.add('theme-ready'));

});

// ── Upload file guard ────────────────────────────────────────
function checkFile(key) {
  const input = document.getElementById('file_' + key);
  if (!input || !input.files || input.files.length === 0) {
    showToast('Please select a file first — click the upload area to browse.', 'warning');
    input && input.click();
    return false;
  }
  return true;
}

// ── Theme (dark ⇄ light) ─────────────────────────────────────
// Dark is the default; light uses an indigo brand. The pre-paint script in
// base.html sets data-theme before first paint (saved choice → OS preference →
// dark). Storage key: 'smartserve-theme'.
const THEME_KEY = 'smartserve-theme';

function currentTheme() {
  return document.documentElement.getAttribute('data-theme') || 'dark';
}

// Reflect the active theme on the toggle button's icon + ARIA state.
function syncThemeToggle() {
  const theme = currentTheme();
  const icon = document.getElementById('themeIcon');
  const btn  = document.getElementById('themeToggle');
  // Show the icon of the theme you'd switch TO: sun in dark, moon in light.
  if (icon) icon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
  if (btn) {
    btn.setAttribute('aria-pressed', theme === 'light' ? 'true' : 'false');
    btn.setAttribute('title', theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme');
  }
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  try { localStorage.setItem(THEME_KEY, theme); } catch (e) {}
  syncThemeToggle();
  // Re-theme JS-driven visuals that bake colors at render (charts).
  if (typeof window.applyChartTheme === 'function') window.applyChartTheme();
}

function toggleTheme() {
  applyTheme(currentTheme() === 'dark' ? 'light' : 'dark');
}

// ── Chart theming ────────────────────────────────────────────
// Chart.js bakes colors at render time, so charts must be re-themed on toggle.
// Templates register their chart instances (and tag each dataset with a
// _ssRole of 'brand' | 'info' and _ssFill true/false) via SmartServe.registerChart.
// The registry itself is initialized early in base.html <head> so content chart
// scripts (which run before this file) can register; guard with || so we never
// clobber already-registered charts.
window.SmartServe = window.SmartServe || {};
SmartServe.charts = SmartServe.charts || [];
SmartServe.token = SmartServe.token || function (name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback || '';
};
SmartServe.registerChart = SmartServe.registerChart || function (chart) {
  if (chart) SmartServe.charts.push(chart);
  return chart;
};

window.applyChartTheme = function () {
  if (typeof Chart === 'undefined') return;
  const t = SmartServe.token;
  const font  = t('--text-muted', '#A1A1AA');
  const grid  = t('--hairline', 'rgba(255,255,255,.07)');
  const brand = t('--brand', '#E5392E');
  const brandTint = t('--brand-tint', 'rgba(229,57,46,.12)');
  const info  = t('--info', '#60A5FA');
  const infoTint = t('--info-tint', 'rgba(96,165,250,.14)');

  Chart.defaults.color = font;
  Chart.defaults.font.family = t('--font-body', 'Inter, sans-serif');

  SmartServe.charts.forEach(ch => {
    if (!ch || !ch.options) return;
    const scales = ch.options.scales || {};
    Object.keys(scales).forEach(k => {
      const s = scales[k];
      if (s.grid && s.grid.display !== false) s.grid.color = grid;
      if (s.ticks) s.ticks.color = font;
    });
    const lg = ch.options.plugins && ch.options.plugins.legend;
    if (lg && lg.labels) lg.labels.color = font;
    (ch.data.datasets || []).forEach(ds => {
      if (ds._ssRole === 'brand') {
        ds.borderColor = brand;
        ds.backgroundColor = ds._ssFill ? brandTint : brand;
      } else if (ds._ssRole === 'info') {
        ds.borderColor = info;
        ds.backgroundColor = ds._ssFill ? infoTint : info;
      }
    });
    ch.update('none');
  });
};

// ── Motion preference (user toggle to reduce interface motion) ───────────────
function syncMotionToggle() {
  const off   = localStorage.getItem('ss_motion') === 'off';
  const icon  = document.getElementById('motionIcon');
  const label = document.getElementById('motionLabel');
  if (icon)  icon.className = off ? 'bi bi-play-circle' : 'bi bi-stars';
  if (label) label.textContent = off ? 'Enable motion' : 'Reduce motion';
}

function toggleMotion() {
  const off = localStorage.getItem('ss_motion') === 'off';
  if (off) {
    localStorage.removeItem('ss_motion');
    document.documentElement.classList.remove('no-motion');
  } else {
    localStorage.setItem('ss_motion', 'off');
    document.documentElement.classList.add('no-motion');
  }
  syncMotionToggle();
}

// ── Formatters ───────────────────────────────────────────────
function formatCurrency(val, currency = 'INR') {
  return new Intl.NumberFormat('en-IN', { style:'currency', currency, maximumFractionDigits:0 }).format(val);
}
function formatNumber(val) {
  return new Intl.NumberFormat('en-IN').format(val);
}
