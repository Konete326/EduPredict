(function () {
  const THEME_KEY = 'edupredict_theme', SIDEBAR_KEY = 'edupredict_sidebar_collapsed';
  const MODAL_IDS = ['confirm-modal', 'form-modal', 'coming-soon-modal', 'theme-studio-modal', 'page-guide-modal'];
  const FIELD_CLS = 'w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-canvas)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent-primary)] focus:outline-none';
  const TOAST_STYLES = { success: { border: 'var(--status-success)', icon: 'fa-solid fa-circle-check', color: 'var(--status-success)' }, warning: { border: 'var(--status-warning)', icon: 'fa-solid fa-triangle-exclamation', color: 'var(--status-warning)' }, danger: { border: 'var(--status-danger)', icon: 'fa-solid fa-circle-exclamation', color: 'var(--status-danger)' }, info: { border: 'var(--accent-primary)', icon: 'fa-solid fa-circle-info', color: 'var(--accent-primary)' } };
  let activeSubmitHandler = null, globalsBound = false, pointerDownTarget = null;
  const paginatedControllers = [];
  const byId = (id) => document.getElementById(id);
  const isDesktop = () => window.innerWidth >= 1024;
  const bindOnce = (el, ev, fn) => { if (el && el.dataset['bound_' + ev] !== '1') { el.dataset['bound_' + ev] = '1'; el.addEventListener(ev, fn); } };
  const mk = (tag, cls, text, attrs) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = String(text); if (attrs) Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v)); return n; };
  const getCsrfToken = () => { const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/); return m ? decodeURIComponent(m[1]) : (document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || ''); };
  function syncBodyScrollLock() {
    if (!document.body) return;
    const modalOpen = MODAL_IDS.some((id) => { const m = byId(id); return m && !m.classList.contains('hidden'); }) || Boolean(document.querySelector('[data-ep-modal]:not(.hidden)'));
    const overlayDrawerOpen = ['ticket-detail-drawer', 'student-360-drawer'].some((id) => { const d = byId(id); return d && !d.classList.contains('hidden'); }), drawer = byId('mobile-sidebar-drawer'), mobileOpen = Boolean(!isDesktop() && drawer && !drawer.classList.contains('-translate-x-full'));
    document.body.classList.toggle('modal-open', Boolean(modalOpen)); document.body.classList.toggle('drawer-open', Boolean(mobileOpen || overlayDrawerOpen)); document.body.classList.toggle('ep-overlay-blur', Boolean(modalOpen || overlayDrawerOpen));
  }
  function setModalOpen(modal, open) { if (!modal) return; modal.classList.toggle('hidden', !open); modal.classList.toggle('flex', open); modal.setAttribute('aria-hidden', open ? 'false' : 'true'); syncBodyScrollLock(); }
  function openConfirmModal(options) {
    const opts = options || {}, modal = byId('confirm-modal'), titleEl = byId('confirm-modal-title'), msgEl = byId('confirm-modal-message'), formEl = byId('confirm-modal-form');
    if (!modal || !titleEl || !msgEl || !formEl) return;
    titleEl.textContent = opts.title || 'Please Confirm'; msgEl.textContent = opts.message || 'Are you sure you want to do this?';
    formEl.setAttribute('action', opts.onConfirmUrl || ''); formEl.querySelectorAll('[data-confirm-field]').forEach((el) => el.remove());
    if (opts.fields && typeof opts.fields === 'object') {
      (Array.isArray(opts.fields) ? opts.fields.map((f) => [f.name, f.value]) : Object.entries(opts.fields)).forEach(([name, value]) => { if (name) formEl.appendChild(mk('input', '', undefined, { type: 'hidden', name: name, value: value == null ? '' : String(value), 'data-confirm-field': 'true' })); });
    }
    const btn = formEl.querySelector('button[type="submit"]'); if (btn) btn.textContent = opts.confirmText || 'Confirm';
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
    items.forEach((text) => { const li = mk('li', 'flex items-start gap-2'); li.append(mk('i', 'fa-solid fa-check mt-0.5 text-[11px] text-[var(--accent-primary)] shrink-0', undefined, { 'aria-hidden': 'true' }), mk('span', '', text)); listEl.appendChild(li); });
    setModalOpen(modal, true);
  }
  const closeComingSoonModal = () => setModalOpen(byId('coming-soon-modal'), false);
  function createSearchableSelect(field, fieldId) {
    const box = mk('div', 'relative', undefined, { 'data-searchable-select': 'true' }), opts = (field.options || []).map((o) => (typeof o === 'object' && o !== null ? { value: String(o.value ?? ''), label: String(o.label ?? o.value ?? '') } : { value: String(o), label: String(o) }));
    const curVal = field.value !== undefined && field.value !== null ? String(field.value) : '', matched = opts.find((o) => o.value === curVal);
    const hidden = mk('input', '', undefined, { type: 'hidden', name: field.name || '', value: curVal, 'data-ss-value': 'true' });
    const input = mk('input', FIELD_CLS + ' pr-8', undefined, { id: fieldId, type: 'text', autocomplete: 'off', placeholder: field.placeholder || 'Search or select...', value: matched ? matched.label : (field.allowCustom ? curVal : '') });
    if (field.required) input.required = true;
    const chev = mk('i', 'fa-solid fa-chevron-down pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[11px] text-[var(--text-muted)]');
    const list = mk('div', 'hidden absolute left-0 right-0 top-full z-50 mt-1 max-h-44 overflow-y-auto rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-1 shadow-xl');
    const render = (q) => {
      const term = String(q || '').trim().toLowerCase(), hits = term ? opts.filter((o) => o.label.toLowerCase().includes(term) || o.value.toLowerCase().includes(term)) : opts;
      list.innerHTML = '';
      if (!hits.length) { list.appendChild(mk('div', 'px-2.5 py-2 text-xs text-[var(--text-muted)]', field.allowCustom ? 'Press Enter or keep typed value' : 'No matching suggestions')); return; }
      hits.slice(0, 20).forEach((o) => {
        const btn = mk('button', 'flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-left text-xs text-[var(--text-primary)] hover:bg-[var(--bg-elevated)]' + (o.value === hidden.value ? ' bg-[var(--accent-soft)] font-semibold text-[var(--accent-primary)]' : ''), o.label, { type: 'button' });
        btn.addEventListener('mousedown', (ev) => { ev.preventDefault(); hidden.value = o.value; input.value = o.label; list.classList.add('hidden'); hidden.dispatchEvent(new Event('change', { bubbles: true })); });
        list.appendChild(btn);
      });
    };
    input.addEventListener('focus', () => { render(input.value === (opts.find((o) => o.value === hidden.value)?.label || '') ? '' : input.value); list.classList.remove('hidden'); });
    input.addEventListener('input', () => { if (field.allowCustom) hidden.value = input.value.trim(); else { const exact = opts.find((o) => o.label.toLowerCase() === input.value.trim().toLowerCase()); hidden.value = exact ? exact.value : ''; } render(input.value); list.classList.remove('hidden'); });
    input.addEventListener('blur', () => setTimeout(() => list.classList.add('hidden'), 140));
    box.append(hidden, input, chev, list);
    return box;
  }
  function createFieldNode(field) {
    if (field.type === 'hidden') return mk('input', '', undefined, { type: 'hidden', name: field.name || '', value: field.value !== undefined ? field.value : '', hidden: 'true' });
    const wrapper = mk('div', 'space-y-1.5'), fieldId = 'modal-field-' + (field.name || Math.random().toString(36).slice(2, 8));
    const label = mk('label', 'block text-sm font-medium text-[var(--text-secondary)]', field.label || field.name || 'Field', { for: fieldId });
    if (field.type === 'searchable_select') { wrapper.append(label, createSearchableSelect(field, fieldId)); return wrapper; }
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
    if (tag === 'input' && el.type === 'password') {
      el.classList.add('pr-9');
      const box = mk('div', 'relative'), toggleBtn = mk('button', 'absolute inset-y-0 right-0 flex items-center px-3 text-[var(--text-muted)] hover:text-[var(--text-primary)]', undefined, { type: 'button', 'data-password-toggle': 'true', 'aria-label': 'Show or hide password' });
      toggleBtn.innerHTML = '<i class="fa-regular fa-eye text-xs" aria-hidden="true"></i>';
      box.append(el, toggleBtn);
      wrapper.append(label, box);
    } else wrapper.append(label, el);
    return wrapper;
  }
  function setupModalShell(title, isBento, headerBadge) {
    const modal = byId('form-modal'), dialogEl = byId('form-modal-dialog'), titleEl = byId('form-modal-title'), badgeEl = byId('form-modal-badge'), formEl = byId('form-modal-element'), fieldsEl = byId('form-modal-fields'), submitBtn = byId('form-modal-submit-btn'), cancelBtn = byId('form-modal-cancel-btn');
    if (!modal || !titleEl || !formEl || !fieldsEl) return null;
    titleEl.textContent = title;
    if (badgeEl) { badgeEl.textContent = headerBadge || ''; badgeEl.classList.toggle('hidden', !headerBadge); }
    if (dialogEl) { dialogEl.classList.toggle('max-w-2xl', isBento); dialogEl.classList.toggle('max-w-lg', !isBento); }
    fieldsEl.className = isBento ? 'flex-1 overflow-y-auto px-5 pt-4 pb-6 grid grid-cols-1 md:grid-cols-2 gap-3.5 items-start' : 'flex-1 overflow-y-auto px-5 pt-4 pb-6 space-y-3.5';
    fieldsEl.innerHTML = '';
    if (activeSubmitHandler) { formEl.removeEventListener('submit', activeSubmitHandler); activeSubmitHandler = null; }
    return { modal, formEl, fieldsEl, submitBtn, cancelBtn };
  }
  function openFormModal(options) {
    const opts = options || {}, visibleFields = Array.isArray(opts.fields) ? opts.fields.filter((f) => f && f.type !== 'hidden') : [], isBento = visibleFields.length >= 5;
    const ctx = setupModalShell(opts.title || 'Form', isBento, opts.headerBadge || ''); if (!ctx) return;
    const actionUrl = opts.actionUrl || '';
    ctx.formEl.setAttribute('action', actionUrl); ctx.formEl.setAttribute('method', opts.method || 'post');
    if (ctx.submitBtn) { ctx.submitBtn.classList.remove('hidden'); ctx.submitBtn.textContent = opts.submitText || 'Save'; }
    if (ctx.cancelBtn) ctx.cancelBtn.textContent = opts.cancelText || 'Cancel';
    if (Array.isArray(opts.fields)) {
      let visIdx = 0, col = 0;
      opts.fields.forEach((f) => {
        const node = createFieldNode(f);
        if (isBento && f && f.type !== 'hidden') {
          const spanTwo = f.type === 'textarea' || Boolean(f.fullWidth) || (visIdx === visibleFields.length - 1 && col === 0);
          if (spanTwo) { node.classList.add('md:col-span-2'); col = 0; } else col = (col + 1) % 2;
          visIdx += 1;
        }
        ctx.fieldsEl.appendChild(node);
      });
    } else if (typeof opts.fieldsHtml === 'string') ctx.fieldsEl.innerHTML = opts.fieldsHtml;
    if (!actionUrl || actionUrl === '#') {
      activeSubmitHandler = (e) => { e.preventDefault(); if (!ctx.formEl.checkValidity()) { ctx.formEl.reportValidity(); return; } closeFormModal(); showToast(opts.previewMessage || 'Saved.', 'success'); };
      ctx.formEl.addEventListener('submit', activeSubmitHandler);
    }
    setModalOpen(ctx.modal, true);
  }
  function openViewDetailsModal(options) {
    const opts = options || {}, ctx = setupModalShell(opts.title || 'Details', true); if (!ctx) return;
    ctx.formEl.setAttribute('action', '');
    if (ctx.submitBtn) ctx.submitBtn.classList.add('hidden');
    if (ctx.cancelBtn) ctx.cancelBtn.textContent = 'Close';
    if (opts.subtitle || opts.badge) {
      const topBanner = mk('div', 'md:col-span-2 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3.5 py-2.5');
      if (opts.subtitle) topBanner.appendChild(mk('p', 'text-xs text-[var(--text-secondary)]', opts.subtitle));
      if (opts.badge) topBanner.appendChild(mk('span', 'rounded-full border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2.5 py-0.5 text-[11px] font-semibold text-[var(--accent-primary)]', opts.badge));
      ctx.fieldsEl.appendChild(topBanner);
    }
    const items = Array.isArray(opts.items) ? opts.items : [];
    let col = 0;
    items.forEach((item, idx) => {
      if (!item) return;
      const spanTwo = Boolean(item.fullWidth) || (idx === items.length - 1 && col === 0);
      const card = mk('div', 'rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-canvas)] p-3' + (spanTwo ? ' md:col-span-2' : ''));
      col = spanTwo ? 0 : (col + 1) % 2;
      card.append(mk('p', 'text-[11px] font-medium uppercase tracking-wider text-[var(--text-muted)]', item.label || ''), mk('p', 'mt-1 text-sm font-medium text-[var(--text-primary)] break-words', item.value !== undefined && item.value !== null && item.value !== '' ? String(item.value) : '—'));
      ctx.fieldsEl.appendChild(card);
    });
    setModalOpen(ctx.modal, true);
  }
  function closeFormModal() { const formEl = byId('form-modal-element'); if (formEl && activeSubmitHandler) { formEl.removeEventListener('submit', activeSubmitHandler); activeSubmitHandler = null; } setModalOpen(byId('form-modal'), false); }
  function removeToastNode(node) { if (!node || !node.parentNode) return; Object.assign(node.style, { opacity: '0', transform: 'translateY(0.35rem)', transition: 'opacity 150ms ease, transform 150ms ease' }); setTimeout(() => { if (node.parentNode) node.parentNode.removeChild(node); }, 160); }
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
    document.documentElement.classList.toggle('sidebar-collapsed', collapsed); if (document.body) document.body.classList.toggle('sidebar-collapsed', collapsed);
    const drawer = byId('mobile-sidebar-drawer'), main = byId('app-shell-main');
    if (drawer) { drawer.classList.toggle('lg:-translate-x-full', collapsed); drawer.classList.toggle('lg:translate-x-0', !collapsed); }
    if (main) { main.classList.toggle('lg:pl-0', collapsed); main.classList.toggle('lg:pl-64', !collapsed); }
  }
  function syncSidebarToggleA11y() {
    const btn = byId('mobile-sidebar-toggle'), drawer = byId('mobile-sidebar-drawer'), collapsed = document.documentElement.classList.contains('sidebar-collapsed') || (document.body && document.body.classList.contains('sidebar-collapsed'));
    if (btn) btn.setAttribute('aria-expanded', (isDesktop() ? !collapsed : Boolean(drawer && !drawer.classList.contains('-translate-x-full'))) ? 'true' : 'false');
  }
  function restoreSidebarState() { let collapsed = document.documentElement.classList.contains('sidebar-collapsed'); try { const saved = localStorage.getItem(SIDEBAR_KEY); if (saved !== null) collapsed = saved === 'true' || saved === '1'; } catch (e) {} applyDesktopSidebarClasses(collapsed); syncSidebarToggleA11y(); }
  function setMobileSidebar(open) {
    const drawer = byId('mobile-sidebar-drawer'), backdrop = byId('mobile-sidebar-backdrop');
    if (drawer) { drawer.classList.toggle('-translate-x-full', !open); drawer.classList.toggle('translate-x-0', open); }
    if (backdrop) backdrop.classList.toggle('hidden', !open);
    syncBodyScrollLock(); syncSidebarToggleA11y();
  }
  const openMobileSidebar = () => setMobileSidebar(true), closeMobileSidebar = () => setMobileSidebar(false);
  function setDesktopCollapsed(collapsed) { applyDesktopSidebarClasses(collapsed); try { localStorage.setItem(SIDEBAR_KEY, collapsed ? 'true' : 'false'); } catch (e) {} syncSidebarToggleA11y(); setTimeout(() => window.dispatchEvent(new Event('resize')), 220); }
  function toggleSidebar() { if (isDesktop()) { setDesktopCollapsed(!(document.documentElement.classList.contains('sidebar-collapsed') || (document.body && document.body.classList.contains('sidebar-collapsed')))); return; } setMobileSidebar(!(byId('mobile-sidebar-drawer') && !byId('mobile-sidebar-drawer').classList.contains('-translate-x-full'))); }
  const closeSidebarAny = () => (isDesktop() ? setDesktopCollapsed(true) : closeMobileSidebar());
  function syncThemeButton() {
    const isDark = document.documentElement.classList.contains('dark');
    if (byId('theme-toggle-btn')) byId('theme-toggle-btn').setAttribute('aria-pressed', isDark ? 'true' : 'false');
    if (byId('theme-icon-sun')) byId('theme-icon-sun').classList.toggle('hidden', !isDark);
    if (byId('theme-icon-moon')) byId('theme-icon-moon').classList.toggle('hidden', isDark); if (byId('theme-toggle-label')) byId('theme-toggle-label').textContent = isDark ? 'Light' : 'Dark';
  }
  function toggleTheme() {
    const doc = document.documentElement, nextTheme = doc.classList.contains('dark') ? 'light' : 'dark';
    if (typeof window.applyEduPredictThemePrefs === 'function') { window.applyEduPredictThemePrefs({ mode: nextTheme }); return; }
    doc.classList.add('theme-transitioning'); doc.classList.toggle('dark', nextTheme === 'dark');
    try { localStorage.setItem(THEME_KEY, nextTheme); } catch (e) {}
    syncThemeButton(); window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: nextTheme } }));
    setTimeout(() => doc.classList.remove('theme-transitioning'), 260);
  }
  function closeNotificationDropdown() { if (byId('notification-dropdown')) byId('notification-dropdown').classList.add('hidden'); if (byId('notification-bell-btn')) byId('notification-bell-btn').setAttribute('aria-expanded', 'false'); }
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
        if (searchEmptyEl) searchEmptyEl.classList.toggle('hidden', total > 0 || entries.length === 0);
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
      const refreshSearchText = () => { if (!entries.length) { const dR = Array.from(container.querySelectorAll('tbody tr[data-page-item]')), mC = Array.from(container.querySelectorAll('[data-mobile-card][data-page-item]')), n = Math.max(dR.length, mC.length); for (let i = 0; i < n; i++) entries.push({ nodes: [dR[i], mC[i]].filter(Boolean), searchText: '' }); } entries.forEach((e) => { e.searchText = e.nodes.map((n) => n.textContent || '').join(' ').toLowerCase(); }); renderPage(); };
      container._paginationController = { applySearch: (q) => { query = String(q || '').trim().toLowerCase(); currentPage = 1; renderPage(); }, sortEntries, refreshSearchText };
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
    table.querySelectorAll('tbody tr, [data-searchable-item], [data-faq-item]').forEach((row) => { if (!row.hasAttribute('data-empty-row')) row.classList.toggle('hidden', Boolean(q) && (row.textContent || '').toLowerCase().indexOf(q) === -1); });
  }
  function bindTableSearch() {
    document.querySelectorAll('input[data-table-search]').forEach((input) => {
      bindOnce(input, 'input', (e) => {
        if (e.isComposing || e.keyCode === 229) return;
        const q = input.value.trim().toLowerCase(), targetEl = byId(input.getAttribute('data-table-search'));
        if (targetEl) {
          const container = targetEl.hasAttribute('data-paginated-container') ? targetEl : targetEl.closest('[data-paginated-container]');
          if (container?._paginationController) container._paginationController.applySearch(q); else filterPlainTable(targetEl, q);
          return;
        }
        paginatedControllers.forEach((ctrl) => ctrl.applySearch(q));
        document.querySelectorAll('table[data-searchable-table], main table').forEach((t) => { if (!t.closest('[data-paginated-container]')) filterPlainTable(t, q); });
        document.querySelectorAll('[data-directory-cards-view] [data-mobile-card], [data-searchable-item], [data-faq-item]').forEach((el) => { if (!el.closest('[data-paginated-container]')) el.classList.toggle('hidden', Boolean(q) && (el.textContent || '').toLowerCase().indexOf(q) === -1); });
      });
      bindOnce(input, 'keydown', (e) => {
        if (e.isComposing || e.keyCode === 229 || e.key !== 'Enter') return;
        const hasMatch = Boolean(paginatedControllers.length && document.querySelector('[data-page-item]:not(.hidden)')) || Array.from(document.querySelectorAll('table[data-searchable-table] tbody tr:not([data-empty-row]):not(.hidden), main table tbody tr:not([data-empty-row]):not(.hidden), [data-directory-cards-view] [data-mobile-card]:not(.hidden), [data-searchable-item]:not(.hidden), [data-faq-item]:not(.hidden)')).some((el) => !el.closest('[data-ep-modal].hidden'));
        if (!hasMatch && typeof window.openCommandSearchModal === 'function') { e.preventDefault(); window.openCommandSearchModal(input.value); }
      });
    });
  }
  function closeModalById(id) {
    if (id === 'confirm-modal') closeConfirmModal(); else if (id === 'form-modal') closeFormModal(); else if (id === 'coming-soon-modal') closeComingSoonModal();
    else if (id === 'theme-studio-modal' && typeof window.closeThemeStudioModal === 'function') window.closeThemeStudioModal(); else if (id === 'page-guide-modal' && typeof window.closePageGuideModal === 'function') window.closePageGuideModal(); else setModalOpen(byId(id), false);
  }
  const openCustomModal = (id) => setModalOpen(byId(id), true);
  const closeCustomModal = (id) => setModalOpen(byId(id), false);
  const closeAllModals = () => { MODAL_IDS.forEach(closeModalById); document.querySelectorAll('[data-ep-modal]').forEach((m) => setModalOpen(m, false)); };
  function bindModalBackdrops() {
    const attach = (m, fn) => bindOnce(m, 'click', (e) => { if (pointerDownTarget === e.target && (e.target === m || e.target.hasAttribute('data-modal-backdrop'))) fn(); });
    MODAL_IDS.forEach((id) => attach(byId(id), () => closeModalById(id))); document.querySelectorAll('[data-ep-modal]').forEach((m) => attach(m, () => setModalOpen(m, false)));
  }
  function bindDynamicControls() {
    restoreSidebarState(); syncThemeButton();
    bindOnce(byId('theme-toggle-btn'), 'click', toggleTheme); bindOnce(byId('mobile-sidebar-toggle'), 'click', toggleSidebar);
    bindOnce(byId('mobile-sidebar-close'), 'click', closeSidebarAny); bindOnce(byId('mobile-sidebar-backdrop'), 'click', closeMobileSidebar);
    bindOnce(byId('notification-bell-btn'), 'click', (e) => {
      e.stopPropagation(); const dropdown = byId('notification-dropdown'), bell = byId('notification-bell-btn');
      if (!dropdown || !bell) return;
      const open = dropdown.classList.contains('hidden'); dropdown.classList.toggle('hidden', !open); bell.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    bindOnce(byId('mark-notifications-read-btn'), 'click', () => {
      const token = getCsrfToken();
      if (typeof fetch === 'function') fetch('/notifications/mark-read/', { method: 'POST', headers: token ? { 'X-CSRFToken': token } : {}, credentials: 'same-origin' }).catch(function () {});
      if (byId('notification-unread-badge')) { byId('notification-unread-badge').classList.add('hidden'); byId('notification-unread-badge').textContent = '0'; }
      if (byId('notification-list')) byId('notification-list').innerHTML = '<div class="px-4 py-6 text-center text-xs text-[var(--text-muted)]">No new alerts.</div>';
      closeNotificationDropdown(); showToast('All alerts marked as read.', 'info');
    });
    initPaginatedContainers(); initSortableTables(); bindTableSearch(); bindModalBackdrops();
    const toastContainer = byId('toast-container'); if (toastContainer) toastContainer.querySelectorAll('[data-toast]').forEach((node) => setTimeout(() => removeToastNode(node), 5000));
  }
  function bindDocumentGlobalsOnce() {
    if (globalsBound) return;
    globalsBound = true;
    document.addEventListener('pointerdown', (e) => { pointerDownTarget = e.target; });
    window.addEventListener('themeChanged', syncThemeButton);
    document.addEventListener('click', (e) => {
      const dropdown = byId('notification-dropdown'), bell = byId('notification-bell-btn');
      if (dropdown && bell && !dropdown.contains(e.target) && !bell.contains(e.target)) closeNotificationDropdown();
      const passBtn = e.target.closest('[data-password-toggle]');
      if (passBtn) {
        const container = passBtn.closest('.relative') || passBtn.parentElement, input = container ? container.querySelector('input') : null, icon = passBtn.querySelector('i');
        if (input) { const show = input.type === 'password'; input.type = show ? 'text' : 'password'; if (icon) { icon.classList.toggle('fa-eye', !show); icon.classList.toggle('fa-eye-slash', show); } }
        return;
      }
      const comingTrigger = e.target.closest('[data-coming-soon]');
      if (comingTrigger) {
        e.preventDefault(); if (!isDesktop()) closeMobileSidebar();
        openComingSoonModal({ title: comingTrigger.getAttribute('data-coming-title') || comingTrigger.textContent.trim(), panel: comingTrigger.getAttribute('data-coming-panel') || 'Coming Soon', desc: comingTrigger.getAttribute('data-coming-desc') || '', features: comingTrigger.getAttribute('data-coming-features') || '' });
        return;
      }
      if (e.target.closest('#mobile-sidebar-drawer a[href]') && !isDesktop()) closeMobileSidebar();
    });
    document.addEventListener('keydown', (e) => { if (!e.isComposing && e.keyCode !== 229 && e.key === 'Escape') { closeAllModals(); closeMobileSidebar(); closeNotificationDropdown(); } });
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
  function reinitEduPredictUI() { closeAllModals(); closeNotificationDropdown(); if (typeof window.eduPredictCancelUpload === 'function') window.eduPredictCancelUpload(true); if (typeof window.resetEduPredictSubmitLocks === 'function') window.resetEduPredictSubmitLocks(); bindDynamicControls(); if (typeof window.initSmartAutomation === 'function') window.initSmartAutomation(); if (typeof window.initEduPredictWidgets === 'function') window.initEduPredictWidgets(); if (typeof window.initDotKpiCards === 'function') window.initDotKpiCards(); if (typeof window.initPageGuidesShell === 'function') window.initPageGuidesShell(); }
  function initShellBindings() { bindDocumentGlobalsOnce(); bindDynamicControls(); }
  restoreSidebarState();
  Object.assign(window, { openConfirmModal, closeConfirmModal, openFormModal, closeFormModal, openViewDetailsModal, openComingSoonModal, closeComingSoonModal, openCustomModal, closeCustomModal, showToast, toggleTheme, openMobileSidebar, closeMobileSidebar, toggleSidebar, closeSidebarAny, syncBodyScrollLock, reinitEduPredictUI });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initShellBindings);
  else initShellBindings();
})();
