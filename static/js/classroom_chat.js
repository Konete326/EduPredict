(function bootChat(attempt) {
  const box = document.getElementById('chat-messages-box'), cfgEl = document.getElementById('chat-boot-cfg'), M = window.EPChatMedia;
  if (!box || !cfgEl) return;
  if (!M) { if ((attempt || 0) < 20) setTimeout(() => bootChat((attempt || 0) + 1), 25); return; }
  if (window.__epChatPollTimer) { clearInterval(window.__epChatPollTimer); window.__epChatPollTimer = null; }
  if (typeof window.__epChatCleanup === 'function') { window.__epChatCleanup(); }

  const IS_STAFF_MODE = cfgEl.dataset.staffMode === '1';
  const API_URL = cfgEl.dataset.apiUrl || (IS_STAFF_MODE ? '/staff-chat/api/' : '/chat/api/messages/');
  const CURRENT_ROLE = (cfgEl.dataset.role || 'STUDENT').toUpperCase();
  const IS_STAFF = CURRENT_ROLE === 'TEACHER' || CURRENT_ROLE === 'ADMIN' || (IS_STAFF_MODE && CURRENT_ROLE === 'ANALYST');
  const EMOJIS = ['\uD83D\uDC4D', '\uD83D\uDC4E', '\u2764\uFE0F', '\uD83D\uDE02', '\uD83D\uDE2E', '\uD83D\uDE22', '\uD83D\uDE4F', '\uD83C\uDF89', '\uD83D\uDC4F', '\uD83D\uDD25', '\u2705', '\u274C', '\uD83D\uDCCC', '\uD83D\uDCDD', '\uD83D\uDCDA', '\uD83D\uDCA1', '\uD83E\uDD14', '\uD83D\uDC40', '\uD83D\uDE80', '\uD83D\uDCAF', '\u270B', '\uD83D\uDC4B', '\uD83D\uDE0A', '\uD83D\uDE05'];

  const parseJsonScript = (id) => { try { let v = JSON.parse((document.getElementById(id) || {}).textContent || '[]'); if (typeof v === 'string') v = JSON.parse(v); return Array.isArray(v) ? v : []; } catch (_) { return []; } };
  let groups = parseJsonScript('chat-groups-data'), activeGroupId = cfgEl.dataset.groupId || '', currentMessages = parseJsonScript('chat-messages-data');
  let pendingImages = [], pendingFiles = [], pendingGroupDp = null, replyToMsg = null, recorder = null, recChunks = [], delMsgId = '';
  let lastRenderSig = '', pollReqSeq = 0, swipeStart = null;

  const groupsPane = document.getElementById('chat-groups-pane'), groupsBackdrop = document.getElementById('chat-groups-backdrop'), textInput = document.getElementById('chat-text-input'), imgInput = document.getElementById('chat-img-input'), docInput = document.getElementById('chat-doc-input'), filePrev = document.getElementById('chat-file-preview'), fileListEl = document.getElementById('chat-file-list'), replyPrev = document.getElementById('chat-reply-preview'), emojiPicker = document.getElementById('chat-emoji-picker'), plusMenu = document.getElementById('chat-plus-menu');

  const getCsrf = () => ((document.querySelector('#chat-composer [name=csrfmiddlewaretoken]') || {}).value || (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '');
  const toast = (msg, type) => { if (typeof window.showToast === 'function') window.showToast(msg, type || 'info'); };
  const esc = M.esc;
  const msgSig = (list) => JSON.stringify((list || []).map((m) => [m.msg_id, m.created_at_iso || '', m.updated_at_iso || '', m.created_at_str || '', m.msg_type || '', m.text || '', m.deleted_for_all ? 1 : 0, m.edited ? 1 : 0, m.tick_state || '', m.all_seen ? 1 : 0, ((m.read_receipts && m.read_receipts.seen_by) || m.seen_by || []).length, (m.images || []).length, (m.files || []).length, m.audio_url || '', m.poll && m.poll.total_votes, m.poll && m.poll.my_vote]));

  window.closeChatModal = function (id) { const m = document.getElementById(id); if (m) { m.classList.add('hidden'); m.classList.remove('flex'); } };
  function openChatModal(id) { const m = document.getElementById(id); if (m) { m.classList.remove('hidden'); m.classList.add('flex'); } }
  document.querySelectorAll('[data-chat-backdrop]').forEach((bd) => { let down = false; bd.addEventListener('pointerdown', (e) => { down = e.target === bd; }); bd.addEventListener('click', (e) => { if (down && e.target === bd) window.closeChatModal(bd.dataset.chatBackdrop); down = false; }); });

  function setGroupsDrawer(open) {
    if (!groupsPane) return;
    const isMobile = window.innerWidth < 768;
    groupsPane.classList.toggle('hidden', !open); groupsPane.classList.toggle('flex', open);
    if (groupsBackdrop) groupsBackdrop.classList.toggle('hidden', !(open && isMobile));
    if (!isMobile) localStorage.setItem('ep_chat_groups_collapsed', open ? '0' : '1');
  }
  function initDrawerState() { setGroupsDrawer(window.innerWidth < 768 ? !activeGroupId : localStorage.getItem('ep_chat_groups_collapsed') !== '1'); }

  function updateHeaderFromGroup(g) {
    if (!g) return;
    const imgEl = document.getElementById('chat-hdr-avatar-img'), initEl = document.getElementById('chat-hdr-avatar');
    if (g.dp_url && imgEl && initEl) { imgEl.src = g.dp_url; imgEl.alt = g.group_id; imgEl.classList.remove('hidden'); initEl.classList.add('hidden'); initEl.classList.remove('flex'); }
    else if (imgEl && initEl) { imgEl.classList.add('hidden'); initEl.textContent = g.group_id.slice(0, 2); initEl.classList.remove('hidden'); initEl.classList.add('flex'); }
    const titleEl = document.getElementById('chat-hdr-title'), subEl = document.getElementById('chat-hdr-sub');
    if (titleEl) titleEl.textContent = g.group_id + ' - ' + g.title;
    if (subEl) subEl.textContent = g.semester_label + ' · ' + g.teacher_name + ' · ' + g.member_count + ' members';
  }

  function syncComposerState() {
    const g = groups.find((x) => x.group_id === activeGroupId);
    const deactivated = Boolean(g && g.chat_active === false);
    const wrap = document.getElementById('chat-composer-wrap'), banner = document.getElementById('chat-deactivated-banner');
    if (wrap) wrap.classList.toggle('hidden', deactivated);
    if (banner) banner.classList.toggle('hidden', !deactivated);
    if (deactivated) { clearReplyTo(); if (plusMenu) plusMenu.classList.add('hidden'); if (emojiPicker) emojiPicker.classList.add('hidden'); }
    const actBtn = document.getElementById('chat-toggle-active-btn');
    if (actBtn) actBtn.innerHTML = deactivated ? '<i class="fa-solid fa-circle-play text-[var(--status-success)]"></i><span>Reactivate</span>' : '<i class="fa-solid fa-ban text-[var(--status-danger)]"></i><span>Deactivate</span>';
    const giBadge = document.getElementById('gi-status-badge');
    if (giBadge && g) {
      giBadge.textContent = deactivated ? 'Paused' : 'Active';
      giBadge.className = 'rounded px-1.5 py-0.5 text-[10px] font-semibold ' + (deactivated ? 'bg-[var(--status-danger)]/15 text-[var(--status-danger)]' : 'bg-[var(--status-success)]/15 text-[var(--status-success)]');
    }
  }

  function syncGroupCard(g) {
    if (!g) return;
    const titleEl = document.querySelector('[data-group-title="' + g.group_id + '"]');
    if (titleEl) titleEl.textContent = g.title;
    const pausedEl = document.querySelector('[data-group-paused="' + g.group_id + '"]');
    if (pausedEl) pausedEl.classList.toggle('hidden', g.chat_active !== false);
    const dpEl = document.querySelector('[data-group-dp="' + g.group_id + '"]');
    if (dpEl && g.dp_url) {
      if (dpEl.tagName === 'IMG') dpEl.src = g.dp_url;
      else {
        const img = document.createElement('img');
        img.setAttribute('data-group-dp', g.group_id);
        img.src = g.dp_url; img.alt = g.group_id;
        img.className = 'h-10 w-10 shrink-0 rounded-full border border-[var(--border-subtle)] object-cover';
        dpEl.replaceWith(img);
      }
    }
  }

  function replySnippet(m) {
    if (!m) return '';
    if (m.text) return m.text.slice(0, 90);
    if (m.msg_type === 'IMAGE') return '[Photo]';
    if (m.msg_type === 'FILE') return '[Document] ' + (m.file_name || '');
    if (m.msg_type === 'AUDIO') return '[Voice note]';
    if (m.msg_type === 'POLL') return '[Poll]';
    return 'Message';
  }

  function setReplyTo(msgId) {
    const m = currentMessages.find((x) => x.msg_id === msgId);
    if (!m || m.deleted_for_all) return;
    replyToMsg = m;
    document.getElementById('chat-reply-sender').textContent = 'Replying to ' + ((m.sender_profile && m.sender_profile.full_name) || 'Member');
    document.getElementById('chat-reply-snippet').textContent = replySnippet(m);
    replyPrev.classList.remove('hidden'); replyPrev.classList.add('flex'); textInput.focus();
  }
  function clearReplyTo() { replyToMsg = null; replyPrev.classList.add('hidden'); replyPrev.classList.remove('flex'); }

  function renderPendingAttachments() {
    if (!filePrev || !fileListEl) return;
    if (!pendingImages.length && !pendingFiles.length) { filePrev.classList.add('hidden'); filePrev.classList.remove('flex'); fileListEl.innerHTML = ''; return; }
    const chips = pendingImages.map((f, i) => '<span class="inline-flex items-center gap-1.5 rounded-full border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2.5 py-1 text-[11px]"><i class="fa-solid fa-image text-emerald-500"></i><span class="max-w-[9rem] truncate">' + esc(f.name) + '</span><button type="button" data-rm-img="' + i + '" class="text-[var(--text-muted)] hover:text-[var(--status-danger)]"><i class="fa-solid fa-xmark"></i></button></span>')
      .concat(pendingFiles.map((f, i) => '<span class="inline-flex items-center gap-1.5 rounded-full border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2.5 py-1 text-[11px]"><i class="' + M.docIconClass(f.name) + '"></i><span class="max-w-[9rem] truncate">' + esc(f.name) + '</span><button type="button" data-rm-doc="' + i + '" class="text-[var(--text-muted)] hover:text-[var(--status-danger)]"><i class="fa-solid fa-xmark"></i></button></span>'));
    fileListEl.innerHTML = chips.join(''); filePrev.classList.remove('hidden'); filePrev.classList.add('flex');
  }

  function renderTicksHtml(m) {
    if (!m.is_mine || m.msg_type === 'DELETED' || m.deleted_for_all) return '';
    const rr = m.read_receipts || {};
    const seen = Array.isArray(rr.seen_by) ? rr.seen_by : (Array.isArray(m.seen_by) ? m.seen_by : []);
    const isBlue = Boolean(m.tick_state === 'double_blue' || m.all_seen || m.tick_status === 'read' || seen.length > 0);
    const icon = isBlue ? '<i class="fa-solid fa-check-double text-[11px] text-[#15BCDF]"></i>' : '<i class="fa-solid fa-check text-[11px] text-[var(--text-muted)]"></i>';
    if (IS_STAFF) return '<button type="button" data-msg-info="' + esc(m.msg_id) + '" title="Message Info" class="inline-flex items-center hover:opacity-80">' + icon + '</button>';
    return '<span class="inline-flex items-center">' + icon + '</span>';
  }

  function renderMessages(list, stickBottom, force) {
    if (!force && box.querySelector('[data-msg-menu]:not(.hidden)')) return;
    const sig = msgSig(list);
    if (!stickBottom && sig === lastRenderSig) return;
    lastRenderSig = sig;
    const wasNearBottom = stickBottom || (box.scrollHeight - box.scrollTop - box.clientHeight < 90);
    if (!list || !list.length) { box.innerHTML = '<div class="py-16 text-center text-xs text-[var(--text-muted)]">No messages yet. Start the conversation!</div>'; return; }
    box.innerHTML = list.map((m) => M.renderBubbleHtml(m, { isStaff: IS_STAFF, currentRole: CURRENT_ROLE, ticksHtml: renderTicksHtml(m) })).join('');
    if (wasNearBottom) box.scrollTop = box.scrollHeight;
  }

  function openMessageInfo(msgId) {
    if (!IS_STAFF) return;
    const m = currentMessages.find((x) => x.msg_id === msgId);
    if (!m) return;
    const rr = m.read_receipts || {};
    const seen = Array.isArray(rr.seen_by) ? rr.seen_by : (Array.isArray(m.seen_by) ? m.seen_by : []);
    const unseen = Array.isArray(rr.unseen_by) ? rr.unseen_by : (Array.isArray(m.not_seen_by) ? m.not_seen_by : []);
    document.getElementById('mi-seen-count').textContent = String(seen.length);
    document.getElementById('mi-unseen-count').textContent = String(unseen.length);
    const fmtPerson = (p) => typeof p === 'string' ? esc(p) : esc((p && (p.full_name || p.name || p.email || p.user_id)) || 'Member');
    document.getElementById('mi-seen-list').innerHTML = seen.length ? seen.map((p) => '<li class="flex items-center justify-between gap-2"><span>' + fmtPerson(p) + '</span>' + (p && p.seen_at_str ? '<span class="text-[10px] text-[var(--text-muted)]">' + esc(p.seen_at_str) + '</span>' : '') + '</li>').join('') : '<li class="text-[var(--text-muted)]">No read receipts recorded yet.</li>';
    document.getElementById('mi-unseen-list').innerHTML = unseen.length ? unseen.map((p) => '<li>' + fmtPerson(p) + '</li>').join('') : '<li class="text-[var(--text-muted)]">' + (seen.length ? 'Everyone in this group has seen this message.' : 'Pending member read status.') + '</li>';
    openChatModal('chat-msg-info-modal');
  }

  async function fetchMessages(stickBottom, force) {
    if (!activeGroupId) return;
    const reqSeq = ++pollReqSeq, targetGid = activeGroupId;
    try {
      const res = await fetch(API_URL + '?group_id=' + encodeURIComponent(targetGid) + '&_t=' + Date.now(), { credentials: 'same-origin', cache: 'no-store' });
      if (!res.ok) return;
      const data = await res.json();
      if (targetGid !== activeGroupId || reqSeq !== pollReqSeq) return;
      if (data.ok && Array.isArray(data.groups)) { groups = data.groups; const cg = groups.find((x) => x.group_id === activeGroupId); if (cg) { updateHeaderFromGroup(cg); syncGroupCard(cg); syncComposerState(); } }
      if (data.ok && Array.isArray(data.messages)) { currentMessages = data.messages; renderMessages(currentMessages, stickBottom, force); }
    } catch (_) {}
  }

  const syncCh = typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel('ep_chat_sync') : null;
  function broadcastSync(gid) {
    const payload = { gid: gid || activeGroupId, ts: Date.now() };
    if (syncCh) { try { syncCh.postMessage(payload); } catch (_) {} }
    try { localStorage.setItem('ep_chat_sync_ping', JSON.stringify(payload)); } catch (_) {}
  }
  function applyPostData(data, stickBottom) {
    if (Array.isArray(data.groups)) groups = data.groups;
    if (Array.isArray(data.messages)) { pollReqSeq += 1; currentMessages = data.messages; renderMessages(currentMessages, stickBottom, true); }
    else fetchMessages(stickBottom, true);
    broadcastSync(activeGroupId);
  }

  async function postApi(body, isForm) {
    const opts = { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': getCsrf() } };
    if (isForm) opts.body = body; else { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
    const res = await fetch(API_URL, opts);
    const data = await res.json().catch(() => ({ ok: false, error: 'Server error (' + res.status + ')' }));
    if (!res.ok || !data.ok) toast(data.error || 'Request failed.', 'danger');
    return data;
  }

  document.querySelectorAll('[data-group-btn]').forEach((btn) => btn.addEventListener('click', () => {
    activeGroupId = btn.dataset.groupId; lastRenderSig = ''; clearReplyTo();
    document.querySelectorAll('[data-group-card]').forEach((c) => c.classList.toggle('bg-[var(--accent-soft)]', c.dataset.groupCard === activeGroupId));
    const g = groups.find((x) => x.group_id === activeGroupId);
    if (g) { updateHeaderFromGroup(g); syncComposerState(); }
    if (window.innerWidth < 768) setGroupsDrawer(false);
    fetchMessages(true, true);
  }));

  const toggleGroupsBtn = document.getElementById('chat-toggle-groups-btn');
  if (toggleGroupsBtn) toggleGroupsBtn.addEventListener('click', () => setGroupsDrawer(groupsPane.classList.contains('hidden')));
  if (groupsBackdrop) groupsBackdrop.addEventListener('click', () => setGroupsDrawer(false));

  const gSearch = document.getElementById('chat-group-search');
  if (gSearch) gSearch.addEventListener('input', () => {
    const q = gSearch.value.trim().toLowerCase();
    document.querySelectorAll('[data-group-card]').forEach((c) => c.classList.toggle('hidden', q && !(c.dataset.search || '').includes(q)));
  });

  M.bindMediaEvents(box);
  box.addEventListener('click', async (e) => {
    const menuBtn = e.target.closest('[data-msg-menu-btn]');
    if (menuBtn) { const mid = menuBtn.dataset.msgMenuBtn, flipUp = menuBtn.getBoundingClientRect().bottom + 140 > box.getBoundingClientRect().bottom; document.querySelectorAll('[data-msg-menu]').forEach((m) => { const show = m.dataset.msgMenu === mid && m.classList.contains('hidden'); m.classList.toggle('hidden', !show); if (show) { m.classList.toggle('bottom-6', flipUp); m.classList.toggle('top-5', !flipUp); } }); return; }
    document.querySelectorAll('[data-msg-menu]').forEach((m) => m.classList.add('hidden'));
    const replyBtn = e.target.closest('[data-reply-msg]'), jumpBtn = e.target.closest('[data-jump-msg]'), profBtn = e.target.closest('[data-profile-msg]');
    const voteBtn = e.target.closest('[data-vote-msg]'), editBtn = e.target.closest('[data-edit-msg]'), delBtn = e.target.closest('[data-del-msg]'), infoBtn = e.target.closest('[data-msg-info]');
    if (replyBtn) return setReplyTo(replyBtn.dataset.replyMsg);
    if (infoBtn) return openMessageInfo(infoBtn.dataset.msgInfo);
    if (jumpBtn) { const t = box.querySelector('[data-msg-bubble="' + jumpBtn.dataset.jumpMsg + '"]'); if (t) { t.scrollIntoView({ behavior: 'smooth', block: 'center' }); t.classList.add('ring-2', 'ring-[var(--accent-primary)]'); setTimeout(() => t.classList.remove('ring-2', 'ring-[var(--accent-primary)]'), 1200); } return; }
    if (profBtn) {
      const msg = currentMessages.find((x) => x.msg_id === profBtn.dataset.profileMsg);
      if (msg && msg.sender_profile) {
        const sp = msg.sender_profile;
        document.getElementById('cp-name').textContent = sp.full_name || 'Member'; document.getElementById('cp-role').textContent = sp.role || 'STUDENT';
        document.getElementById('cp-sid').textContent = sp.student_id ? 'ID: ' + sp.student_id : ''; document.getElementById('cp-email').textContent = sp.email || '';
        document.getElementById('cp-sem').textContent = sp.semester_label || ''; openChatModal('chat-profile-modal');
      }
      return;
    }
    if (voteBtn) { const r = await postApi({ action: 'vote', group_id: activeGroupId, msg_id: voteBtn.dataset.voteMsg, option_idx: Number(voteBtn.dataset.voteIdx) }, false); if (r.ok) applyPostData(r, false); return; }
    if (editBtn) { const m = currentMessages.find((x) => x.msg_id === editBtn.dataset.editMsg); if (m) { document.getElementById('edit-msg-id').value = m.msg_id; document.getElementById('edit-msg-text').value = m.text || ''; openChatModal('chat-edit-modal'); } return; }
    if (delBtn) { delMsgId = delBtn.dataset.delMsg; document.getElementById('del-all-btn').classList.toggle('hidden', delBtn.dataset.canAll !== '1'); openChatModal('chat-delete-modal'); }
  });

  box.addEventListener('touchstart', (e) => { const b = e.target.closest('[data-msg-bubble]'); if (b && e.touches && e.touches[0]) swipeStart = { id: b.dataset.msgBubble, el: b, x: e.touches[0].clientX, y: e.touches[0].clientY }; }, { passive: true });
  box.addEventListener('touchmove', (e) => { if (!swipeStart || !e.touches || !e.touches[0]) return; const dx = e.touches[0].clientX - swipeStart.x, dy = e.touches[0].clientY - swipeStart.y; if (dx > 8 && Math.abs(dy) < 30) swipeStart.el.style.transform = 'translateX(' + Math.min(54, dx) + 'px)'; }, { passive: true });
  box.addEventListener('touchend', (e) => { if (!swipeStart) return; swipeStart.el.style.transform = ''; const t = e.changedTouches && e.changedTouches[0]; if (t && (t.clientX - swipeStart.x) > 48 && Math.abs(t.clientY - swipeStart.y) < 35) setReplyTo(swipeStart.id); swipeStart = null; }, { passive: true });

  document.getElementById('chat-reply-clear').addEventListener('click', clearReplyTo);
  document.getElementById('chat-plus-btn').addEventListener('click', (e) => { e.stopPropagation(); plusMenu.classList.toggle('hidden'); if (emojiPicker) emojiPicker.classList.add('hidden'); });
  document.getElementById('chat-plus-photos').addEventListener('click', () => { plusMenu.classList.add('hidden'); imgInput.click(); });
  document.getElementById('chat-plus-docs').addEventListener('click', () => { plusMenu.classList.add('hidden'); docInput.click(); });
  document.getElementById('chat-plus-poll').addEventListener('click', () => { plusMenu.classList.add('hidden'); if (activeGroupId) openChatModal('chat-poll-modal'); });

  imgInput.addEventListener('change', () => { const v = M.validateFiles(imgInput.files, 'image', pendingImages.length, toast); imgInput.value = ''; if (v.length) { pendingImages = pendingImages.concat(v); renderPendingAttachments(); } });
  docInput.addEventListener('change', () => { const v = M.validateFiles(docInput.files, 'file', pendingFiles.length, toast); docInput.value = ''; if (v.length) { pendingFiles = pendingFiles.concat(v); renderPendingAttachments(); } });
  fileListEl.addEventListener('click', (e) => {
    const ri = e.target.closest('[data-rm-img]'), rd = e.target.closest('[data-rm-doc]');
    if (ri) { pendingImages.splice(Number(ri.dataset.rmImg), 1); renderPendingAttachments(); }
    if (rd) { pendingFiles.splice(Number(rd.dataset.rmDoc), 1); renderPendingAttachments(); }
  });
  document.getElementById('chat-file-clear').addEventListener('click', () => { pendingImages = []; pendingFiles = []; imgInput.value = ''; docInput.value = ''; renderPendingAttachments(); });

  const emojiGrid = document.getElementById('chat-emoji-grid');
  if (emojiGrid) {
    emojiGrid.innerHTML = EMOJIS.map((em) => '<button type="button" data-emoji-val="' + em + '" class="flex h-8 w-8 items-center justify-center rounded-lg text-base hover:bg-[var(--bg-elevated)]">' + em + '</button>').join('');
    emojiGrid.addEventListener('click', (e) => {
      const b = e.target.closest('[data-emoji-val]'); if (!b) return;
      const val = b.dataset.emojiVal, s = textInput.selectionStart || textInput.value.length, end = textInput.selectionEnd || s;
      textInput.value = textInput.value.slice(0, s) + val + textInput.value.slice(end);
      textInput.focus(); textInput.setSelectionRange(s + val.length, s + val.length); emojiPicker.classList.add('hidden');
    });
  }
  document.getElementById('chat-emoji-btn').addEventListener('click', (e) => { e.stopPropagation(); emojiPicker.classList.toggle('hidden'); if (plusMenu) plusMenu.classList.add('hidden'); });
  const hdrMenuBtn = document.getElementById('chat-hdr-menu-btn'), hdrMenu = document.getElementById('chat-hdr-menu');
  if (hdrMenuBtn && hdrMenu) hdrMenuBtn.addEventListener('click', (e) => { e.stopPropagation(); hdrMenu.classList.toggle('hidden'); });
  document.addEventListener('click', (e) => {
    if (emojiPicker && !emojiPicker.classList.contains('hidden') && !e.target.closest('#chat-emoji-picker') && !e.target.closest('#chat-emoji-btn')) emojiPicker.classList.add('hidden');
    if (plusMenu && !plusMenu.classList.contains('hidden') && !e.target.closest('#chat-plus-menu') && !e.target.closest('#chat-plus-btn')) plusMenu.classList.add('hidden');
    if (hdrMenu && !hdrMenu.classList.contains('hidden') && !e.target.closest('#chat-hdr-menu') && !e.target.closest('#chat-hdr-menu-btn')) hdrMenu.classList.add('hidden');
    if (!e.target.closest('[data-msg-menu-btn]') && !e.target.closest('[data-msg-menu]')) document.querySelectorAll('[data-msg-menu]').forEach((m) => m.classList.add('hidden'));
  });

  textInput.addEventListener('keydown', (e) => { if (e.key === 'Enter' && (e.isComposing || e.keyCode === 229)) return; });
  document.getElementById('chat-composer').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!activeGroupId) return;
    const txt = textInput.value.trim(), sendBtn = document.getElementById('chat-send-btn');
    if (!txt && !pendingImages.length && !pendingFiles.length) return;
    const fd = new FormData();
    fd.append('action', 'send'); fd.append('group_id', activeGroupId); fd.append('text', txt);
    if (pendingImages.length) { fd.append('image', pendingImages[0]); pendingImages.forEach((f) => fd.append('images', f)); }
    if (pendingFiles.length) { fd.append('file', pendingFiles[0]); pendingFiles.forEach((f) => fd.append('files', f)); }
    if (replyToMsg) fd.append('reply_to_id', replyToMsg.msg_id);
    if (sendBtn) sendBtn.disabled = true;
    try {
      const data = await postApi(fd, true);
      if (data.ok) { textInput.value = ''; pendingImages = []; pendingFiles = []; renderPendingAttachments(); clearReplyTo(); applyPostData(data, true); }
    } finally { if (sendBtn) sendBtn.disabled = false; }
  });

  document.getElementById('chat-voice-btn').addEventListener('click', async () => {
    if (!activeGroupId || !navigator.mediaDevices) return;
    const recStat = document.getElementById('chat-rec-status');
    if (recorder && recorder.state === 'recording') { recorder.stop(); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recChunks = []; recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (ev) => { if (ev.data.size > 0) recChunks.push(ev.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop()); recStat.classList.add('hidden');
        const fd = new FormData();
        fd.append('action', 'send'); fd.append('group_id', activeGroupId); fd.append('audio', new Blob(recChunks, { type: 'audio/webm' }), 'voice.webm');
        if (replyToMsg) fd.append('reply_to_id', replyToMsg.msg_id);
        const data = await postApi(fd, true);
        if (data.ok) { clearReplyTo(); applyPostData(data, true); }
      };
      recorder.start(); recStat.classList.remove('hidden');
    } catch (_) { toast('Microphone access denied or unavailable.', 'warning'); }
  });

  const giDpImg = document.getElementById('gi-dp-img'), giDpInit = document.getElementById('gi-dp-init');
  const gsForm = document.getElementById('chat-group-settings-form'), toggleActiveBtn = document.getElementById('chat-toggle-active-btn');
  function openGroupInfoFor(gid) {
    if (!gid) return;
    if (gid !== activeGroupId) {
      activeGroupId = gid; lastRenderSig = ''; clearReplyTo();
      document.querySelectorAll('[data-group-card]').forEach((c) => c.classList.toggle('bg-[var(--accent-soft)]', c.dataset.groupCard === activeGroupId));
      const sg = groups.find((x) => x.group_id === activeGroupId);
      if (sg) { updateHeaderFromGroup(sg); syncComposerState(); }
      fetchMessages(true, true);
    }
    const g = groups.find((x) => x.group_id === activeGroupId);
    if (!g) return;
    pendingGroupDp = null;
    if (g.dp_url && giDpImg && giDpInit) { giDpImg.src = g.dp_url; giDpImg.classList.remove('hidden'); giDpInit.classList.add('hidden'); }
    else if (giDpImg && giDpInit) { giDpImg.classList.add('hidden'); giDpInit.textContent = g.group_id.slice(0, 2); giDpInit.classList.remove('hidden'); }
    const giName = document.getElementById('gi-name'), giSub = document.getElementById('gi-sub'), giMem = document.getElementById('gi-members-count');
    if (giName) giName.textContent = g.title || g.group_id;
    if (giSub) giSub.textContent = g.group_id + ' · ' + g.semester_label + ' · ' + g.teacher_name;
    if (giMem) giMem.textContent = (g.member_count || 0) + ' member' + ((g.member_count || 0) === 1 ? '' : 's');
    const nameIn = document.getElementById('gs-group-name');
    if (nameIn) nameIn.value = g.title || g.group_id;
    syncComposerState();
    openChatModal('chat-group-info-modal');
  }
  const hdrInfoBtn = document.getElementById('chat-hdr-info-btn'), menuInfoBtn = document.getElementById('chat-menu-group-info');
  if (hdrInfoBtn) hdrInfoBtn.addEventListener('click', () => openGroupInfoFor(activeGroupId));
  if (menuInfoBtn) menuInfoBtn.addEventListener('click', () => { if (hdrMenu) hdrMenu.classList.add('hidden'); openGroupInfoFor(activeGroupId); });
  document.querySelectorAll('[data-edit-group-btn]').forEach((eb) => eb.addEventListener('click', (e) => { e.preventDefault(); e.stopPropagation(); openGroupInfoFor(eb.dataset.editGroupBtn); }));
  if (gsForm) {
    const gsDpInput = document.getElementById('gs-dp-input'), gsDpBtn = document.getElementById('gs-dp-btn');
    if (gsDpBtn && gsDpInput) gsDpBtn.addEventListener('click', () => gsDpInput.click());
    if (gsDpInput) gsDpInput.addEventListener('change', () => {
      const f = gsDpInput.files && gsDpInput.files[0]; if (!f) return;
      if (f.size > M.MAX_FILE_BYTES) { gsDpInput.value = ''; toast('Group photo must be 10 MB or smaller.', 'danger'); return; }
      if (typeof window.openImageCropperModal === 'function') window.openImageCropperModal({ mode: 'avatar', aspect: '1:1', title: 'Crop Group Photo', file: f, fileName: f.name, onApply: (res) => { pendingGroupDp = res.file; if (giDpImg && giDpInit) { giDpImg.src = res.dataUrl; giDpImg.classList.remove('hidden'); giDpInit.classList.add('hidden'); } } });
      else pendingGroupDp = f;
      gsDpInput.value = '';
    });
    gsForm.addEventListener('submit', async (e) => {
      e.preventDefault(); if (!activeGroupId) return;
      const fd = new FormData(); fd.append('action', 'update_group'); fd.append('group_id', activeGroupId); fd.append('group_name', document.getElementById('gs-group-name').value.trim());
      if (pendingGroupDp) fd.append('group_dp', pendingGroupDp);
      const data = await postApi(fd, true);
      if (data.ok) { if (Array.isArray(data.groups)) groups = data.groups; if (data.group) { updateHeaderFromGroup(data.group); syncGroupCard(data.group); syncComposerState(); } window.closeChatModal('chat-group-info-modal'); toast('Group updated.', 'success'); }
    });
  }
  if (toggleActiveBtn) toggleActiveBtn.addEventListener('click', async () => {
    if (!activeGroupId) return;
    const data = await postApi({ action: 'toggle_group_active', group_id: activeGroupId }, false);
    if (data.ok) { if (Array.isArray(data.groups)) groups = data.groups; if (data.group) { updateHeaderFromGroup(data.group); syncGroupCard(data.group); syncComposerState(); toast(data.group.chat_active === false ? 'Group chat deactivated.' : 'Group chat activated.', 'success'); } }
  });

  document.getElementById('chat-poll-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const q = document.getElementById('poll-question').value.trim(), opts = Array.from(document.querySelectorAll('[data-poll-opt]')).map((i) => i.value.trim()).filter(Boolean);
    if (!q || opts.length < 2) return;
    const data = await postApi({ action: 'poll', group_id: activeGroupId, poll_question: q, poll_options: opts }, false);
    if (data.ok) { e.target.reset(); window.closeChatModal('chat-poll-modal'); applyPostData(data, true); }
  });
  document.getElementById('chat-edit-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = await postApi({ action: 'edit', group_id: activeGroupId, msg_id: document.getElementById('edit-msg-id').value, text: document.getElementById('edit-msg-text').value.trim() }, false);
    if (data.ok) { window.closeChatModal('chat-edit-modal'); applyPostData(data, false); toast('Message updated.', 'success'); }
  });
  [['del-me-btn', 'me'], ['del-all-btn', 'everyone']].forEach(([id, scope]) => document.getElementById(id).addEventListener('click', async () => { const r = await postApi({ action: 'delete', group_id: activeGroupId, msg_id: delMsgId, scope }, false); if (r.ok) { window.closeChatModal('chat-delete-modal'); applyPostData(r, false); toast('Message deleted.', 'success'); } }));

  const onSyncNow = () => { if (activeGroupId && !document.hidden) fetchMessages(false, true); };
  const onVis = () => { if (!document.hidden) onSyncNow(); };
  const onStorage = (e) => { if (e.key === 'ep_chat_sync_ping' && e.newValue) { try { const p = JSON.parse(e.newValue); if (p && p.gid === activeGroupId) fetchMessages(false, true); } catch (_) {} } };
  if (syncCh) syncCh.onmessage = (e) => { if (e.data && e.data.gid === activeGroupId) fetchMessages(false, true); };
  window.addEventListener('focus', onSyncNow); window.addEventListener('online', onSyncNow); window.addEventListener('pageshow', onSyncNow);
  window.addEventListener('storage', onStorage); document.addEventListener('visibilitychange', onVis);
  window.__epChatCleanup = () => {
    window.removeEventListener('focus', onSyncNow); window.removeEventListener('online', onSyncNow); window.removeEventListener('pageshow', onSyncNow);
    window.removeEventListener('storage', onStorage); document.removeEventListener('visibilitychange', onVis);
    if (syncCh) { try { syncCh.close(); } catch (_) {} }
  };

  initDrawerState();
  syncComposerState();
  renderMessages(currentMessages, true, true);
  if (activeGroupId) fetchMessages(true, true);
  window.__epChatPollTimer = setInterval(() => {
    if (!document.getElementById('chat-messages-box')) { clearInterval(window.__epChatPollTimer); window.__epChatPollTimer = null; if (typeof window.__epChatCleanup === 'function') window.__epChatCleanup(); return; }
    if (!document.hidden && activeGroupId) fetchMessages(false, false);
  }, 1200);
})(0);
