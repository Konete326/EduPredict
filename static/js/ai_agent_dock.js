(function () {
  const CHAT_ENDPOINT = '/ai-agents/chat/', SESSION_KEY = 'ep_ai_active_session', PENDING_DOM_KEY = 'ep_ai_pending_dom_action';
  const RING_CLS = ['ring-2', 'ring-[var(--accent-primary)]', 'ring-offset-2', 'ring-offset-[var(--bg-surface)]', 'scale-105'];
  const PREFILL_CLS = ['ring-2', 'ring-[var(--accent-primary)]', 'bg-[var(--accent-soft)]'];
  const SVG_NS = ['http:', '', 'www.w3.org', '2000', 'svg'].join('/');
  const mkSvgDp = (c1, c2, shape) => 'data:image/svg+xml;utf8,' + encodeURIComponent('<svg xmlns="' + SVG_NS + '" viewBox="0 0 40 40"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="' + c1 + '"/><stop offset="100%" stop-color="' + c2 + '"/></linearGradient></defs><rect width="40" height="40" rx="20" fill="url(#g)"/>' + shape + '</svg>');
  const AGENT_ALIASES = { amina: 'coach', zain: 'analyst', sara: 'ops', bilal: 'desk' };
  const AGENTS = {
    coach: { id: 'coach', name: 'EduCoach AI', role: 'Academic & Study Advisor', shortRole: 'Study Advisor', accent: '#16a34a', avatar_url: mkSvgDp('#16a34a', '#059669', '<path d="M20 11L9 16l11 5 11-5-11-5zm-6 7.5v4.5c0 1.8 2.7 3 6 3s6-1.2 6-3v-4.5l-6 2.8-6-2.8z" fill="#ffffff"/>'), intro: 'Assalam-o-Alaikum! I am EduCoach AI. Ask about GPA, attendance recovery, coursework, or study plans.' },
    analyst: { id: 'analyst', name: 'PulseML AI', role: 'Predictive Risk & Data Agent', shortRole: 'Risk & Data', accent: '#2563eb', avatar_url: mkSvgDp('#2563eb', '#1d4ed8', '<path d="M10 26h20M11 22l5-6 4.5 3.5L28 13" fill="none" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="28" cy="13" r="2.4" fill="#ffffff"/>'), intro: 'Hello! I am PulseML AI. Ask about dropout risk scores, model metrics, anomalies, or predictions.' },
    ops: { id: 'ops', name: 'CourseOps AI', role: 'Course, Roster & Marks Agent', shortRole: 'Courses & Marks', accent: '#d97706', avatar_url: mkSvgDp('#d97706', '#b45309', '<rect x="12" y="11" width="16" height="18" rx="3" fill="none" stroke="#ffffff" stroke-width="2.3"/><path d="M16 11h8v3h-8z" fill="#ffffff"/><path d="M16 20l2.5 2.5L24 17" fill="none" stroke="#ffffff" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/>'), intro: 'Hi! I am CourseOps AI. Ask about course capacity, class rosters, or CSV/Excel marks uploads.' },
    desk: { id: 'desk', name: 'HelpDesk AI', role: 'Portal Guide, PDF & Support Agent', shortRole: 'Portal Support', accent: '#dc2626', avatar_url: mkSvgDp('#dc2626', '#b91c1c', '<path d="M12 21v-2a8 8 0 0 1 16 0v2" fill="none" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round"/><rect x="10" y="19" width="4" height="7" rx="2" fill="#ffffff"/><rect x="26" y="19" width="4" height="7" rx="2" fill="#ffffff"/><path d="M28 26c0 2.2-1.8 3.5-4.5 3.5H20" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round"/>'), intro: 'Hi! I am HelpDesk AI. Ask about A4 PDF transcripts, help tickets, profile settings, or passwords.' }
  };
  let ephemeralMessages = [], activeAgentId = null, isDockOpen = false, isChatOpen = false, isSending = false, sessionSeq = 0, lastEngine = 'live';
  const byId = (id) => document.getElementById(id);
  const mk = (tag, cls, text, attrs) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined && text !== null) n.textContent = String(text); if (attrs) Object.keys(attrs).forEach((k) => n.setAttribute(k, attrs[k])); return n; };
  const getEls = () => ({ root: byId('ep-agent-dock-root'), toggleBtn: byId('ep-agent-dock-toggle'), dockBar: byId('ep-message-dock'), chatPanel: byId('ep-agent-chat-panel'), stream: byId('ep-zig-zag-stream'), form: byId('ep-dock-form'), input: byId('ep-dock-input'), sendBtn: byId('ep-dock-send'), clearBtn: byId('ep-dock-clear-btn'), closeBtn: byId('ep-dock-close-btn'), chatDp: byId('ep-chat-agent-dp'), nameEl: byId('ep-chat-agent-name'), roleEl: byId('ep-chat-agent-role'), engBadge: byId('ep-dock-engine-badge'), engDot: byId('ep-dock-engine-dot'), engLabel: byId('ep-dock-engine-label') });
  const getCsrfToken = () => { const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/); return m ? decodeURIComponent(m[1]) : (document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || ''); };
  const formatTime = () => { const d = new Date(); return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0'); };
  const normPath = (p) => { const s = String(p || '').split('?')[0].split('#')[0]; return s.length > 1 && s.endsWith('/') ? s.slice(0, -1) : (s || '/'); };
  const currentPath = () => normPath((window.location && window.location.pathname) || '/');
  const resolveAgentId = (rawId) => { const k = String(rawId || '').trim().toLowerCase(), m = AGENT_ALIASES[k] || k; return AGENTS[m] ? m : 'coach'; };
  const normalizeAgent = (raw) => { const id = resolveAgentId(raw && raw.id ? raw.id : 'coach'), base = AGENTS[id]; return (!raw || typeof raw !== 'object') ? base : { id, name: raw.name || base.name, role: raw.role || base.role, shortRole: raw.shortRole || base.shortRole, accent: raw.accent || base.accent, avatar_url: raw.avatar_url || base.avatar_url, intro: raw.intro || base.intro }; };
  const toggleFlexPanel = (node, open) => { if (!node) return; node.classList.toggle('hidden', !open); node.classList.toggle('flex', Boolean(open)); node.setAttribute('aria-hidden', open ? 'false' : 'true'); };
  const makeEvent = (name) => (typeof Event === 'function' ? new Event(name, { bubbles: true }) : { type: name, bubbles: true });
  const schedulePendingRun = () => { if (typeof setTimeout === 'function') setTimeout(consumePendingDomAction, 85); else consumePendingDomAction(); };
  const isFallbackEngine = (eng) => String(eng || '').toLowerCase().startsWith('fallback:');
  const saveActiveSession = () => { try { if (window.sessionStorage) window.sessionStorage.setItem(SESSION_KEY, JSON.stringify({ messages: ephemeralMessages.slice(-40), activeAgentId, isDockOpen, isChatOpen, lastEngine })); } catch (e) {} };
  const clearActiveSession = () => { try { if (window.sessionStorage) { window.sessionStorage.removeItem(SESSION_KEY); window.sessionStorage.removeItem(PENDING_DOM_KEY); } } catch (e) {} };
  const queuePendingAction = (act) => { try { if (window.sessionStorage && act) window.sessionStorage.setItem(PENDING_DOM_KEY, JSON.stringify(act)); } catch (e) {} };
  const pushStreamNode = (stream, node) => { if (!stream) return; const e = stream.querySelector('[data-dock-empty]'); if (e && e.parentNode) e.parentNode.removeChild(e); stream.appendChild(node); stream.scrollTop = stream.scrollHeight || 0; };
  const setChatOpen = (open) => { isChatOpen = Boolean(open); toggleFlexPanel(getEls().chatPanel, isChatOpen); };
  const removeTypingBubble = () => { const s = getEls().stream, n = s ? s.querySelector('[data-dock-typing]') : null; if (n && n.parentNode) n.parentNode.removeChild(n); };
  const highlightInputs = (nodes) => { nodes.forEach((i) => PREFILL_CLS.forEach((c) => i.classList.add(c))); if (typeof setTimeout === 'function' && nodes.length) setTimeout(() => nodes.forEach((i) => PREFILL_CLS.forEach((c) => i.classList.remove(c))), 2200); };

  function updateEngineBadge(engine) {
    lastEngine = String(engine || 'live');
    const el = getEls(), low = lastEngine.toLowerCase();
    if (!el.engBadge || !el.engDot || !el.engLabel) return;
    const isFb = low.startsWith('fallback:'), isGuard = low.startsWith('guard:') || low.startsWith('rbac:');
    el.engBadge.title = 'Engine: ' + lastEngine;
    el.engBadge.className = 'inline-flex shrink-0 items-center gap-1 font-medium ' + (isFb ? 'text-[var(--status-warning)]' : (isGuard ? 'text-[var(--accent-primary)]' : 'text-[var(--status-success)]'));
    el.engDot.className = 'h-1.5 w-1.5 rounded-full ' + (isFb ? 'bg-[var(--status-warning)]' : (isGuard ? 'bg-[var(--accent-primary)]' : 'bg-[var(--status-success)]'));
    el.engLabel.textContent = isFb ? 'Offline Mode' : (isGuard ? 'Policy Guard' : 'Live AI');
  }
  function navigateToUrl(rawUrl, forceDirect) {
    if (!rawUrl) return;
    saveActiveSession();
    try {
      const target = new URL(rawUrl, (window.location && window.location.origin) || (['http:', '', 'localhost'].join('/'))), low = target.pathname.toLowerCase();
      const isFile = forceDirect || low.includes('/backup') || low.includes('download') || low.includes('export-pdf') || low.endsWith('.pdf') || low.endsWith('.csv');
      if (!isFile && typeof window.eduPredictNavigate === 'function') { window.eduPredictNavigate(target, { pushState: true, bypassCache: false }); return; }
      if (window.location && typeof window.location.assign === 'function') window.location.assign(target.href);
      else if (window.location) window.location.href = target.href;
    } catch (e) { if (window.location) window.location.href = rawUrl; }
  }
  function renderEmptyState(stream) {
    if (!stream) return;
    stream.textContent = '';
    const box = mk('div', 'flex h-full flex-col items-center justify-center gap-1.5 px-4 text-center text-[var(--text-muted)]', null, { 'data-dock-empty': 'true' });
    box.append(mk('i', 'fa-solid fa-comments text-lg text-[var(--accent-primary)]', null, { 'aria-hidden': 'true' }), mk('p', 'text-xs font-medium text-[var(--text-primary)]', 'Pick an EduPredict AI Agent'), mk('p', 'text-[11px] leading-relaxed', 'Select an agent below or type your request. Specialists auto-route and can run portal actions.'));
    stream.appendChild(box);
  }
  function updateAgentVisuals(agent) {
    const el = getEls(), viewAgent = agent || AGENTS.coach;
    if (!el.root) return;
    el.root.querySelectorAll('[data-dock-agent]').forEach((btn) => {
      const bid = resolveAgentId(btn.getAttribute('data-dock-agent')), active = Boolean(agent && bid === agent.id), av = btn.querySelector('[data-dock-avatar]');
      btn.setAttribute('aria-pressed', active ? 'true' : 'false');
      RING_CLS.forEach((cls) => btn.classList.toggle(cls, active));
      if (av && AGENTS[bid]) { av.src = AGENTS[bid].avatar_url; av.alt = AGENTS[bid].name; }
    });
    if (el.chatDp) { el.chatDp.src = viewAgent.avatar_url; el.chatDp.alt = viewAgent.name; }
    if (el.nameEl) el.nameEl.textContent = viewAgent.name;
    if (el.roleEl) el.roleEl.textContent = viewAgent.role;
    if (el.input) el.input.placeholder = agent ? ('Ask ' + agent.name + '...') : 'Select an agent or type a message...';
  }
  function resetConversation(clearActive) { const el = getEls(); sessionSeq += 1; ephemeralMessages = []; isSending = false; if (el.sendBtn) el.sendBtn.disabled = false; renderEmptyState(el.stream); updateEngineBadge('live'); if (clearActive) { activeAgentId = null; updateAgentVisuals(null); } }
  function setDockOpen(open) {
    const el = getEls(); isDockOpen = Boolean(open); toggleFlexPanel(el.dockBar, isDockOpen);
    if (el.toggleBtn) el.toggleBtn.setAttribute('aria-expanded', isDockOpen ? 'true' : 'false');
    if (!isDockOpen) { setChatOpen(false); resetConversation(true); clearActiveSession(); } else saveActiveSession();
  }
  function populateModalFields(modalNode, fields) {
    if (!modalNode || !fields || typeof fields !== 'object') return;
    const keys = Object.keys(fields), first = ['role', 'course_code', 'full_name'], touched = [];
    keys.filter((k) => first.includes(k)).concat(keys.filter((k) => !first.includes(k))).forEach((k) => {
      const inp = modalNode.querySelector('[name="' + k + '"]'); if (!inp) return;
      inp.value = fields[k] == null ? '' : String(fields[k]);
      if (typeof inp.dispatchEvent === 'function') { inp.dispatchEvent(makeEvent('input')); inp.dispatchEvent(makeEvent('change')); }
      touched.push(inp);
    });
    if (touched.length) highlightInputs(touched);
    const submitBtn = modalNode.querySelector('button[type="submit"], #form-modal-submit-btn');
    if (submitBtn && typeof submitBtn.focus === 'function') submitBtn.focus();
  }
  function runOpenAndFillForm(act, retryDone) {
    const kind = String(act.form_kind || '').toLowerCase(), fields = act.fields || {};
    if (act.route && normPath(act.route) !== currentPath()) { queuePendingAction(act); navigateToUrl(act.route); return; }
    let modal = null, opened = false;
    if (kind === 'support_ticket') {
      if (typeof window.openSupportTicketModal === 'function') { window.openSupportTicketModal({ reset: true, subject: fields.subject || '', message: fields.message || '' }); opened = true; }
      else if (typeof window.openCustomModal === 'function') { window.openCustomModal('support-ticket-modal'); opened = true; }
      modal = byId('support-ticket-modal');
    } else if (kind === 'profile_update') {
      if (typeof window.openProfileCustomModal === 'function') { window.openProfileCustomModal('profile-edit-modal'); opened = true; }
      else if (typeof window.openCustomModal === 'function') { window.openCustomModal('profile-edit-modal'); opened = true; }
      modal = byId('profile-edit-modal');
    } else if (kind === 'quick_marks' && typeof window.openQuickEntryModal === 'function') { window.openQuickEntryModal(); modal = byId('form-modal'); opened = true; }
    else if (kind === 'create_course' && typeof window.openCreateCourseModal === 'function') { window.openCreateCourseModal(); modal = byId('form-modal'); opened = true; }
    else if (kind === 'create_user' && typeof window.openCreateUserModal === 'function') { window.openCreateUserModal(); modal = byId('form-modal'); opened = true; }
    if (!opened && !retryDone && typeof setTimeout === 'function') { setTimeout(() => runOpenAndFillForm(act, true), 140); return; }
    populateModalFields(modal || document, fields);
  }
  function clickSafeSelector(sel) {
    if (typeof sel !== 'string' || !sel.trim() || sel.length > 120 || /[<>`\\]/.test(sel)) return false;
    try {
      const target = document.querySelector(sel);
      if (!target || typeof target.click !== 'function') return false;
      if (typeof target.matches === 'function' && !target.matches('button, a, [role="button"], input[type="submit"], input[type="button"], input[type="checkbox"]')) return false;
      const href = String(target.getAttribute('href') || '').toLowerCase();
      if (href.includes('logout') || href.includes('delete')) return false;
      target.click(); return true;
    } catch (e) { return false; }
  }
  function runToggleTheme(act) {
    const mode = String((act && act.mode) || 'toggle').toLowerCase(), isDark = document.documentElement.classList.contains('dark'), desired = (mode === 'dark' || mode === 'light') ? mode : (isDark ? 'light' : 'dark');
    if (typeof window.applyEduPredictThemePrefs === 'function') { window.applyEduPredictThemePrefs({ mode: desired }); return; }
    if ((desired === 'dark') !== isDark) { const btn = byId('theme-toggle-btn'); if (btn && typeof btn.click === 'function') btn.click(); }
  }
  function runToggleSidebar(act) {
    const state = String((act && act.state) || 'toggle').toLowerCase(), btn = byId('mobile-sidebar-toggle');
    if (!btn || typeof btn.click !== 'function') return;
    const collapsed = window.innerWidth >= 1024 ? (document.documentElement.classList.contains('sidebar-collapsed') || Boolean(document.body && document.body.classList.contains('sidebar-collapsed'))) : Boolean(byId('mobile-sidebar-drawer') && byId('mobile-sidebar-drawer').classList.contains('-translate-x-full'));
    if (((state === 'collapse' || state === 'collapsed' || state === 'hide') && collapsed) || ((state === 'expand' || state === 'expanded' || state === 'open' || state === 'show') && !collapsed)) return;
    btn.click();
  }
  function runClickElement(act) {
    const cmd = String(act.action || '').toLowerCase(), goRoute = (fb) => { const r = act.route || fb; if (r && normPath(r) !== currentPath()) { queuePendingAction(Object.assign({}, act, { route: r })); navigateToUrl(r); return true; } return false; };
    if (cmd === 'print_a4_report') { if (typeof window.printOfficialA4Report === 'function') window.printOfficialA4Report(); else if (!goRoute('') && typeof window.print === 'function') window.print(); }
    else if (cmd === 'download_pdf') { const link = document.querySelector('a[href*="-pdf"], a[href*="download-pdf"], a[href*="export-pdf"], a[href*="report/pdf"], a[href*="roster/pdf"]'); if (link && typeof link.click === 'function') link.click(); else if (act.url) navigateToUrl(act.url, true); else goRoute(''); }
    else if (cmd === 'open_change_password') { if (typeof window.openChangePasswordModal === 'function') window.openChangePasswordModal(); else goRoute('/profile/'); }
    else if (cmd === 'open_theme_studio') { if (typeof window.openThemeStudioModal === 'function') window.openThemeStudioModal(); else goRoute('/admin-panel/settings/'); }
    else if (cmd === 'notify_high_risk') { if (!clickSafeSelector(act.selector || '#notify-all-high-risk-btn')) goRoute('/teacher-panel/alerts/'); }
    else if (cmd === 'run_ml') { if (!clickSafeSelector('form[action*="run-ml"] button[type="submit"], form[action*="run-predictions"] button[type="submit"], form[action*="run_predictions"] button[type="submit"]') && !clickSafeSelector(act.selector || '')) goRoute('/analyst-panel/'); }
    else if (cmd === 'simulate_stream') { if (!clickSafeSelector(act.selector || '#live-stream-toggle-btn')) goRoute('/analyst-panel/'); }
    else if (cmd === 'export_backup') { const link = document.querySelector('a[href*="/admin-panel/backup"]'); if (link && typeof link.click === 'function') link.click(); else navigateToUrl(act.url || '/admin-panel/backup/?format=json', true); }
    else if (act.selector) { if (act.route && normPath(act.route) !== currentPath()) { goRoute(act.route); return; } clickSafeSelector(act.selector); }
  }
  function runSingleDomAction(act) {
    if (!act || typeof act !== 'object') return;
    if (act.type === 'redirect' && act.url) { navigateToUrl(act.url); return; }
    if (act.type === 'toggle_theme') { runToggleTheme(act); return; }
    if (act.type === 'toggle_sidebar') { runToggleSidebar(act); return; }
    if (act.type === 'filter_table') {
      if (act.route && normPath(act.route) !== currentPath()) { queuePendingAction(act); navigateToUrl(act.route); return; }
      const inputs = Array.from(document.querySelectorAll('input[data-table-search]')), target = inputs.find((n) => !n.closest('.hidden')) || inputs[0];
      if (target) { target.value = act.query || ''; if (typeof target.dispatchEvent === 'function') target.dispatchEvent(makeEvent('input')); highlightInputs([target]); if (typeof window.showToast === 'function') window.showToast('Filtered by "' + (act.query || '') + '"', 'info'); }
      return;
    }
    if (act.type === 'click_element') { runClickElement(act); return; }
    if (act.type === 'open_and_fill_form') runOpenAndFillForm(act, false);
  }
  function executeDomActions(actions) {
    const list = Array.isArray(actions) ? actions.filter(Boolean) : (actions ? [actions] : []);
    if (!list.length) return;
    const redirIdx = list.findIndex((a) => a.type === 'redirect' && a.url);
    if (redirIdx !== -1) {
      const redir = list[redirIdx], trailing = list.slice(redirIdx + 1);
      if (trailing.length) queuePendingAction(trailing.length === 1 ? trailing[0] : trailing);
      if (normPath(redir.url) !== currentPath()) { navigateToUrl(redir.url); return; }
      consumePendingDomAction(); return;
    }
    list.forEach(runSingleDomAction);
  }
  function consumePendingDomAction() {
    try { if (!window.sessionStorage) return; const raw = window.sessionStorage.getItem(PENDING_DOM_KEY); if (!raw) return; window.sessionStorage.removeItem(PENDING_DOM_KEY); executeDomActions(JSON.parse(raw)); } catch (e) {}
  }
  function renderActionChips(bubble, actions) {
    if (!bubble || !Array.isArray(actions) || !actions.length) return;
    const wrap = mk('div', 'mt-2 flex flex-wrap gap-1.5'), icons = { redirect: 'fa-solid fa-arrow-up-right-from-square', filter_table: 'fa-solid fa-filter', click_element: 'fa-solid fa-bolt', open_and_fill_form: 'fa-solid fa-pen-to-square', toggle_theme: 'fa-solid fa-circle-half-stroke', toggle_sidebar: 'fa-solid fa-bars-staggered' };
    actions.forEach((act) => {
      if (!act || !act.type) return;
      const chip = mk('button', 'inline-flex items-center gap-1 rounded-full border border-[var(--border-subtle)] bg-[var(--bg-canvas)] px-2.5 py-1 text-[10px] font-semibold text-[var(--accent-primary)] transition-colors hover:border-[var(--accent-primary)] hover:bg-[var(--accent-soft)]', null, { type: 'button', 'data-dom-action-chip': 'true' });
      chip.append(mk('i', (icons[act.type] || 'fa-solid fa-play') + ' text-[9px]', null, { 'aria-hidden': 'true' }), mk('span', '', act.label || act.type));
      chip.addEventListener('click', () => executeDomActions([act]));
      wrap.appendChild(chip);
    });
    if (wrap.children.length) bubble.appendChild(wrap);
  }
  function appendUserBubble(text, timeOverride, skipStore) {
    const el = getEls(), time = timeOverride || formatTime(); if (!el.stream) return;
    if (!skipStore) { ephemeralMessages.push({ side: 'right', text, time }); saveActiveSession(); }
    const row = mk('div', 'flex justify-end', null, { 'data-dock-msg': 'user', 'data-msg-side': 'right' }), bubble = mk('div', 'ml-auto max-w-[82%] rounded-2xl rounded-br-none bg-[var(--accent-primary)] px-3.5 py-2 text-xs text-white shadow-sm'), meta = mk('div', 'mt-1 flex items-center justify-end gap-1 text-[10px] text-white/80');
    meta.append(mk('span', '', time), mk('span', '', '✓✓'));
    bubble.append(mk('p', 'whitespace-pre-wrap break-words leading-relaxed', text), meta);
    row.appendChild(bubble); pushStreamNode(el.stream, row);
  }
  function appendAgentBubble(agentObj, text, continuePrefix, domActions, timeOverride, skipStore, metaOpts) {
    const el = getEls(), agent = normalizeAgent(agentObj), time = timeOverride || formatTime(), actions = Array.isArray(domActions) ? domActions : [], opts = metaOpts || {}, eng = opts.engine || '', retryPrompt = opts.retryPrompt || '';
    if (!el.stream) return;
    if (!skipStore) { ephemeralMessages.push({ side: 'left', agentId: agent.id, text, continuePrefix: continuePrefix || '', domActions: actions, time, engine: eng, retryPrompt }); saveActiveSession(); }
    const row = mk('div', 'flex justify-start', null, { 'data-dock-msg': 'agent', 'data-msg-side': 'left', 'data-agent-id': agent.id }), bubble = mk('div', 'mr-auto max-w-[86%] rounded-2xl rounded-bl-none border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3.5 py-2.5 text-xs text-[var(--text-primary)] shadow-sm');
    const head = mk('div', 'mb-1 flex items-center gap-1.5 text-[11px] font-semibold'), badgeLbl = mk('span', '', agent.name + ' · ' + agent.shortRole);
    badgeLbl.style.color = agent.accent;
    head.append(mk('img', 'h-5 w-5 rounded-full object-cover shrink-0', null, { src: agent.avatar_url, alt: agent.name }), badgeLbl);
    bubble.appendChild(head);
    if (continuePrefix) bubble.appendChild(mk('p', 'mb-1 font-semibold leading-snug text-[var(--text-primary)]', continuePrefix));
    bubble.appendChild(mk('p', 'whitespace-pre-wrap break-words leading-relaxed text-[var(--text-primary)]', text));
    renderActionChips(bubble, actions);
    if (isFallbackEngine(eng)) {
      const fb = mk('div', 'mt-2 flex items-center justify-between gap-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-canvas)] px-2 py-1 text-[10px] text-[var(--text-muted)]', null, { 'data-fallback-note': 'true' });
      fb.appendChild(mk('span', '', 'Live AI busy — offline reply shown.'));
      if (retryPrompt) {
        const rBtn = mk('button', 'shrink-0 font-semibold text-[var(--accent-primary)] hover:underline', 'Retry', { type: 'button', 'data-retry-prompt': 'true' });
        rBtn.addEventListener('click', () => { const cur = getEls(); if (cur.input) cur.input.value = retryPrompt; handleSendSubmit({ preventDefault: function () {} }); });
        fb.appendChild(rBtn);
      }
      bubble.appendChild(fb);
    }
    bubble.appendChild(mk('div', 'mt-1 text-right text-[10px] text-[var(--text-muted)]', time));
    row.appendChild(bubble); pushStreamNode(el.stream, row);
  }
  function appendHandoffBanner(fromAgentObj, toAgentObj, taskPreview, skipStore) {
    const el = getEls(), fromA = normalizeAgent(fromAgentObj), toA = normalizeAgent(toAgentObj); if (!el.stream) return;
    if (!skipStore) { ephemeralMessages.push({ side: 'center', type: 'handoff', fromId: fromA.id, toId: toA.id, from: fromA.name, to: toA.name, taskPreview: taskPreview || '' }); saveActiveSession(); }
    const banner = mk('div', 'mx-auto w-full max-w-[94%] rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-2 text-center text-[11px] text-[var(--text-secondary)] space-y-0.5', null, { 'data-handoff-preview': 'true' }), line1 = mk('div', 'flex items-center justify-center gap-1.5 font-semibold text-[var(--text-primary)]');
    line1.append(mk('i', 'fa-solid fa-arrows-rotate text-[10px] text-[var(--accent-primary)]', null, { 'aria-hidden': 'true' }), mk('span', '', 'Task Reassigned: ' + fromA.name + ' -> ' + toA.name));
    banner.appendChild(line1);
    if (taskPreview) banner.appendChild(mk('p', 'line-clamp-2 break-words text-[10px] text-[var(--text-muted)]', 'Task Preview: ' + taskPreview));
    pushStreamNode(el.stream, banner);
  }
  function appendPollBubble(agentObj, poll, skipStore) {
    const el = getEls(), agent = normalizeAgent(agentObj);
    if (!el.stream || !poll || !Array.isArray(poll.options) || !poll.options.length) return;
    if (!skipStore) { ephemeralMessages.push({ side: 'left', type: 'poll', agentId: agent.id, poll }); saveActiveSession(); }
    const row = mk('div', 'flex justify-start', null, { 'data-agent-poll': 'true', 'data-agent-id': agent.id }), card = mk('div', 'mr-auto max-w-[90%] rounded-2xl rounded-bl-none border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3.5 py-2.5 text-xs text-[var(--text-primary)] shadow-sm space-y-2'), optsWrap = mk('div', 'flex flex-wrap gap-1.5');
    card.appendChild(mk('p', 'font-semibold leading-snug text-[var(--text-primary)]', poll.question || 'Choose an option:'));
    poll.options.forEach((opt) => {
      if (!opt) return;
      const prompt = opt.prompt || opt.label || '', btn = mk('button', 'inline-flex items-center gap-1 rounded-full border border-[var(--border-subtle)] bg-[var(--bg-canvas)] px-2.5 py-1 text-[11px] font-medium text-[var(--text-primary)] transition-colors hover:border-[var(--accent-primary)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent-primary)]', opt.label || prompt, { type: 'button', 'data-poll-option': 'true' });
      btn.addEventListener('click', () => { const cur = getEls(); if (cur.input) cur.input.value = prompt; handleSendSubmit({ preventDefault: function () {} }); });
      optsWrap.appendChild(btn);
    });
    card.appendChild(optsWrap); row.appendChild(card); pushStreamNode(el.stream, row);
  }
  function showTypingBubble(agent) {
    const stream = getEls().stream; if (!stream) return;
    removeTypingBubble();
    const row = mk('div', 'flex justify-start', null, { 'data-dock-typing': 'true' });
    row.appendChild(mk('div', 'mr-auto rounded-2xl rounded-bl-none border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3.5 py-2 text-[11px] text-[var(--text-muted)] shadow-sm animate-pulse', agent.name + ' is typing...'));
    pushStreamNode(stream, row);
  }
  function selectAgent(agentId, skipIntro) {
    const agent = AGENTS[resolveAgentId(agentId)] || AGENTS.coach, el = getEls();
    activeAgentId = agent.id; updateAgentVisuals(agent);
    if (!isDockOpen) setDockOpen(true);
    if (!isChatOpen) setChatOpen(true);
    if (!skipIntro && ephemeralMessages.length === 0) appendAgentBubble(agent, agent.intro); else saveActiveSession();
    if (el.input && typeof el.input.focus === 'function') el.input.focus();
  }
  const buildHistoryPayload = () => ephemeralMessages.filter((m) => m && (m.side === 'right' || (m.side === 'left' && !m.type)) && m.text).slice(-10).map((m) => ({ role: m.side === 'right' ? 'user' : 'assistant', agent_id: m.agentId || activeAgentId || 'coach', text: m.text }));
  function handleSendSubmit(e) {
    if (e && typeof e.preventDefault === 'function') e.preventDefault();
    if (isSending) return;
    const el = getEls(), rawText = el.input ? el.input.value.trim() : '';
    if (!rawText) { if (typeof window.showToast === 'function') window.showToast('Please type a message first.', 'warning'); return; }
    const targetId = resolveAgentId(activeAgentId || 'coach'), reqSeq = sessionSeq, historyPayload = buildHistoryPayload();
    selectAgent(targetId, true); if (el.input) el.input.value = '';
    appendUserBubble(rawText);
    if (typeof fetch !== 'function') return;
    isSending = true; if (el.sendBtn) el.sendBtn.disabled = true;
    showTypingBubble(AGENTS[targetId] || AGENTS.coach);
    fetch(CHAT_ENDPOINT, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken(), 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify({ agent_id: targetId, message: rawText, history: historyPayload, current_path: currentPath() })
    }).then((res) => res.json().catch(() => ({ ok: false, error: 'Unable to parse AI response.' }))).then((data) => {
      if (reqSeq !== sessionSeq || !isChatOpen) return;
      removeTypingBubble();
      if (!data || !data.ok) { appendAgentBubble(AGENTS[targetId], (data && data.error) || 'Could not process your request.'); return; }
      const actions = Array.isArray(data.dom_actions) ? data.dom_actions : [], responder = normalizeAgent(data.active_agent || AGENTS[targetId]), engine = data.engine || 'live', meta = { engine, retryPrompt: rawText };
      updateEngineBadge(engine);
      if (data.handoff === true) {
        const fromAgent = normalizeAgent(data.from_agent || AGENTS[targetId]);
        appendAgentBubble(fromAgent, data.handoff_message || ('Reassigning your request to ' + responder.name + '...'));
        appendHandoffBanner(fromAgent, responder, data.task_preview || rawText.slice(0, 110));
        selectAgent(responder.id, true);
        appendAgentBubble(responder, data.reply || '', data.continue_prefix || '', actions, null, false, meta);
      } else { if (responder.id !== activeAgentId) selectAgent(responder.id, true); appendAgentBubble(responder, data.reply || '', '', actions, null, false, meta); }
      if (data.poll) appendPollBubble(responder, data.poll);
      const autoActs = actions.filter((a) => a && a.auto);
      if (autoActs.length) executeDomActions(autoActs);
    }).catch(() => { if (reqSeq === sessionSeq && isChatOpen) { removeTypingBubble(); updateEngineBadge('fallback:network'); appendAgentBubble(AGENTS[targetId], 'Connection issue while contacting the specialist.', '', [], null, false, { engine: 'fallback:network', retryPrompt: rawText }); } })
      .finally(() => { if (reqSeq !== sessionSeq) return; isSending = false; const cur = getEls(); if (cur.sendBtn) cur.sendBtn.disabled = false; if (cur.input && typeof cur.input.focus === 'function') cur.input.focus(); });
  }
  function restoreActiveSession() {
    try {
      if (!window.sessionStorage) return;
      const raw = window.sessionStorage.getItem(SESSION_KEY); if (!raw) return;
      const st = JSON.parse(raw); if (!st || typeof st !== 'object') return;
      const el = getEls(), msgs = Array.isArray(st.messages) ? st.messages : [];
      isDockOpen = Boolean(st.isDockOpen); isChatOpen = Boolean(st.isChatOpen); activeAgentId = st.activeAgentId ? resolveAgentId(st.activeAgentId) : null;
      toggleFlexPanel(el.dockBar, isDockOpen); if (el.toggleBtn) el.toggleBtn.setAttribute('aria-expanded', isDockOpen ? 'true' : 'false');
      toggleFlexPanel(el.chatPanel, isChatOpen); updateAgentVisuals(activeAgentId ? AGENTS[activeAgentId] : null);
      if (st.lastEngine) updateEngineBadge(st.lastEngine);
      ephemeralMessages = msgs;
      if (el.stream && msgs.length) {
        el.stream.textContent = '';
        msgs.forEach((m) => {
          if (m.side === 'right') appendUserBubble(m.text, m.time, true);
          else if (m.type === 'handoff') appendHandoffBanner(AGENTS[resolveAgentId(m.fromId || m.from)], AGENTS[resolveAgentId(m.toId || m.to)], m.taskPreview, true);
          else if (m.type === 'poll') appendPollBubble(AGENTS[resolveAgentId(m.agentId)], m.poll, true);
          else if (m.side === 'left') appendAgentBubble(AGENTS[resolveAgentId(m.agentId)], m.text, m.continuePrefix, m.domActions, m.time, true, { engine: m.engine, retryPrompt: m.retryPrompt });
        });
      }
    } catch (e) {}
  }
  function bindDockDrag(el) {
    if (!el.root || !el.toggleBtn || el.toggleBtn.dataset.dragBound === '1') return;
    el.toggleBtn.dataset.dragBound = '1';
    const POS_KEY = 'ep_agent_dock_pos'; let drag = null, suppressClick = false;
    const applyPos = (r, b) => { el.root.style.right = Math.max(12, Math.min(Math.max(12, window.innerWidth - (el.root.offsetWidth || 160) - 12), r)) + 'px'; el.root.style.bottom = Math.max(12, Math.min(Math.max(12, window.innerHeight - (el.toggleBtn.offsetHeight || 44) - 12), b)) + 'px'; };
    try { const s = JSON.parse(sessionStorage.getItem(POS_KEY) || 'null'); if (s && typeof s.r === 'number' && typeof s.b === 'number') applyPos(s.r, s.b); } catch (e) {}
    el.toggleBtn.addEventListener('pointerdown', (e) => { drag = { id: e.pointerId, x: e.clientX, y: e.clientY, r: parseFloat(el.root.style.right || '16') || 16, b: parseFloat(el.root.style.bottom || '16') || 16, moved: false }; if (el.toggleBtn.setPointerCapture) el.toggleBtn.setPointerCapture(e.pointerId); });
    el.toggleBtn.addEventListener('pointermove', (e) => { if (!drag || e.pointerId !== drag.id) return; const dx = e.clientX - drag.x, dy = e.clientY - drag.y; if (Math.abs(dx) > 5 || Math.abs(dy) > 5) drag.moved = true; if (drag.moved) applyPos(drag.r - dx, drag.b - dy); });
    const endDrag = (e) => { if (!drag || e.pointerId !== drag.id) return; if (drag.moved) { suppressClick = true; try { sessionStorage.setItem(POS_KEY, JSON.stringify({ r: parseFloat(el.root.style.right || '16'), b: parseFloat(el.root.style.bottom || '16') })); } catch (err) {} } drag = null; };
    el.toggleBtn.addEventListener('pointerup', endDrag); el.toggleBtn.addEventListener('pointercancel', endDrag);
    el.toggleBtn.addEventListener('click', (e) => { if (suppressClick) { suppressClick = false; e.stopImmediatePropagation(); return; } setDockOpen(!isDockOpen); });
  }
  function initAiAgentDock() {
    const el = getEls(); if (!el.root) return;
    if (el.root.dataset.dockBound === '1') { schedulePendingRun(); return; }
    el.root.dataset.dockBound = '1';
    bindDockDrag(el);
    if (el.closeBtn) el.closeBtn.addEventListener('click', () => { setChatOpen(false); resetConversation(true); clearActiveSession(); });
    if (el.clearBtn) el.clearBtn.addEventListener('click', () => { resetConversation(false); clearActiveSession(); const cur = getEls(); if (cur.input && typeof cur.input.focus === 'function') cur.input.focus(); });
    el.root.querySelectorAll('[data-dock-agent]').forEach((btn) => btn.addEventListener('click', () => selectAgent(btn.getAttribute('data-dock-agent'), false)));
    if (el.input) el.input.addEventListener('keydown', (e) => { if ((e.isComposing || e.keyCode === 229) && e.key === 'Enter') e.preventDefault(); });
    if (el.form) el.form.addEventListener('submit', handleSendSubmit);
    restoreActiveSession(); schedulePendingRun();
  }
  function openAiAgentDock(agentId) { setDockOpen(true); if (agentId) selectAgent(resolveAgentId(agentId), false); else { const el = getEls(); if (el.input && typeof el.input.focus === 'function') el.input.focus(); } }
  const closeAiAgentDock = () => setDockOpen(false);
  if (typeof window.reinitEduPredictUI === 'function' && !window.reinitEduPredictUI._aiDockWrapped) { const orig = window.reinitEduPredictUI, wrapped = function () { orig(); initAiAgentDock(); }; wrapped._aiDockWrapped = true; window.reinitEduPredictUI = wrapped; }
  Object.assign(window, { initAiAgentDock, openAiAgentDock, closeAiAgentDock, executeAiDomActions: executeDomActions });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initAiAgentDock); else initAiAgentDock();
})();
