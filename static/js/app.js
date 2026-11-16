(function () {
  const THEME_KEY = 'edupredict_theme', SIDEBAR_KEY = 'edupredict_sidebar_collapsed';
  const MODAL_IDS = ['confirm-modal', 'form-modal', 'coming-soon-modal'];
  const FIELD_CLS = 'w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-canvas)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent-primary)] focus:outline-none';
  const TOAST_STYLES = {
    success: { border: 'var(--status-success)', icon: 'fa-solid fa-circle-check', color: 'var(--status-success)' },
    warning: { border: 'var(--status-warning)', icon: 'fa-solid fa-triangle-exclamation', color: 'var(--status-warning)' },
    danger: { border: 'var(--status-danger)', icon: 'fa-solid fa-circle-exclamation', color: 'var(--status-danger)' },
    info: { border: 'var(--accent-primary)', icon: 'fa-solid fa-circle-info', color: 'var(--accent-primary)' }
  };
  let activeSubmitHandler = null, globalsBound = false;
  const paginatedControllers = [];
  const byId = (id) => document.getElementById(id);
  const isDesktop = () => window.innerWidth >= 1024;
  const bindOnce = (el, ev, fn) => { if (el && el.dataset['bound_' + ev] !== '1') { el.dataset['bound_' + ev] = '1'; el.addEventListener(ev, fn); } };
  const mk = (tag, cls, text, attrs) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = String(text);
    if (attrs) Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
    return n;
  };
  const getCsrfToken = () => {
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : (document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '');
  };

  function syncBodyScrollLock() {
    if (!document.body) return;
    const modalOpen = MODAL_IDS.some((id) => { const m = byId(id); return m && !m.classList.contains('hidden'); });
    const drawer = byId('mobile-sidebar-drawer');
    document.body.classList.toggle('modal-open', Boolean(modalOpen));
    document.body.classList.toggle('drawer-open', Boolean(!isDesktop() && drawer && !drawer.classList.contains('-translate-x-full')));
  }
  function setModalOpen(modal, open) {
    if (!modal) return;
    modal.classList.toggle('hidden', !open);
    if (modal.classList.contains('items-center') || modal.classList.contains('justify-center')) modal.classList.toggle('flex', open);
    modal.setAttribute('aria-hidden', open ? 'false' : 'true');
    syncBodyScrollLock();
  }
  function openConfirmModal(options) {
    const opts = options || {}, modal = byId('confirm-modal'), titleEl = byId('confirm-modal-title'), msgEl = byId('confirm-modal-message'), formEl = byId('confirm-modal-form');
    if (!modal || !titleEl || !msgEl || !formEl) return;
    titleEl.textContent = opts.title || 'Please Confirm';
    msgEl.textContent = opts.message || 'Are you sure you want to do this?';
    formEl.setAttribute('action', opts.onConfirmUrl || '');
    formEl.querySelectorAll('[data-confirm-field]').forEach((el) => el.remove());
    if (opts.fields && typeof opts.fields === 'object') {
      const pairs = Array.isArray(opts.fields) ? opts.fields.map((f) => [f.name, f.value]) : Object.entries(opts.fields);
      pairs.forEach(([name, value]) => { if (name) formEl.appendChild(mk('input', '', undefined, { type: 'hidden', name: name, value: value == null ? '' : String(value), 'data-confirm-field': 'true' })); });
    }
    const btn = formEl.querySelector('button[type="submit"]');
    if (btn) btn.textContent = opts.confirmText || 'Confirm';
    setModalOpen(modal, true);
  }
  const closeConfirmModal = () => setModalOpen(byId('confirm-modal'), false);
  function openComingSoonModal(options) {
    const opts = options || {}, modal = byId('coming-soon-modal'), titleEl = byId('coming-soon-modal-title'), descEl = byId('coming-soon-modal-desc'), listEl = byId('coming-soon-modal-features');
    if (!modal || !titleEl || !descEl || !listEl) return;
    if (byId('coming-soon-modal-panel')) byId('coming-soon-modal-panel').textContent = opts.panel || 'Coming Soon';
    titleEl.textContent = opts.title || 'Feature Coming Soon';
    descEl.textContent = opts.desc || opts.description || 'This feature is planned next and will use live data from MongoDB.';
    let items = Array.isArray(opts.features) ? opts.features : (typeof opts.features === 'string' && opts.features.trim() ? opts.features.split('|').map((s) => s.trim()).filter(Boolean) : []);
    if (!items.length) items = ['Live numbers from MongoDB', 'Easy charts and 5-row tables', 'Quick alerts and CSV downloads'];
    listEl.innerHTML = '';
    items.forEach((text) => {
      const li = mk('li', 'flex items-start gap-2');
      li.append(mk('i', 'fa-solid fa-check mt-0.5 text-[11px] text-[var(--accent-primary)] shrink-0', undefined, { 'aria-hidden': 'true' }), mk('span', '', text));
      listEl.appendChild(li);
    });
    setModalOpen(modal, true);
  }
  const closeComingSoonModal = () => setModalOpen(byId('coming-soon-modal'), false);
  function createFieldNode(field) {
    if (field.type === 'hidden') return mk('input', '', undefined, { type: 'hidden', name: field.name || '', value: field.value !== undefined ? field.value : '', hidden: 'true' });
    const wrapper = mk('div', 'space-y-1.5'), fieldId = 'modal-field-' + (field.name || Math.random().toString(36).slice(2, 8));
    const label = mk('label', 'block text-sm font-medium text-[var(--text-secondary)]', field.label || field.name || 'Field', { for: fieldId });
    const tag = field.type === 'textarea' ? 'textarea' : (field.type === 'select' ? 'select' : 'input'), el = mk(tag, FIELD_CLS, undefined, { id: fieldId });
    if (tag === 'input') el.type = field.type || 'text';
    if (tag === 'textarea') el.rows = field.rows || 3;
    if (tag === 'select') {
      (field.options || []).forEach((opt) => {
        const isObj = typeof opt === 'object' && opt !== null, optEl = mk('option', '', isObj ? opt.label : opt);
        optEl.value = isObj ? opt.value : String(opt);
        if (field.value !== undefined && String(optEl.value) === String(field.value)) optEl.selected = true;
        el.appendChild(optEl);
      });
    } else if (field.value !== undefined) el.value = field.value;
    ['name', 'placeholder', 'min', 'max', 'step'].forEach((k) => { if (field[k] !== undefined) el[k] = field[k]; });
    if (field.required) el.required = true;
    if (field.readonly) el.readOnly = true;
    wrapper.append(label, el);
    return wrapper;
  }
  function openFormModal(options) {
    const opts = options || {}, modal = byId('form-modal'), titleEl = byId('form-modal-title'), formEl = byId('form-modal-element'), fieldsEl = byId('form-modal-fields');
    if (!modal || !titleEl || !formEl || !fieldsEl) return;
    titleEl.textContent = opts.title || 'Form';
    const actionUrl = opts.actionUrl || '';
    formEl.setAttribute('action', actionUrl);
    formEl.setAttribute('method', opts.method || 'post');
    if (byId('form-modal-submit-btn')) byId('form-modal-submit-btn').textContent = opts.submitText || 'Save';
    fieldsEl.innerHTML = '';
    if (Array.isArray(opts.fields)) opts.fields.forEach((f) => fieldsEl.appendChild(createFieldNode(f)));
    else if (typeof opts.fieldsHtml === 'string') fieldsEl.innerHTML = opts.fieldsHtml;
    if (activeSubmitHandler) { formEl.removeEventListener('submit', activeSubmitHandler); activeSubmitHandler = null; }
    if (!actionUrl || actionUrl === '#') {
      activeSubmitHandler = (e) => { e.preventDefault(); if (!formEl.checkValidity()) { formEl.reportValidity(); return; } closeFormModal(); showToast(opts.previewMessage || 'Saved.', 'success'); };
      formEl.addEventListener('submit', activeSubmitHandler);
    }
    setModalOpen(modal, true);
  }
  function closeFormModal() {
    const formEl = byId('form-modal-element');
    if (formEl && activeSubmitHandler) { formEl.removeEventListener('submit', activeSubmitHandler); activeSubmitHandler = null; }
    setModalOpen(byId('form-modal'), false);
  }
  function removeToastNode(node) {
    if (!node || !node.parentNode) return;
    Object.assign(node.style, { opacity: '0', transform: 'translateY(0.35rem)', transition: 'opacity 150ms ease, transform 150ms ease' });
    setTimeout(() => { if (node.parentNode) node.parentNode.removeChild(node); }, 160);
  }
  function showToast(message, severity) {
    const container = byId('toast-container');
    if (!container) return;
    const rawKey = (severity || 'info').toLowerCase(), style = TOAST_STYLES[rawKey === 'error' ? 'danger' : rawKey] || TOAST_STYLES.info;
    const toast = mk('div', 'toast-enter pointer-events-auto flex items-start gap-3 rounded-xl border border-[var(--border-subtle)] border-l-4 bg-[var(--bg-surface)] p-4 shadow-lg', undefined, { role: 'status', 'data-toast': 'true' });
    toast.style.borderLeftColor = style.border;
    const icon = mk('i', style.icon + ' mt-0.5 text-base shrink-0');
    icon.style.color = style.color;
    const closeBtn = mk('button', 'inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-elevated)] hover:text-[var(--text-primary)]', undefined, { type: 'button', 'aria-label': 'Dismiss alert' });
    closeBtn.innerHTML = '<i class="fa-solid fa-xmark text-xs"></i>';
    closeBtn.addEventListener('click', () => removeToastNode(toast));
    toast.append(icon, mk('p', 'flex-1 text-sm font-medium leading-snug text-[var(--text-primary)]', message || ''), closeBtn);
    container.appendChild(toast);
    setTimeout(() => removeToastNode(toast), 4500);
  }

  function applyDesktopSidebarClasses(collapsed) {
    document.documentElement.classList.toggle('sidebar-collapsed', collapsed);
    if (document.body) document.body.classList.toggle('sidebar-collapsed', collapsed);
    const drawer = byId('mobile-sidebar-drawer'), main = byId('app-shell-main');
    if (drawer) { drawer.classList.toggle('lg:-translate-x-full', collapsed); drawer.classList.toggle('lg:translate-x-0', !collapsed); }
    if (main) { main.classList.toggle('lg:pl-0', collapsed); main.classList.toggle('lg:pl-64', !collapsed); }
  }
  function syncSidebarToggleA11y() {
    const btn = byId('mobile-sidebar-toggle'), drawer = byId('mobile-sidebar-drawer');
    const collapsed = document.documentElement.classList.contains('sidebar-collapsed') || (document.body && document.body.classList.contains('sidebar-collapsed'));
    if (btn) btn.setAttribute('aria-expanded', (isDesktop() ? !collapsed : Boolean(drawer && !drawer.classList.contains('-translate-x-full'))) ? 'true' : 'false');
  }
  function restoreSidebarState() {
    let collapsed = document.documentElement.classList.contains('sidebar-collapsed');
    try { const saved = localStorage.getItem(SIDEBAR_KEY); if (saved !== null) collapsed = saved === 'true' || saved === '1'; } catch (e) {}
    applyDesktopSidebarClasses(collapsed);
    syncSidebarToggleA11y();
  }
  function setMobileSidebar(open) {
    const drawer = byId('mobile-sidebar-drawer'), backdrop = byId('mobile-sidebar-backdrop');
    if (drawer) { drawer.classList.toggle('-translate-x-full', !open); drawer.classList.toggle('translate-x-0', open); }
    if (backdrop) backdrop.classList.toggle('hidden', !open);
    syncBodyScrollLock();
    syncSidebarToggleA11y();
  }
  const openMobileSidebar = () => setMobileSidebar(true);
  const closeMobileSidebar = () => setMobileSidebar(false);
  function setDesktopCollapsed(collapsed) {
    applyDesktopSidebarClasses(collapsed);
    try { localStorage.setItem(SIDEBAR_KEY, collapsed ? 'true' : 'false'); } catch (e) {}
    syncSidebarToggleA11y();
    setTimeout(() => window.dispatchEvent(new Event('resize')), 220);
  }
  function toggleSidebar() {
    if (isDesktop()) { setDesktopCollapsed(!(document.documentElement.classList.contains('sidebar-collapsed') || (document.body && document.body.classList.contains('sidebar-collapsed')))); return; }
    setMobileSidebar(!(byId('mobile-sidebar-drawer') && !byId('mobile-sidebar-drawer').classList.contains('-translate-x-full')));
  }
  const closeSidebarAny = () => (isDesktop() ? setDesktopCollapsed(true) : closeMobileSidebar());
  function syncThemeButton() {
    const isDark = document.documentElement.classList.contains('dark');
    if (byId('theme-toggle-btn')) byId('theme-toggle-btn').setAttribute('aria-pressed', isDark ? 'true' : 'false');
    if (byId('theme-icon-sun')) byId('theme-icon-sun').classList.toggle('hidden', !isDark);
    if (byId('theme-icon-moon')) byId('theme-icon-moon').classList.toggle('hidden', isDark);
    if (byId('theme-toggle-label')) byId('theme-toggle-label').textContent = isDark ? 'Light' : 'Dark';
  }
  function toggleTheme() {
    const nextTheme = document.documentElement.classList.contains('dark') ? 'light' : 'dark';
    document.documentElement.classList.toggle('dark', nextTheme === 'dark');
    try { localStorage.setItem(THEME_KEY, nextTheme); } catch (e) {}
    syncThemeButton();
    window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: nextTheme } }));
  }
  function closeNotificationDropdown() {
    if (byId('notification-dropdown')) byId('notification-dropdown').classList.add('hidden');
    if (byId('notification-bell-btn')) byId('notification-bell-btn').setAttribute('aria-expanded', 'false');
  }
  function compareCells(rowA, rowB, colIdx, dir) {
    const rawA = ((rowA?.children[colIdx]?.textContent) || '').trim(), rawB = ((rowB?.children[colIdx]?.textContent) || '').trim();
    const numA = rawA.replace(/,/g, '').replace(/%$/, ''), numB = rawB.replace(/,/g, '').replace(/%$/, '');
    const cmp = (/^-?\d+(\.\d+)?$/.test(numA) && /^-?\d+(\.\d+)?$/.test(numB)) ? (parseFloat(numA) - parseFloat(numB)) : rawA.localeCompare(rawB, undefined, { numeric: true, sensitivity: 'base' });
    return dir === 'asc' ? cmp : -cmp;
  }
  function initPaginatedContainers() {
    paginatedControllers.length = 0;
    document.querySelectorAll('[data-paginated-container]').forEach((container) => {
      if (container.dataset.paginationReady === '1') { if (container._paginationController) paginatedControllers.push(container._paginationController); return; }
      container.dataset.paginationReady = '1';
      const pageSize = Math.max(1, parseInt(container.getAttribute('data-page-size') || '5', 10) || 5);
      const desktopRows = Array.from(container.querySelectorAll('tbody tr[data-page-item]')), mobileCards = Array.from(container.querySelectorAll('[data-mobile-card][data-page-item]'));
      const fallback = (!desktopRows.length && !mobileCards.length) ? Array.from(container.querySelectorAll('[data-page-item]')) : [];
      const rowCount = fallback.length || Math.max(desktopRows.length, mobileCards.length);
      const entries = Array.from({ length: rowCount }, (_, i) => {
        const nodes = fallback.length ? [fallback[i]] : [desktopRows[i], mobileCards[i]].filter(Boolean);
        return { nodes, searchText: nodes.map((n) => n.textContent || '').join(' ').toLowerCase() };
      });
      const qSel = (s) => container.querySelector(s), bar = qSel('[data-pagination-bar]'), infoEl = qSel('[data-pagination-info]');
      const indicatorEl = qSel('[data-page-indicator]'), prevBtn = qSel('[data-page-prev]'), nextBtn = qSel('[data-page-next]'), searchEmptyEl = qSel('[data-search-empty]');
      let currentPage = 1, query = '';
      const renderPage = () => {
        const matched = entries.filter((e) => !query || e.searchText.indexOf(query) !== -1), total = matched.length, totalPages = Math.max(1, Math.ceil(total / pageSize));
        if (currentPage > totalPages) currentPage = totalPages;
        const startIdx = (currentPage - 1) * pageSize, endIdx = Math.min(startIdx + pageSize, total), visibleSet = new Set(matched.slice(startIdx, endIdx));
        entries.forEach((e) => e.nodes.forEach((n) => n.classList.toggle('hidden', !visibleSet.has(e))));
        if (searchEmptyEl) searchEmptyEl.classList.toggle('hidden', total > 0 || rowCount === 0);
        if (infoEl) infoEl.textContent = total ? ('Showing ' + (startIdx + 1) + '-' + endIdx + ' of ' + total) : 'Showing 0 of 0';
        if (indicatorEl) indicatorEl.textContent = 'Page ' + currentPage + ' of ' + totalPages;
        if (prevBtn) prevBtn.disabled = currentPage <= 1;
        if (nextBtn) nextBtn.disabled = currentPage >= totalPages;
        if (bar) { bar.classList.toggle('hidden', total <= pageSize); bar.classList.toggle('flex', total > pageSize); }
      };
      const sortEntries = (colIdx, dir) => {
        if (!entries.length) return;
        entries.sort((a, b) => compareCells(a.nodes[0], b.nodes[0], colIdx, dir));
        const tbody = container.querySelector('tbody'), mobileWrap = mobileCards[0]?.parentElement;
        entries.forEach((e) => { if (tbody && e.nodes[0]?.parentNode === tbody) tbody.appendChild(e.nodes[0]); if (mobileWrap && e.nodes[1]?.parentNode === mobileWrap) mobileWrap.appendChild(e.nodes[1]); });
        currentPage = 1; renderPage();
      };
      if (prevBtn) prevBtn.addEventListener('click', () => { if (currentPage > 1) { currentPage -= 1; renderPage(); } });
      if (nextBtn) nextBtn.addEventListener('click', () => { currentPage += 1; renderPage(); });
      container._paginationController = { applySearch: (q) => { query = String(q || '').trim().toLowerCase(); currentPage = 1; renderPage(); }, sortEntries };
      paginatedControllers.push(container._paginationController);
      renderPage();
    });
  }
  function initSortableTables() {
    document.querySelectorAll('table[data-searchable-table]').forEach((table) => {
      if (table.dataset.sortReady === '1') return;
      table.dataset.sortReady = '1';
      const headers = Array.from(table.querySelectorAll('thead th'));
      headers.forEach((th, colIdx) => {
        const label = (th.textContent || '').trim();
        if (!label || label.toLowerCase() === 'actions' || th.getAttribute('data-sortable') === 'false') return;
        th.setAttribute('data-sortable', 'true'); th.setAttribute('aria-sort', 'none');
        if (!th.getAttribute('title')) th.setAttribute('title', 'Sort by ' + label);
        th.addEventListener('click', () => {
          const dir = th.getAttribute('data-sort-dir') === 'asc' ? 'desc' : 'asc';
          headers.forEach((h) => { h.removeAttribute('data-sort-dir'); h.setAttribute('aria-sort', 'none'); });
          th.setAttribute('data-sort-dir', dir); th.setAttribute('aria-sort', dir === 'asc' ? 'ascending' : 'descending');
          const container = table.closest('[data-paginated-container]');
          if (container?._paginationController) { container._paginationController.sortEntries(colIdx, dir); return; }
          const tbody = table.querySelector('tbody');
          if (tbody) Array.from(tbody.querySelectorAll('tr')).filter((r) => !r.hasAttribute('data-empty-row')).sort((a, b) => compareCells(a, b, colIdx, dir)).forEach((r) => tbody.appendChild(r));
        });
      });
    });
  }
  function filterPlainTable(table, q) {
    table.querySelectorAll('tbody tr').forEach((row) => { if (!row.hasAttribute('data-empty-row')) row.classList.toggle('hidden', Boolean(q) && (row.textContent || '').toLowerCase().indexOf(q) === -1); });
  }
  function bindTableSearch() {
    document.querySelectorAll('input[data-table-search]').forEach((input) => {
      bindOnce(input, 'input', () => {
        const q = input.value.trim().toLowerCase(), targetEl = byId(input.getAttribute('data-table-search'));
        if (targetEl) {
          const container = targetEl.hasAttribute('data-paginated-container') ? targetEl : targetEl.closest('[data-paginated-container]');
          if (container?._paginationController) container._paginationController.applySearch(q);
          else filterPlainTable(targetEl, q);
          return;
        }
        paginatedControllers.forEach((ctrl) => ctrl.applySearch(q));
        document.querySelectorAll('table[data-searchable-table], main table').forEach((t) => { if (!t.closest('[data-paginated-container]')) filterPlainTable(t, q); });
      });
    });
  }
  function bindDynamicControls() {
    restoreSidebarState(); syncThemeButton();
    bindOnce(byId('theme-toggle-btn'), 'click', toggleTheme);
    bindOnce(byId('mobile-sidebar-toggle'), 'click', toggleSidebar);
    bindOnce(byId('mobile-sidebar-close'), 'click', closeSidebarAny);
    bindOnce(byId('mobile-sidebar-backdrop'), 'click', closeMobileSidebar);
    bindOnce(byId('notification-bell-btn'), 'click', (e) => {
      e.stopPropagation();
      const dropdown = byId('notification-dropdown'), bell = byId('notification-bell-btn');
      if (!dropdown || !bell) return;
      const open = dropdown.classList.contains('hidden');
      dropdown.classList.toggle('hidden', !open); bell.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    bindOnce(byId('mark-notifications-read-btn'), 'click', () => {
      const token = getCsrfToken();
      if (typeof fetch === 'function') fetch('/notifications/mark-read/', { method: 'POST', headers: token ? { 'X-CSRFToken': token } : {}, credentials: 'same-origin' }).catch(function () {});
      if (byId('notification-unread-badge')) { byId('notification-unread-badge').classList.add('hidden'); byId('notification-unread-badge').textContent = '0'; }
      if (byId('notification-list')) byId('notification-list').innerHTML = '<div class="px-4 py-6 text-center text-xs text-[var(--text-muted)]">No new alerts.</div>';
      closeNotificationDropdown(); showToast('All alerts marked as read.', 'info');
    });
    initPaginatedContainers(); initSortableTables(); bindTableSearch();
    const toastContainer = byId('toast-container');
    if (toastContainer) toastContainer.querySelectorAll('[data-toast]').forEach((node) => setTimeout(() => removeToastNode(node), 5000));
  }
  function bindDocumentGlobalsOnce() {
    if (globalsBound) return;
    globalsBound = true;
    document.addEventListener('click', (e) => {
      const dropdown = byId('notification-dropdown'), bell = byId('notification-bell-btn');
      if (dropdown && bell && !dropdown.contains(e.target) && !bell.contains(e.target)) closeNotificationDropdown();
      const comingTrigger = e.target.closest('[data-coming-soon]');
      if (comingTrigger) {
        e.preventDefault(); if (!isDesktop()) closeMobileSidebar();
        openComingSoonModal({ title: comingTrigger.getAttribute('data-coming-title') || comingTrigger.textContent.trim(), panel: comingTrigger.getAttribute('data-coming-panel') || 'Coming Soon', desc: comingTrigger.getAttribute('data-coming-desc') || '', features: comingTrigger.getAttribute('data-coming-features') || '' });
        return;
      }
      if (e.target.closest('#mobile-sidebar-drawer a[href]') && !isDesktop()) closeMobileSidebar();
    });
    MODAL_IDS.forEach((id) => bindOnce(byId(id), 'click', (e) => { if (e.target === byId(id)) setModalOpen(byId(id), false); }));
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { closeConfirmModal(); closeFormModal(); closeComingSoonModal(); closeMobileSidebar(); closeNotificationDropdown(); } });
    window.addEventListener('resize', () => {
      if (isDesktop()) {
        if (byId('mobile-sidebar-backdrop')) byId('mobile-sidebar-backdrop').classList.add('hidden');
        const drawer = byId('mobile-sidebar-drawer');
        if (drawer) { drawer.classList.add('-translate-x-full'); drawer.classList.remove('translate-x-0'); }
        restoreSidebarState(); syncBodyScrollLock();
      }
      syncSidebarToggleA11y();
    });
  }
  function reinitEduPredictUI() { closeConfirmModal(); closeFormModal(); closeComingSoonModal(); closeNotificationDropdown(); bindDynamicControls(); }
  function initShellBindings() { bindDocumentGlobalsOnce(); bindDynamicControls(); }

  restoreSidebarState();
  Object.assign(window, { openConfirmModal, closeConfirmModal, openFormModal, closeFormModal, openComingSoonModal, closeComingSoonModal, showToast, toggleTheme, openMobileSidebar, closeMobileSidebar, toggleSidebar, closeSidebarAny, reinitEduPredictUI });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initShellBindings);
  else initShellBindings();
})();
