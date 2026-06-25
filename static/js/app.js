/* SmartServe AI — global utilities */

// Sidebar toggle (mobile)
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

// Show a toast notification
function showToast(message, type = 'success', duration = 4000) {
  const container = document.getElementById('toastContainer');
  const icons = { success: 'check-circle', danger: 'exclamation-circle', warning: 'exclamation-triangle', info: 'info-circle' };
  const colors = { success: 'var(--color-success)', danger: 'var(--color-danger)', warning: 'var(--color-warning)', info: 'var(--color-info)' };

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `
    <i class="bi bi-${icons[type] || 'info-circle'}" style="color:${colors[type]};font-size:1.1rem;flex-shrink:0;"></i>
    <span style="font-size:var(--text-sm);flex:1;">${message}</span>
    <button onclick="this.parentElement.remove()" style="background:none;border:none;cursor:pointer;color:var(--color-muted);padding:0;line-height:1;">
      <i class="bi bi-x"></i>
    </button>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}

// Confirm dialog helper
function confirmAction(message, callback) {
  if (window.confirm(message)) callback();
}

// Auto-dismiss Django messages after 5s
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.alert').forEach(el => {
    setTimeout(() => el.style.opacity = '0', 4500);
    setTimeout(() => el.remove(), 5000);
    el.style.transition = 'opacity 0.5s';
  });

  // Dropzone drag-and-drop highlight
  document.querySelectorAll('.dropzone').forEach(zone => {
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragging'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragging'));
    zone.addEventListener('drop', e => { e.preventDefault(); zone.classList.remove('dragging'); });
    zone.addEventListener('click', () => zone.querySelector('input[type=file]')?.click());
  });
});

// Currency formatter (INR)
function formatCurrency(val, currency = 'INR') {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency, maximumFractionDigits: 0 }).format(val);
}

// Number with commas
function formatNumber(val) {
  return new Intl.NumberFormat('en-IN').format(val);
}
