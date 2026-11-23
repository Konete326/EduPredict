(function () {
  const CHAT_ENDPOINT = '/ai-agents/chat/', SESSION_KEY = 'ep_ai_active_session', PENDING_DOM_KEY = 'ep_ai_pending_dom_action';
  const RING_CLS = ['ring-2', 'ring-[var(--accent-primary)]', 'ring-offset-2', 'ring-offset-[var(--bg-surface)]', 'scale-105'];
  const SVG_NS = ['http:', '', 'www.w3.org', '2000', 'svg'].join('/');
  const mkSvgDp = (c1, c2, shape) => 'data:image/svg+xml;utf8,' + encodeURIComponent('<svg xmlns="' + SVG_NS + '" viewBox="0 0 40 40"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="' + c1 + '"/><stop offset="100%" stop-color="' + c2 + '"/></linearGradient></defs><rect width="40" height="40" rx="20" fill="url(#g)"/>' + shape + '</svg>');
  const AGENT_ALIASES = { amina: 'coach', zain: 'analyst', sara: 'ops', bilal: 'desk' };
  const AGENTS = {
    coach: { id: 'coach', name: 'EduCoach AI', role: 'Academic & Study Advisor', shortRole: 'Study Advisor', accent: '#16a34a', avatar_url: mkSvgDp('#16a34a', '#059669', '<path d="M20 11L9 16l11 5 11-5-11-5zm-6 7.5v4.5c0 1.8 2.7 3 6 3s6-1.2 6-3v-4.5l-6 2.8-6-2.8z" fill="#ffffff"/>'), intro: 'Assalam-o-Alaikum! I am EduCoach AI. Ask about GPA, attendance recovery, coursework, or study plans.' },
    analyst: { id: 'analyst', name: 'PulseML AI', role: 'Predictive Risk & Data Agent', shortRole: 'Risk & Data', accent: '#2563eb', avatar_url: mkSvgDp('#2563eb', '#1d4ed8', '<path d="M10 26h20M11 22l5-6 4.5 3.5L28 13" fill="none" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="28" cy="13" r="2.4" fill="#ffffff"/>'), intro: 'Hello! I am PulseML AI. Ask about dropout risk scores, model metrics, anomalies, or predictions.' },
    ops: { id: 'ops', name: 'CourseOps AI', role: 'Course, Roster & Marks Agent', shortRole: 'Courses & Marks', accent: '#d97706', avatar_url: mkSvgDp('#d97706', '#b45309', '<rect x="12" y="11" width="16" height="18" rx="3" fill="none" stroke="#ffffff" stroke-width="2.3"/><path d="M16 11h8v3h-8z" fill="#ffffff"/><path d="M16 20l2.5 2.5L24 17" fill="none" stroke="#ffffff" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/>'), intro: 'Hi! I am CourseOps AI. Ask about course capacity, class rosters, or CSV/Excel marks uploads.' },
    desk: { id: 'desk', name: 'HelpDesk AI', role: 'Portal Guide, PDF & Support Agent', shortRole: 'Portal Support', accent: '#dc2626', avatar_url: mkSvgDp('#dc2626', '#b91c1c', '<path d="M12 21v-2a8 8 0 0 1 16 0v2" fill="none" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round"/><rect x="10" y="19" width="4" height="7" rx="2" fill="#ffffff"/><rect x="26" y="19" width="4" height="7" rx="2" fill="#ffffff"/><path d="M28 26c0 2.2-1.8 3.5-4.5 3.5H20" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round"/>'), intro: 'Hi! I am HelpDesk AI. Ask about A4 PDF transcripts, help tickets, profile settings, or passwords.' }
  };

  let ephemeralMessages = [], activeAgentId = null, isDockOpen = false, isChatOpen = false, isSending = false, sessionSeq = 0;
  const byId = (id) => document.getElementById(id);
  const mk = (tag, cls, text, attrs) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined && text !== null) n.textContent = String(text); if (attrs) Object.keys(attrs).forEach((k) => n.setAttribute(k, attrs[k])); return n; };
  const getEls = () => ({ root: byId('ep-agent-dock-root'), toggleBtn: byId('ep-agent-dock-toggle'), dockBar: byId('ep-message-dock'), chatPanel: byId('ep-agent-chat-panel'), stream: byId('ep-zig-zag-stream'), form: byId('ep-dock-form'), input: byId('ep-dock-input'), sendBtn: byId('ep-dock-send'), clearBtn: byId('ep-dock-clear-btn'), closeBtn: byId('ep-dock-close-btn'), chatDp: byId('ep-chat-agent-dp'), nameEl: byId('ep-chat-agent-name'), roleEl: byId('ep-chat-agent-role') });
  const getCsrfToken = () => { const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/); return m ? decodeURIComponent(m[1]) : (document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || ''); };
  const formatTime = () => { const d = new Date(); return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0'); };
  const normPath = (p) => { const s = String(p || '').split('?')[0].split('#')[0]; return s.length > 1 && s.endsWith('/') ? s.slice(0, -1) : (s || '/'); };
  const currentPath = () => normPath((window.location && window.location.pathname) || '/');
  const resolveAgentId = (rawId) => { const k = String(rawId || '').trim().toLowerCase(), m = AGENT_ALIASES[k] || k; return AGENTS[m] ? m : 'coach'; };
  const normalizeAgent = (raw) => { const id = resolveAgentId(raw && raw.id ? raw.id : 'coach'), base = AGENTS[id]; return (!raw || typeof raw !== 'object') ? base : { id, name: raw.name || base.name, role: raw.role || base.role, shortRole: raw.shortRole || base.shortRole, accent: raw.accent || base.accent, avatar_url: raw.avatar_url || base.avatar_url, intro: raw.intro || base.intro }; };
  const toggleFlexPanel = (node, open) => { if (!node) return; node.classList.toggle('hidden', !open); node.classList.toggle('flex', Boolean(open)); node.setAttribute('aria-hidden', open ? 'false' : 'true'); };
  const makeEvent = (name) => (typeof Event === 'function' ? new Event(name, { bubbles: true }) : { type: name, bubbles: true });
  const schedulePendingRun = () => { if (typeof setTimeout === 'function') setTimeout(consumePendingDomAction, 35); else consumePendingDomAction(); };

  function saveActiveSession() { try { if (window.sessionStorage) window.sessionStorage.setItem(SESSION_KEY, JSON.stringify({ messages: ephemeralMessages.slice(-40), activeAgentId, isDockOpen, isChatOpen })); } catch (e) {} }
  function clearActiveSession() { try { if (window.sessionStorage) { window.sessionStorage.removeItem(SESSION_KEY); window.sessionStorage.removeItem(PENDING_DOM_KEY); } } catch (e) {} }
  function queuePendingAction(act) { try { if (window.sessionStorage && act) window.sessionStorage.setItem(PENDING_DOM_KEY, JSON.stringify(act)); } catch (e) {} }
  function navigateToUrl(rawUrl) {
    if (!rawUrl) return;
    saveActiveSession();
    try {
      const target = new URL(rawUrl, (window.location && window.location.origin) || (['http:', '', 'localhost'].join('/')));
      if (typeof window.eduPredictNavigate === 'function') { window.eduPredictNavigate(target, { pushState: true, bypassCache: false }); return; }
      if (window.location && typeof window.location.assign === 'function') window.location.assign(target.href);
    } catch (e) { if (window.location && typeof window.location.assign === 'function') window.location.assign(rawUrl); }
  }

  function renderEmptyState(stream) {
    if (!stream) return;
    stream.textContent = '';
    const box = mk('div', 'flex h-full flex-col items-center justify-center gap-1.5 px-4 text-center text-[var(--text-muted)]', null, { 'data-dock-empty': 'true' });
    box.append(mk('i', 'fa-solid fa-comments text-lg text-[var(--accent-primary)]', null, { 'aria-hidden': 'true' }), mk('p', 'text-xs font-medium text-[var(--text-primary)]', 'Pick an EduPredict AI Agent'), mk('p', 'text-[11px] leading-relaxed', 'Select an agent below or type your request. Specialists auto-route and can run portal actions.'));
    stream.appendChild(box);
  }
  function pushStreamNode(stream, node) { if (!stream) return; const e = stream.querySelector('[data-dock-empty]'); if (e && e.parentNode) e.parentNode.removeChild(e); stream.appendChild(node); stream.scrollTop = stream.scrollHeight || 0; }

  function updateAgentVisuals(agent) {
    const el = getEls(), viewAgent = agent || AGENTS.coach;
    if (!el.root) return;
    el.root.querySelectorAll('[data-dock-agent]').forEach((btn) => {
      const bid = resolveAgentId(btn.getAttribute('data-dock-agent')), active = Boolean(agent && bid === agent.id);
      btn.setAttribute('aria-pressed', active ? 'true' : 'false');
      RING_CLS.forEach((cls) => btn.classList.toggle(cls, active));
      const av = btn.querySelector('[data-dock-avatar]');
      if (av && AGENTS[bid]) { av.src = AGENTS[bid].avatar_url; av.alt = AGENTS[bid].name; }
    });
    if (el.chatDp) { el.chatDp.src = viewAgent.avatar_url; el.chatDp.alt = viewAgent.name; }
    if (el.nameEl) el.nameEl.textContent = viewAgent.name;
    if (el.roleEl) el.roleEl.textContent = viewAgent.role;
    if (el.input) el.input.placeholder = agent ? ('Ask ' + agent.name + '...') : 'Select an agent or type a message...';
  }

  function setChatOpen(open) { isChatOpen = Boolean(open); toggleFlexPanel(getEls().chatPanel, isChatOpen); }
  function resetConversation(clearActive) { const el = getEls(); sessionSeq += 1; ephemeralMessages = []; isSending = false; if (el.sendBtn) el.sendBtn.disabled = false; renderEmptyState(el.stream); if (clearActive) { activeAgentId = null; updateAgentVisuals(null); } }
  function setDockOpen(open) {
    const el = getEls();
    isDockOpen = Boolean(open);
    toggleFlexPanel(el.dockBar, isDockOpen);
    if (el.toggleBtn) el.toggleBtn.setAttribute('aria-expanded', isDockOpen ? 'true' : 'false');
    if (!isDockOpen) { setChatOpen(false); resetConversation(true); clearActiveSession(); } else saveActiveSession();
  }

  function populateModalFields(modalNode, fields) {
    if (!modalNode || !fields || typeof fields !== 'object') return;
    const keys = Object.keys(fields), first = ['role', 'course_code', 'full_name'];
    keys.filter((k) => first.includes(k)).concat(keys.filter((k) => !first.includes(k))).forEach((k) => {
      const inp = modalNode.querySelector('[name="' + k + '"]');
      if (!inp) return;
      inp.value = fields[k] == null ? '' : String(fields[k]);
      if (typeof inp.dispatchEvent === 'function') { inp.dispatchEvent(makeEvent('input')); inp.dispatchEvent(makeEvent('change')); }
    });
    const submitBtn = modalNode.querySelector('button[type="submit"], #form-modal-submit-btn');
    if (submitBtn && typeof submitBtn.focus === 'function') submitBtn.focus();
  }

  function runOpenAndFillForm(act) {
    const kind = String(act.form_kind || '').toLowerCase(), fields = act.fields || {};
    if (act.route && normPath(act.route) !== currentPath()) { queuePendingAction(act); navigateToUrl(act.route); return; }
    let modal = null;
    if (kind === 'support_ticket') {
      if (typeof window.openSupportTicketModal === 'function') window.openSupportTicketModal({ reset: true, subject: fields.subject || '', message: fields.message || '' });
      else if (typeof window.openCustomModal === 'function') window.openCustomModal('support-ticket-modal');
      modal = byId('support-ticket-modal');
    } else if (kind === 'profile_update') {
      if (typeof window.openProfileCustomModal === 'function') window.openProfileCustomModal('profile-edit-modal');
      else if (typeof window.openCustomModal === 'function') window.openCustomModal('profile-edit-modal');
      modal = byId('profile-edit-modal');
    } else if (kind === 'quick_marks' && typeof window.openQuickEntryModal === 'function') { window.openQuickEntryModal(); modal = byId('form-modal'); }
    else if (kind === 'create_course' && typeof window.openCreateCourseModal === 'function') { window.openCreateCourseModal(); modal = byId('form-modal'); }
    else if (kind === 'create_user' && typeof window.openCreateUserModal === 'function') { window.openCreateUserModal(); modal = byId('form-modal'); }
    populateModalFields(modal || document, fields);
  }

  function runSingleDomAction(act) {
    if (!act || typeof act !== 'object') return;
    if (act.type === 'redirect' && act.url) { navigateToUrl(act.url); return; }
    if (act.type === 'filter_table') {
      if (act.route && normPath(act.route) !== currentPath()) { queuePendingAction(act); navigateToUrl(act.route); return; }
      const inputs = Array.from(document.querySelectorAll('input[data-table-search]')), target = inputs.find((n) => !n.closest('.hidden')) || inputs[0];
      if (target) { target.value = act.query || ''; if (typeof target.dispatchEvent === 'function') target.dispatchEvent(makeEvent('input')); if (typeof window.showToast === 'function') window.showToast('Filtered by "' + (act.query || '') + '"', 'info'); }
      return;
    }
    if (act.type === 'click_element') {
      const cmd = String(act.action || '').toLowerCase();
      if (cmd === 'print_a4_report') {
        if (typeof window.printOfficialA4Report === 'function') window.printOfficialA4Report();
        else if (act.route && normPath(act.route) !== currentPath()) { queuePendingAction(act); navigateToUrl(act.route); }
        else if (typeof window.print === 'function') window.print();
      } else if (cmd === 'download_pdf') {
        const link = document.querySelector('a[href*="-pdf"], a[href*="report/pdf"], a[href*="roster/pdf"]');
        if (link && typeof link.click === 'function') link.click(); else if (act.url) navigateToUrl(act.url);
      } else if (cmd === 'open_change_password') {
        if (typeof window.openChangePasswordModal === 'function') window.openChangePasswordModal();
        else if (currentPath() !== '/profile') { queuePendingAction(Object.assign({ route: '/profile/' }, act)); navigateToUrl('/profile/'); }
      } else if (cmd === 'open_theme_studio' && typeof window.openThemeStudioModal === 'function') window.openThemeStudioModal();
      return;
    }
    if (act.type === 'open_and_fill_form') runOpenAndFillForm(act);
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
    try {
      if (!window.sessionStorage) return;
      const raw = window.sessionStorage.getItem(PENDING_DOM_KEY);
      if (!raw) return;
      window.sessionStorage.removeItem(PENDING_DOM_KEY);
      executeDomActions(JSON.parse(raw));
    } catch (e) {}
  }

  function renderActionChips(bubble, actions) {
    if (!bubble || !Array.isArray(actions) || !actions.length) return;
    const wrap = mk('div', 'mt-2 flex flex-wrap gap-1.5'), icons = { redirect: 'fa-solid fa-arrow-up-right-from-square', filter_table: 'fa-solid fa-filter', click_element: 'fa-solid fa-bolt', open_and_fill_form: 'fa-solid fa-pen-to-square' };
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
    const el = getEls(), time = timeOverride || formatTime();
    if (!el.stream) return;
    if (!skipStore) { ephemeralMessages.push({ side: 'right', text, time }); saveActiveSession(); }
    const row = mk('div', 'flex justify-end', null, { 'data-dock-msg': 'user', 'data-msg-side': 'right' });
    const bubble = mk('div', 'ml-auto max-w-[82%] rounded-2xl rounded-br-none bg-[var(--accent-primary)] px-3.5 py-2 text-xs text-white shadow-sm');
    const meta = mk('div', 'mt-1 flex items-center justify-end gap-1 text-[10px] text-white/80');
    meta.append(mk('span', '', time), mk('span', '', '✓✓'));
    bubble.append(mk('p', 'whitespace-pre-wrap break-words leading-relaxed', text), meta);
    row.appendChild(bubble);
    pushStreamNode(el.stream, row);
  }

  function appendAgentBubble(agentObj, text, continuePrefix, domActions, timeOverride, skipStore) {
    const el = getEls(), agent = normalizeAgent(agentObj), time = timeOverride || formatTime(), actions = Array.isArray(domActions) ? domActions : [];
    if (!el.stream) return;
    if (!skipStore) { ephemeralMessages.push({ side: 'left', agentId: agent.id, text, continuePrefix: continuePrefix || '', domActions: actions, time }); saveActiveSession(); }
    const row = mk('div', 'flex justify-start', null, { 'data-dock-msg': 'agent', 'data-msg-side': 'left', 'data-agent-id': agent.id });
    const bubble = mk('div', 'mr-auto max-w-[86%] rounded-2xl rounded-bl-none border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3.5 py-2.5 text-xs text-[var(--text-primary)] shadow-sm');
    const head = mk('div', 'mb-1 flex items-center gap-1.5 text-[11px] font-semibold'), badgeLbl = mk('span', '', agent.name + ' · ' + agent.shortRole);
    badgeLbl.style.color = agent.accent;
    head.append(mk('img', 'h-5 w-5 rounded-full object-cover shrink-0', null, { src: agent.avatar_url, alt: agent.name }), badgeLbl);
    bubble.appendChild(head);
    if (continuePrefix) bubble.appendChild(mk('p', 'mb-1 font-semibold leading-snug text-[var(--text-primary)]', continuePrefix));
    bubble.appendChild(mk('p', 'whitespace-pre-wrap break-words leading-relaxed text-[var(--text-primary)]', text));
    renderActionChips(bubble, actions);
    bubble.appendChild(mk('div', 'mt-1 text-right text-[10px] text-[var(--text-muted)]', time));
    row.appendChild(bubble);
    pushStreamNode(el.stream, row);
  }

  function appendHandoffBanner(fromAgentObj, toAgentObj, taskPreview, skipStore) {
    const el = getEls(), fromA = normalizeAgent(fromAgentObj), toA = normalizeAgent(toAgentObj);
    if (!el.stream) return;
    if (!skipStore) { ephemeralMessages.push({ side: 'center', type: 'handoff', fromId: fromA.id, toId: toA.id, from: fromA.name, to: toA.name, taskPreview: taskPreview || '' }); saveActiveSession(); }
    const banner = mk('div', 'mx-auto w-full max-w-[94%] rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-2 text-center text-[11px] text-[var(--text-secondary)] space-y-0.5', null, { 'data-handoff-preview': 'true' });
    const line1 = mk('div', 'flex items-center justify-center gap-1.5 font-semibold text-[var(--text-primary)]');
    line1.append(mk('i', 'fa-solid fa-arrows-rotate text-[10px] text-[var(--accent-primary)]', null, { 'aria-hidden': 'true' }), mk('span', '', 'Task Reassigned: ' + fromA.name + ' -> ' + toA.name));
    banner.appendChild(line1);
    if (taskPreview) banner.appendChild(mk('p', 'line-clamp-2 break-words text-[10px] text-[var(--text-muted)]', 'Task Preview: ' + taskPreview));
    pushStreamNode(el.stream, banner);
  }

  function appendPollBubble(agentObj, poll, skipStore) {
    const el = getEls(), agent = normalizeAgent(agentObj);
    if (!el.stream || !poll || !Array.isArray(poll.options) || !poll.options.length) return;
    if (!skipStore) { ephemeralMessages.push({ side: 'left', type: 'poll', agentId: agent.id, poll }); saveActiveSession(); }
    const row = mk('div', 'flex justify-start', null, { 'data-agent-poll': 'true', 'data-agent-id': agent.id });
    const card = mk('div', 'mr-auto max-w-[90%] rounded-2xl rounded-bl-none border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3.5 py-2.5 text-xs text-[var(--text-primary)] shadow-sm space-y-2');
    card.appendChild(mk('p', 'font-semibold leading-snug text-[var(--text-primary)]', poll.question || 'Choose an option:'));
    const optsWrap = mk('div', 'flex flex-wrap gap-1.5');
    poll.options.forEach((opt) => {
      if (!opt) return;
      const prompt = opt.prompt || opt.label || '';
      const btn = mk('button', 'inline-flex items-center gap-1 rounded-full border border-[var(--border-subtle)] bg-[var(--bg-canvas)] px-2.5 py-1 text-[11px] font-medium text-[var(--text-primary)] transition-colors hover:border-[var(--accent-primary)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent-primary)]', opt.label || prompt, { type: 'button', 'data-poll-option': 'true' });
      btn.addEventListener('click', () => { const cur = getEls(); if (cur.input) cur.input.value = prompt; handleSendSubmit({ preventDefault: function () {} }); });
      optsWrap.appendChild(btn);
    });
    card.appendChild(optsWrap);
    row.appendChild(card);
    pushStreamNode(el.stream, row);
  }

  function removeTypingBubble() { const s = getEls().stream, n = s ? s.querySelector('[data-dock-typing]') : null; if (n && n.parentNode) n.parentNode.removeChild(n); }
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
    selectAgent(targetId, true);
    if (el.input) el.input.value = '';
    appendUserBubble(rawText);
    if (typeof fetch !== 'function') return;
    isSending = true; if (el.sendBtn) el.sendBtn.disabled = true;
    showTypingBubble(AGENTS[targetId] || AGENTS.coach);
    fetch(CHAT_ENDPOINT, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken(), 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify({ agent_id: targetId, message: rawText, history: historyPayload })
    }).then((res) => res.json().catch(() => ({ ok: false, error: 'Unable to parse AI response.' }))).then((data) => {
      if (reqSeq !== sessionSeq || !isChatOpen) return;
      removeTypingBubble();
      if (!data || !data.ok) { appendAgentBubble(AGENTS[targetId], (data && data.error) || 'Could not process your request.'); return; }
      const actions = Array.isArray(data.dom_actions) ? data.dom_actions : [], responder = normalizeAgent(data.active_agent || AGENTS[targetId]);
      if (data.handoff === true) {
        const fromAgent = normalizeAgent(data.from_agent || AGENTS[targetId]);
        appendAgentBubble(fromAgent, data.handoff_message || ('Reassigning your request to ' + responder.name + '...'));
        appendHandoffBanner(fromAgent, responder, data.task_preview || rawText.slice(0, 110));
        selectAgent(responder.id, true);
        appendAgentBubble(responder, data.reply || '', data.continue_prefix || '', actions);
      } else { if (responder.id !== activeAgentId) selectAgent(responder.id, true); appendAgentBubble(responder, data.reply || '', '', actions); }
      if (data.poll) appendPollBubble(responder, data.poll);
      const autoActs = actions.filter((a) => a && a.auto);
      if (autoActs.length) executeDomActions(autoActs);
    }).catch(() => { if (reqSeq === sessionSeq && isChatOpen) { removeTypingBubble(); appendAgentBubble(AGENTS[targetId], 'Connection issue while contacting the specialist. Please try again.'); } })
      .finally(() => { if (reqSeq !== sessionSeq) return; isSending = false; const cur = getEls(); if (cur.sendBtn) cur.sendBtn.disabled = false; if (cur.input && typeof cur.input.focus === 'function') cur.input.focus(); });
  }
  function restoreActiveSession() {
    try {
      if (!window.sessionStorage) return;
      const raw = window.sessionStorage.getItem(SESSION_KEY); if (!raw) return;
      const st = JSON.parse(raw); if (!st || typeof st !== 'object') return;
      const el = getEls(), msgs = Array.isArray(st.messages) ? st.messages : [];
      isDockOpen = Boolean(st.isDockOpen); isChatOpen = Boolean(st.isChatOpen);
      activeAgentId = st.activeAgentId ? resolveAgentId(st.activeAgentId) : null;
      toggleFlexPanel(el.dockBar, isDockOpen); if (el.toggleBtn) el.toggleBtn.setAttribute('aria-expanded', isDockOpen ? 'true' : 'false');
      toggleFlexPanel(el.chatPanel, isChatOpen); updateAgentVisuals(activeAgentId ? AGENTS[activeAgentId] : null);
      ephemeralMessages = msgs;
      if (el.stream && msgs.length) {
        el.stream.textContent = '';
        msgs.forEach((m) => {
          if (m.side === 'right') appendUserBubble(m.text, m.time, true);
          else if (m.type === 'handoff') appendHandoffBanner(AGENTS[resolveAgentId(m.fromId || m.from)], AGENTS[resolveAgentId(m.toId || m.to)], m.taskPreview, true);
          else if (m.type === 'poll') appendPollBubble(AGENTS[resolveAgentId(m.agentId)], m.poll, true);
          else if (m.side === 'left') appendAgentBubble(AGENTS[resolveAgentId(m.agentId)], m.text, m.continuePrefix, m.domActions, m.time, true);
        });
      }
    } catch (e) {}
  }
  function initAiAgentDock() {
    const el = getEls(); if (!el.root) return;
    if (el.root.dataset.dockBound === '1') { schedulePendingRun(); return; }
    el.root.dataset.dockBound = '1';
    if (el.toggleBtn) el.toggleBtn.addEventListener('click', () => setDockOpen(!isDockOpen));
    if (el.closeBtn) el.closeBtn.addEventListener('click', () => { setChatOpen(false); resetConversation(true); clearActiveSession(); });
    if (el.clearBtn) el.clearBtn.addEventListener('click', () => { resetConversation(false); clearActiveSession(); const cur = getEls(); if (cur.input && typeof cur.input.focus === 'function') cur.input.focus(); });
    el.root.querySelectorAll('[data-dock-agent]').forEach((btn) => btn.addEventListener('click', () => selectAgent(btn.getAttribute('data-dock-agent'), false)));
    if (el.input) el.input.addEventListener('keydown', (e) => { if ((e.isComposing || e.keyCode === 229) && e.key === 'Enter') e.preventDefault(); });
    if (el.form) el.form.addEventListener('submit', handleSendSubmit);
    restoreActiveSession(); schedulePendingRun();
  }
  function openAiAgentDock(agentId) { setDockOpen(true); if (agentId) selectAgent(resolveAgentId(agentId), false); else { const el = getEls(); if (el.input && typeof el.input.focus === 'function') el.input.focus(); } }
  const closeAiAgentDock = () => setDockOpen(false);
  if (typeof window.reinitEduPredictUI === 'function' && !window.reinitEduPredictUI._aiDockWrapped) {
    const orig = window.reinitEduPredictUI, wrapped = function () { orig(); initAiAgentDock(); };
    wrapped._aiDockWrapped = true; window.reinitEduPredictUI = wrapped;
  }
  Object.assign(window, { initAiAgentDock, openAiAgentDock, closeAiAgentDock, executeAiDomActions: executeDomActions });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initAiAgentDock); else initAiAgentDock();
})();
