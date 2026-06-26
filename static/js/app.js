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

  // Sync theme icon with current theme
  const icon = document.getElementById('themeIcon');
  const savedTheme = localStorage.getItem('ss_theme') || 'light';
  if (icon) icon.className = savedTheme === 'dark' ? 'bi bi-sun' : 'bi bi-moon';

  // Animate stat cards and content cards on page load
  document.querySelectorAll('.stat-card').forEach((card, i) => {
    card.style.animationDelay = `${i * 0.07}s`;
    card.classList.add('animate-in');
  });

  // Number counter animation for stat values
  document.querySelectorAll('.stat-value[data-count], .stat-card-value[data-count]').forEach(el => {
    animateCounter(el, parseInt(el.dataset.count));
  });

});

// ── Number counter animation ─────────────────────────────────
function animateCounter(el, target) {
  const start   = 0;
  const duration = 1200;
  const startTime = performance.now();
  const prefix  = el.dataset.prefix || '';
  const suffix  = el.dataset.suffix || '';

  function step(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    el.textContent = prefix + Math.floor(ease * target).toLocaleString('en-IN') + suffix;
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

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

// ── Theme (light / dark) ─────────────────────────────────────
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('ss_theme', theme);
  const icon = document.getElementById('themeIcon');
  if (icon) icon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon';
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'light';
  applyTheme(current === 'dark' ? 'light' : 'dark');
}

// Apply saved theme immediately (runs before DOMContentLoaded to avoid flash)
(function () {
  const saved = localStorage.getItem('ss_theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
})();

// ── Formatters ───────────────────────────────────────────────
function formatCurrency(val, currency = 'INR') {
  return new Intl.NumberFormat('en-IN', { style:'currency', currency, maximumFractionDigits:0 }).format(val);
}
function formatNumber(val) {
  return new Intl.NumberFormat('en-IN').format(val);
}
