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

// ── Theme ────────────────────────────────────────────────────
// Dark is the default and only built theme in the Noir Crimson system. The
// pre-paint inline script in base.html applies data-theme before first paint;
// this re-asserts it as a safety net. A light theme is structurally possible
// later (tokens are theme-able) but is intentionally not built yet.
(function () {
  const saved = localStorage.getItem('ss_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
})();

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
