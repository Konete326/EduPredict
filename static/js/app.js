(function () {
  const THEME_KEY = 'edupredict_theme';
  let activeSubmitHandler = null;
  const byId = function (id) { return document.getElementById(id); };

  const TOAST_STYLES = {
    success: { border: 'var(--status-success)', icon: 'fa-solid fa-circle-check', color: 'var(--status-success)' },
    warning: { border: 'var(--status-warning)', icon: 'fa-solid fa-triangle-exclamation', color: 'var(--status-warning)' },
    danger: { border: 'var(--status-danger)', icon: 'fa-solid fa-circle-exclamation', color: 'var(--status-danger)' },
    error: { border: 'var(--status-danger)', icon: 'fa-solid fa-circle-exclamation', color: 'var(--status-danger)' },
    info: { border: 'var(--accent-primary)', icon: 'fa-solid fa-circle-info', color: 'var(--accent-primary)' }
  };

  function syncBodyScrollLock() {
    const confirmModal = byId('confirm-modal');
    const formModal = byId('form-modal');
    const drawer = byId('mobile-sidebar-drawer');
    const modalOpen = (confirmModal && !confirmModal.classList.contains('hidden')) || (formModal && !formModal.classList.contains('hidden'));
    const drawerOpen = drawer && !drawer.classList.contains('-translate-x-full');
    document.body.classList.toggle('modal-open', Boolean(modalOpen));
    document.body.classList.toggle('drawer-open', Boolean(drawerOpen));
  }

  function setModalOpen(modal, open) {
    if (!modal) return;
    modal.classList.toggle('hidden', !open);
    if (modal.classList.contains('items-center') || modal.classList.contains('justify-center')) {
      modal.classList.toggle('flex', open);
    }
    modal.setAttribute('aria-hidden', open ? 'false' : 'true');
    syncBodyScrollLock();
  }

  function openConfirmModal(options) {
    const opts = options || {};
    const modal = byId('confirm-modal');
    const titleEl = byId('confirm-modal-title');
    const messageEl = byId('confirm-modal-message');
    const formEl = byId('confirm-modal-form');
    if (!modal || !titleEl || !messageEl || !formEl) return;
    titleEl.textContent = opts.title || 'Confirm Action';
    messageEl.textContent = opts.message || 'Are you sure you want to continue?';
    formEl.setAttribute('action', opts.onConfirmUrl || '');
    const submitBtn = formEl.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.textContent = opts.confirmText || 'Confirm';
    setModalOpen(modal, true);
  }

  function closeConfirmModal() {
    setModalOpen(byId('confirm-modal'), false);
  }

  function createFieldNode(field) {
    const wrapper = document.createElement('div');
    wrapper.className = 'space-y-1.5';
    const fieldId = 'modal-field-' + (field.name || Math.random().toString(36).slice(2, 8));
    const label = document.createElement('label');
    label.setAttribute('for', fieldId);
    label.className = 'block text-sm font-medium text-[var(--text-secondary)]';
    label.textContent = field.label || field.name || 'Field';
    wrapper.appendChild(label);

    const cls = 'w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-canvas)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent-primary)] focus:outline-none';
    const tag = field.type === 'textarea' ? 'textarea' : (field.type === 'select' ? 'select' : 'input');
    const inputEl = document.createElement(tag);
    inputEl.className = cls;
    inputEl.id = fieldId;
    if (tag === 'input') inputEl.type = field.type || 'text';
    if (tag === 'textarea') inputEl.rows = field.rows || 3;
    if (tag === 'select') {
      (field.options || []).forEach(function (opt) {
        const optionEl = document.createElement('option');
        optionEl.value = typeof opt === 'object' && opt !== null ? opt.value : String(opt);
        optionEl.textContent = typeof opt === 'object' && opt !== null ? opt.label : String(opt);
        if (field.value !== undefined && String(optionEl.value) === String(field.value)) optionEl.selected = true;
        inputEl.appendChild(optionEl);
      });
    } else if (field.value !== undefined) {
      inputEl.value = field.value;
    }
    if (field.name) inputEl.name = field.name;
    if (field.placeholder) inputEl.placeholder = field.placeholder;
    if (field.required) inputEl.required = true;
    wrapper.appendChild(inputEl);
    return wrapper;
  }

  function openFormModal(options) {
    const opts = options || {};
    const modal = byId('form-modal');
    const titleEl = byId('form-modal-title');
    const formEl = byId('form-modal-element');
    const fieldsEl = byId('form-modal-fields');
    if (!modal || !titleEl || !formEl || !fieldsEl) return;

    titleEl.textContent = opts.title || 'Modal Form';
    const actionUrl = opts.actionUrl || '';
    formEl.setAttribute('action', actionUrl);
    formEl.setAttribute('method', opts.method || 'post');
    fieldsEl.innerHTML = '';

    if (Array.isArray(opts.fields)) {
      opts.fields.forEach(function (field) { fieldsEl.appendChild(createFieldNode(field)); });
    } else if (typeof opts.fieldsHtml === 'string') {
      fieldsEl.innerHTML = opts.fieldsHtml;
    }

    if (activeSubmitHandler) {
      formEl.removeEventListener('submit', activeSubmitHandler);
      activeSubmitHandler = null;
    }
    if (!actionUrl || actionUrl === '#') {
      activeSubmitHandler = function (event) {
        event.preventDefault();
        if (!formEl.checkValidity()) { formEl.reportValidity(); return; }
        closeFormModal();
        showToast(opts.previewMessage || 'Submitted successfully.', 'success');
      };
      formEl.addEventListener('submit', activeSubmitHandler);
    }
    setModalOpen(modal, true);
  }

  function closeFormModal() {
    const formEl = byId('form-modal-element');
    if (formEl && activeSubmitHandler) {
      formEl.removeEventListener('submit', activeSubmitHandler);
      activeSubmitHandler = null;
    }
    setModalOpen(byId('form-modal'), false);
  }

  function removeToastNode(node) {
    if (!node || !node.parentNode) return;
    node.style.opacity = '0';
    node.style.transform = 'translateY(0.35rem)';
    node.style.transition = 'opacity 150ms ease, transform 150ms ease';
    setTimeout(function () { if (node.parentNode) node.parentNode.removeChild(node); }, 160);
  }

  function showToast(message, severity) {
    const container = byId('toast-container');
    if (!container) return;
    const style = TOAST_STYLES[(severity || 'info').toLowerCase()] || TOAST_STYLES.info;
    const toast = document.createElement('div');
    toast.setAttribute('role', 'status');
    toast.setAttribute('data-toast', 'true');
    toast.className = 'toast-enter pointer-events-auto flex items-start gap-3 rounded-xl border border-[var(--border-subtle)] border-l-4 bg-[var(--bg-surface)] p-4 shadow-lg';
    toast.style.borderLeftColor = style.border;

    const icon = document.createElement('i');
    icon.className = style.icon + ' mt-0.5 text-base shrink-0';
    icon.style.color = style.color;

    const text = document.createElement('p');
    text.className = 'flex-1 text-sm font-medium leading-snug text-[var(--text-primary)]';
    text.textContent = String(message || '');

    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.setAttribute('aria-label', 'Dismiss notification');
    closeBtn.className = 'inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-elevated)] hover:text-[var(--text-primary)]';
    closeBtn.innerHTML = '<i class="fa-solid fa-xmark text-xs"></i>';
    closeBtn.addEventListener('click', function () { removeToastNode(toast); });

    toast.append(icon, text, closeBtn);
    container.appendChild(toast);
    setTimeout(function () { removeToastNode(toast); }, 4500);
  }

  function setMobileSidebar(open) {
    const drawer = byId('mobile-sidebar-drawer');
    const backdrop = byId('mobile-sidebar-backdrop');
    if (drawer) {
      drawer.classList.toggle('-translate-x-full', !open);
      drawer.classList.toggle('translate-x-0', open);
    }
    if (backdrop) backdrop.classList.toggle('hidden', !open);
    syncBodyScrollLock();
  }

  function openMobileSidebar() { setMobileSidebar(true); }
  function closeMobileSidebar() { setMobileSidebar(false); }

  function syncThemeButton() {
    const isDark = document.documentElement.classList.contains('dark');
    const btn = byId('theme-toggle-btn');
    const sun = byId('theme-icon-sun');
    const moon = byId('theme-icon-moon');
    const label = byId('theme-toggle-label');
    if (btn) btn.setAttribute('aria-pressed', isDark ? 'true' : 'false');
    if (sun) sun.classList.toggle('hidden', !isDark);
    if (moon) moon.classList.toggle('hidden', isDark);
    if (label) label.textContent = isDark ? 'Light' : 'Dark';
  }

  function toggleTheme() {
    const nextTheme = document.documentElement.classList.contains('dark') ? 'light' : 'dark';
    document.documentElement.classList.toggle('dark', nextTheme === 'dark');
    try { localStorage.setItem(THEME_KEY, nextTheme); } catch (e) {}
    syncThemeButton();
    window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: nextTheme } }));
  }

  function closeNotificationDropdown() {
    const dropdown = byId('notification-dropdown');
    const bell = byId('notification-bell-btn');
    if (dropdown) dropdown.classList.add('hidden');
    if (bell) bell.setAttribute('aria-expanded', 'false');
  }

  function initShellBindings() {
    const themeBtn = byId('theme-toggle-btn');
    if (themeBtn) themeBtn.addEventListener('click', toggleTheme);
    syncThemeButton();

    if (byId('mobile-sidebar-toggle')) byId('mobile-sidebar-toggle').addEventListener('click', openMobileSidebar);
    if (byId('mobile-sidebar-close')) byId('mobile-sidebar-close').addEventListener('click', closeMobileSidebar);
    if (byId('mobile-sidebar-backdrop')) byId('mobile-sidebar-backdrop').addEventListener('click', closeMobileSidebar);

    const bell = byId('notification-bell-btn');
    const dropdown = byId('notification-dropdown');
    if (bell && dropdown) {
      bell.addEventListener('click', function (e) {
        e.stopPropagation();
        const open = dropdown.classList.contains('hidden');
        dropdown.classList.toggle('hidden', !open);
        bell.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
      document.addEventListener('click', function (e) {
        if (!dropdown.contains(e.target) && !bell.contains(e.target)) closeNotificationDropdown();
      });
    }

    const markRead = byId('mark-notifications-read-btn');
    if (markRead) {
      markRead.addEventListener('click', function () {
        const badge = byId('notification-unread-badge');
        const list = byId('notification-list');
        if (badge) { badge.classList.add('hidden'); badge.textContent = '0'; }
        if (list) list.innerHTML = '<div class="px-4 py-6 text-center text-xs text-[var(--text-muted)]">No unread notifications.</div>';
        closeNotificationDropdown();
        showToast('All notifications marked as read.', 'info');
      });
    }

    document.querySelectorAll('input[data-table-search]').forEach(function (input) {
      input.addEventListener('input', function () {
        const q = input.value.trim().toLowerCase();
        const targetId = input.getAttribute('data-table-search');
        const targetEl = targetId ? byId(targetId) : null;
        const tables = targetEl ? [targetEl] : Array.from(document.querySelectorAll('table[data-searchable-table], main table'));
        tables.forEach(function (table) {
          table.querySelectorAll('tbody tr').forEach(function (row) {
            if (!row.hasAttribute('data-empty-row')) {
              row.classList.toggle('hidden', Boolean(q) && (row.textContent || '').toLowerCase().indexOf(q) === -1);
            }
          });
        });
      });
    });

    ['confirm-modal', 'form-modal'].forEach(function (id) {
      const el = byId(id);
      if (el) el.addEventListener('click', function (e) { if (e.target === el) setModalOpen(el, false); });
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        closeConfirmModal();
        closeFormModal();
        closeMobileSidebar();
        closeNotificationDropdown();
      }
    });

    const toastContainer = byId('toast-container');
    if (toastContainer) {
      toastContainer.querySelectorAll('[data-toast]').forEach(function (node) {
        setTimeout(function () { removeToastNode(node); }, 5000);
      });
    }
  }

  window.openConfirmModal = openConfirmModal;
  window.closeConfirmModal = closeConfirmModal;
  window.openFormModal = openFormModal;
  window.closeFormModal = closeFormModal;
  window.showToast = showToast;
  window.toggleTheme = toggleTheme;
  window.openMobileSidebar = openMobileSidebar;
  window.closeMobileSidebar = closeMobileSidebar;

  document.addEventListener('DOMContentLoaded', initShellBindings);
})();
