(function () {
  const box = document.getElementById('chat-messages-box'), cfgEl = document.getElementById('chat-boot-cfg');
  if (!box || !cfgEl) return;
  if (window.__epChatPollTimer) { clearInterval(window.__epChatPollTimer); window.__epChatPollTimer = null; }

  const API_URL = cfgEl.dataset.apiUrl || '/panels/chat/api/messages/';
  const CURRENT_ROLE = (cfgEl.dataset.role || 'STUDENT').toUpperCase();
  const MAX_FILE_BYTES = 5 * 1024 * 1024;
  const ALLOWED_EXTS = new Set(['.jpg', '.jpeg', '.png', '.webp', '.gif', '.pdf', '.csv', '.txt', '.doc', '.docx']);
  const EMOJIS = ['\uD83D\uDC4D', '\uD83D\uDC4E', '\u2764\uFE0F', '\uD83D\uDE02', '\uD83D\uDE2E', '\uD83D\uDE22', '\uD83D\uDE4F', '\uD83C\uDF89', '\uD83D\uDC4F', '\uD83D\uDD25', '\u2705', '\u274C', '\uD83D\uDCCC', '\uD83D\uDCDD', '\uD83D\uDCDA', '\uD83D\uDCA1', '\uD83E\uDD14', '\uD83D\uDC40', '\uD83D\uDE80', '\uD83D\uDCAF', '\u270B', '\uD83D\uDC4B', '\uD83D\uDE0A', '\uD83D\uDE05'];

  let groups = JSON.parse((document.getElementById('chat-groups-data') || {}).textContent || '[]');
  let activeGroupId = cfgEl.dataset.groupId || '';
  let currentMessages = JSON.parse((document.getElementById('chat-messages-data') || {}).textContent || '[]');
  let pendingFile = null, pendingGroupDp = null, replyToMsg = null, recorder = null, recChunks = [], delMsgId = '';
  let lastRenderSig = '', isPolling = false, swipeStart = null;

  const groupsPane = document.getElementById('chat-groups-pane');
  const groupsBackdrop = document.getElementById('chat-groups-backdrop');
  const textInput = document.getElementById('chat-text-input');
  const fileInput = document.getElementById('chat-file-input');
  const filePrev = document.getElementById('chat-file-preview');
  const replyPrev = document.getElementById('chat-reply-preview');
  const emojiPicker = document.getElementById('chat-emoji-picker');

  const getCsrf = () => ((document.querySelector('#chat-composer [name=csrfmiddlewaretoken]') || {}).value || (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '');
  const toast = (msg, type) => { if (typeof window.showToast === 'function') window.showToast(msg, type || 'info'); };
  const esc = (s) => { const d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; };
  const fmtBytes = (n) => (n >= 1048576 ? (n / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round((n || 0) / 1024)) + ' KB');
  const msgSig = (list) => JSON.stringify((list || []).map((m) => [m.msg_id, m.updated_at_iso || m.created_at_iso, m.text, m.deleted_for_all, m.edited, m.poll && m.poll.total_votes, m.poll && m.poll.my_vote]));

  function roleBadge(r) {
    if (r === 'ADMIN') return '<span class="rounded px-1.5 py-0.5 text-[10px] font-bold bg-[var(--status-danger)] text-white">ADMIN</span>';
    if (r === 'TEACHER') return '<span class="rounded px-1.5 py-0.5 text-[10px] font-bold bg-[var(--accent-primary)] text-white">TEACHER</span>';
    return '<span class="rounded px-1.5 py-0.5 text-[10px] font-semibold border border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-muted)]">STUDENT</span>';
  }

  function docIconClass(name) {
    const ext = (name || '').split('.').pop().toLowerCase();
    if (ext === 'pdf') return 'fa-solid fa-file-pdf text-rose-500';
    if (ext === 'csv') return 'fa-solid fa-file-csv text-emerald-500';
    if (ext === 'doc' || ext === 'docx') return 'fa-solid fa-file-word text-blue-500';
    return 'fa-solid fa-file-lines text-[var(--accent-primary)]';
  }

  window.closeChatModal = function (id) { const m = document.getElementById(id); if (m) { m.classList.add('hidden'); m.classList.remove('flex'); } };
  function openChatModal(id) { const m = document.getElementById(id); if (m) { m.classList.remove('hidden'); m.classList.add('flex'); } }
  document.querySelectorAll('[data-chat-backdrop]').forEach((bd) => {
    let down = false;
    bd.addEventListener('pointerdown', (e) => { down = e.target === bd; });
    bd.addEventListener('click', (e) => { if (down && e.target === bd) window.closeChatModal(bd.dataset.chatBackdrop); down = false; });
  });
  function setGroupsDrawer(open) {
    if (!groupsPane) return;
    const isMobile = window.innerWidth < 768;
    groupsPane.classList.toggle('hidden', !open); groupsPane.classList.toggle('flex', open);
    if (groupsBackdrop) groupsBackdrop.classList.toggle('hidden', !(open && isMobile));
    if (!isMobile) localStorage.setItem('ep_chat_groups_collapsed', open ? '0' : '1');
  }
  function initDrawerState() {
    if (window.innerWidth < 768) setGroupsDrawer(!activeGroupId);
    else setGroupsDrawer(localStorage.getItem('ep_chat_groups_collapsed') !== '1');
  }

  function updateHeaderFromGroup(g) {
    if (!g) return;
    const imgEl = document.getElementById('chat-hdr-avatar-img'), initEl = document.getElementById('chat-hdr-avatar');
    if (g.dp_url && imgEl && initEl) {
      imgEl.src = g.dp_url; imgEl.alt = g.group_id; imgEl.classList.remove('hidden'); initEl.classList.add('hidden'); initEl.classList.remove('flex');
    } else if (imgEl && initEl) {
      imgEl.classList.add('hidden'); initEl.textContent = g.group_id.slice(0, 2); initEl.classList.remove('hidden'); initEl.classList.add('flex');
    }
    const titleEl = document.getElementById('chat-hdr-title'), subEl = document.getElementById('chat-hdr-sub');
    if (titleEl) titleEl.textContent = g.group_id + ' - ' + g.title;
    if (subEl) subEl.textContent = g.semester_label + ' · ' + g.teacher_name + ' · ' + g.member_count + ' members';
  }

  function syncGroupCard(g) {
    if (!g) return;
    const titleEl = document.querySelector('[data-group-title="' + g.group_id + '"]');
    if (titleEl) titleEl.textContent = g.title;
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

  function renderMessages(list, stickBottom) {
    const sig = msgSig(list);
    if (!stickBottom && sig === lastRenderSig) return;
    lastRenderSig = sig;
    const wasNearBottom = stickBottom || (box.scrollHeight - box.scrollTop - box.clientHeight < 90);
    if (!list || !list.length) { box.innerHTML = '<div class="py-16 text-center text-xs text-[var(--text-muted)]">No messages yet. Start the conversation!</div>'; return; }
    box.innerHTML = list.map(function (m) {
      const sp = m.sender_profile || {}, align = m.is_mine ? 'justify-end' : 'justify-start';
      const bubble = m.is_mine ? 'bg-[var(--accent-soft)] border-[var(--accent-primary)]/30' : 'bg-[var(--bg-elevated)] border-[var(--border-subtle)]';
      let quoteHtml = '';
      if (m.reply_to && !m.deleted_for_all) {
        const rq = m.reply_to;
        const rqTxt = rq.text || (rq.msg_type === 'FILE' ? '[Document] ' + (rq.file_name || '') : (rq.msg_type === 'IMAGE' ? '[Photo]' : (rq.msg_type === 'AUDIO' ? '[Voice note]' : 'Message')));
        quoteHtml = '<button type="button" data-jump-msg="' + esc(rq.msg_id) + '" class="block w-full text-left rounded-r-[8px] border-l-4 border-[var(--accent-primary)] bg-[var(--bg-surface)]/80 px-2.5 py-1.5 text-[11px] hover:bg-[var(--bg-surface)]"><span class="block font-semibold text-[var(--accent-primary)] truncate">' + esc(rq.sender_name || 'Member') + '</span><span class="block text-[var(--text-secondary)] truncate">' + esc(rqTxt) + '</span></button>';
      }
      let body = '';
      if (m.msg_type === 'DELETED' || m.deleted_for_all) {
        body = '<p class="italic text-xs text-[var(--text-muted)]"><i class="fa-solid fa-ban mr-1"></i>' + esc(m.text || 'This message was deleted') + '</p>';
      } else if (m.msg_type === 'ASSIGNMENT' && m.assignment) {
        const a = m.assignment;
        body = '<div class="rounded-[12px] border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3 space-y-1.5"><div class="flex items-center justify-between gap-2"><span class="text-[10px] font-bold uppercase text-[var(--accent-primary)]"><i class="fa-solid fa-file-pen mr-1"></i>New ' + esc(a.test_type || 'Assignment') + '</span><span class="text-[10px] font-mono text-[var(--text-muted)]">' + esc(a.max_marks || 0) + ' marks</span></div><p class="text-sm font-semibold text-[var(--text-primary)]">' + esc(a.title) + '</p>' + (a.due_date ? '<p class="text-[11px] text-[var(--text-secondary)]">Due: ' + esc(a.due_date) + '</p>' : '') + (a.url ? '<a href="' + esc(a.url) + '" class="inline-flex items-center gap-1 text-xs font-semibold text-[var(--accent-primary)] hover:underline">View Test &rarr;</a>' : '') + '</div>';
      } else if (m.msg_type === 'POLL' && m.poll) {
        const p = m.poll;
        body = '<div class="space-y-2"><p class="text-sm font-semibold text-[var(--text-primary)]"><i class="fa-solid fa-square-poll-vertical mr-1.5 text-[var(--accent-primary)]"></i>' + esc(p.question) + '</p>' + (p.options || []).map(function (o) {
          return '<button type="button" data-vote-msg="' + esc(m.msg_id) + '" data-vote-idx="' + o.idx + '" class="relative w-full overflow-hidden rounded-[10px] border px-3 py-1.5 text-left text-xs ' + (p.my_vote === o.idx ? 'border-[var(--accent-primary)] font-semibold' : 'border-[var(--border-subtle)] bg-[var(--bg-surface)]') + '"><span class="absolute inset-y-0 left-0 bg-[var(--accent-primary)]/15" style="width:' + (o.pct || 0) + '%"></span><span class="relative flex items-center justify-between gap-2"><span>' + esc(o.text) + '</span><span class="font-mono text-[11px] text-[var(--text-muted)]">' + (o.votes || 0) + ' (' + (o.pct || 0) + '%)</span></span></button>';
        }).join('') + '<p class="text-[10px] text-[var(--text-muted)]">' + (p.total_votes || 0) + ' vote(s)</p></div>';
      } else {
        if (m.image_url) body += '<a href="' + esc(m.image_url) + '" target="_blank" rel="noopener"><img src="' + esc(m.image_url) + '" alt="Attachment" class="mb-1.5 max-h-56 rounded-[10px] object-cover"></a>';
        if (m.file_url) body += '<a href="' + esc(m.file_url) + '" target="_blank" rel="noopener" download="' + esc(m.file_name || 'document') + '" class="mb-1.5 flex items-center gap-2.5 rounded-[10px] border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-xs hover:bg-[var(--bg-canvas)]"><i class="' + docIconClass(m.file_name) + ' text-base shrink-0"></i><div class="min-w-0 flex-1"><p class="truncate font-semibold text-[var(--text-primary)]">' + esc(m.file_name || 'Document') + '</p><p class="text-[10px] text-[var(--text-muted)]">' + (m.file_size ? fmtBytes(m.file_size) : 'Download') + '</p></div><i class="fa-solid fa-download text-[var(--accent-primary)] shrink-0"></i></a>';
        if (m.audio_url) body += '<audio controls src="' + esc(m.audio_url) + '" class="mb-1.5 h-9 w-56 max-w-full"></audio>';
        if (m.text) body += '<p class="text-sm text-[var(--text-primary)] whitespace-pre-wrap break-words">' + esc(m.text) + '</p>';
      }
      const canEdit = m.is_mine && m.msg_type === 'TEXT';
      const canAll = m.is_mine || CURRENT_ROLE === 'ADMIN';
      const menuHtml = (m.msg_type !== 'DELETED' && !m.deleted_for_all) ? ('<div class="relative flex items-center gap-1"><button type="button" data-reply-msg="' + esc(m.msg_id) + '" title="Reply" class="inline-flex h-6 w-6 items-center justify-center rounded-full text-[var(--text-muted)] hover:bg-[var(--bg-surface)] hover:text-[var(--accent-primary)]"><i class="fa-solid fa-reply text-[11px]"></i></button><button type="button" data-msg-menu-btn="' + esc(m.msg_id) + '" title="More options" class="inline-flex h-6 w-6 items-center justify-center rounded-full text-[var(--text-muted)] hover:bg-[var(--bg-surface)] hover:text-[var(--text-primary)]"><i class="fa-solid fa-ellipsis-vertical text-[11px]"></i></button><div data-msg-menu="' + esc(m.msg_id) + '" class="hidden absolute right-0 bottom-7 z-30 w-32 rounded-[10px] border border-[var(--border-subtle)] bg-[var(--bg-surface)] py-1 shadow-xl text-xs"><button type="button" data-reply-msg="' + esc(m.msg_id) + '" class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[var(--text-primary)] hover:bg-[var(--bg-elevated)]"><i class="fa-solid fa-reply text-[10px]"></i>Reply</button>' + (canEdit ? '<button type="button" data-edit-msg="' + esc(m.msg_id) + '" class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[var(--text-primary)] hover:bg-[var(--bg-elevated)]"><i class="fa-solid fa-pen text-[10px]"></i>Edit</button>' : '') + '<button type="button" data-del-msg="' + esc(m.msg_id) + '" data-can-all="' + (canAll ? '1' : '0') + '" class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[var(--status-danger)] hover:bg-[var(--bg-elevated)]"><i class="fa-solid fa-trash text-[10px]"></i>Delete</button></div></div>') : '';
      return '<div class="flex ' + align + '"><div data-msg-bubble="' + esc(m.msg_id) + '" class="group relative max-w-[88%] sm:max-w-[72%] rounded-[14px] border px-3.5 py-2.5 space-y-1.5 transition-transform duration-150 ' + bubble + '"><div class="flex flex-wrap items-center justify-between gap-2"><div class="flex flex-wrap items-center gap-1.5"><button type="button" data-profile-msg="' + esc(m.msg_id) + '" class="text-xs font-semibold text-[var(--accent-primary)] hover:underline">' + esc(sp.full_name || 'Member') + '</button>' + roleBadge(sp.role || 'STUDENT') + '</div>' + menuHtml + '</div>' + quoteHtml + body + '<div class="flex items-center justify-between gap-3 pt-0.5"><span class="text-[10px] text-[var(--text-muted)]">' + esc(m.created_at_str || '') + (m.edited ? ' · edited' : '') + '</span></div></div></div>';
    }).join('');
    if (wasNearBottom) box.scrollTop = box.scrollHeight;
  }

  async function fetchMessages(stickBottom) {
    if (!activeGroupId || isPolling) return;
    isPolling = true;
    const targetGid = activeGroupId;
    try {
      const res = await fetch(API_URL + '?group_id=' + encodeURIComponent(targetGid) + '&_t=' + Date.now(), { credentials: 'same-origin', cache: 'no-store' });
      if (!res.ok) return;
      const data = await res.json();
      if (targetGid !== activeGroupId) return;
      if (data.ok && Array.isArray(data.groups)) { groups = data.groups; const cg = groups.find((x) => x.group_id === activeGroupId); if (cg) { updateHeaderFromGroup(cg); syncGroupCard(cg); } }
      if (data.ok && Array.isArray(data.messages)) { currentMessages = data.messages; renderMessages(currentMessages, stickBottom); }
    } catch (_) {} finally { isPolling = false; }
  }

  async function postApi(body, isForm) {
    const opts = { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': getCsrf() } };
    if (isForm) opts.body = body; else { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
    const res = await fetch(API_URL, opts);
    const data = await res.json().catch(() => ({ ok: false, error: 'Server error (' + res.status + ')' }));
    if (!res.ok || !data.ok) toast(data.error || 'Request failed.', 'danger');
    return data;
  }

  document.querySelectorAll('[data-group-btn]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      activeGroupId = btn.dataset.groupId;
      lastRenderSig = '';
      clearReplyTo();
      document.querySelectorAll('[data-group-btn]').forEach((b) => b.classList.toggle('bg-[var(--accent-soft)]', b.dataset.groupId === activeGroupId));
      const g = groups.find((x) => x.group_id === activeGroupId);
      if (g) updateHeaderFromGroup(g);
      if (window.innerWidth < 768) setGroupsDrawer(false);
      fetchMessages(true);
    });
  });

  const toggleGroupsBtn = document.getElementById('chat-toggle-groups-btn');
  const closeGroupsBtn = document.getElementById('chat-close-groups-btn');
  if (toggleGroupsBtn) toggleGroupsBtn.addEventListener('click', () => setGroupsDrawer(groupsPane.classList.contains('hidden')));
  if (closeGroupsBtn) closeGroupsBtn.addEventListener('click', () => setGroupsDrawer(false));
  if (groupsBackdrop) groupsBackdrop.addEventListener('click', () => setGroupsDrawer(false));

  const gSearch = document.getElementById('chat-group-search');
  if (gSearch) gSearch.addEventListener('input', function () {
    const q = gSearch.value.trim().toLowerCase();
    document.querySelectorAll('[data-group-btn]').forEach((b) => b.classList.toggle('hidden', q && !(b.dataset.search || '').includes(q)));
  });

  box.addEventListener('click', async function (e) {
    const menuBtn = e.target.closest('[data-msg-menu-btn]');
    if (menuBtn) {
      const mid = menuBtn.dataset.msgMenuBtn;
      document.querySelectorAll('[data-msg-menu]').forEach((m) => m.classList.toggle('hidden', m.dataset.msgMenu !== mid || !m.classList.contains('hidden')));
      return;
    }
    document.querySelectorAll('[data-msg-menu]').forEach((m) => m.classList.add('hidden'));
    const replyBtn = e.target.closest('[data-reply-msg]'), jumpBtn = e.target.closest('[data-jump-msg]');
    const profBtn = e.target.closest('[data-profile-msg]'), voteBtn = e.target.closest('[data-vote-msg]');
    const editBtn = e.target.closest('[data-edit-msg]'), delBtn = e.target.closest('[data-del-msg]');
    if (replyBtn) { setReplyTo(replyBtn.dataset.replyMsg); return; }
    if (jumpBtn) {
      const target = box.querySelector('[data-msg-bubble="' + jumpBtn.dataset.jumpMsg + '"]');
      if (target) { target.scrollIntoView({ behavior: 'smooth', block: 'center' }); target.classList.add('ring-2', 'ring-[var(--accent-primary)]'); setTimeout(() => target.classList.remove('ring-2', 'ring-[var(--accent-primary)]'), 1200); }
      return;
    }
    if (profBtn) {
      const msg = currentMessages.find((x) => x.msg_id === profBtn.dataset.profileMsg);
      if (msg && msg.sender_profile) {
        const sp = msg.sender_profile;
        document.getElementById('cp-name').textContent = sp.full_name || 'Member';
        document.getElementById('cp-role').textContent = sp.role || 'STUDENT';
        document.getElementById('cp-sid').textContent = sp.student_id ? 'ID: ' + sp.student_id : '';
        document.getElementById('cp-email').textContent = sp.email || '';
        document.getElementById('cp-sem').textContent = sp.semester_label || '';
        openChatModal('chat-profile-modal');
      }
      return;
    }
    if (voteBtn) { const r = await postApi({ action: 'vote', group_id: activeGroupId, msg_id: voteBtn.dataset.voteMsg, option_idx: Number(voteBtn.dataset.voteIdx) }, false); if (r.ok) fetchMessages(false); return; }
    if (editBtn) {
      const msg = currentMessages.find((x) => x.msg_id === editBtn.dataset.editMsg);
      if (msg) { document.getElementById('edit-msg-id').value = msg.msg_id; document.getElementById('edit-msg-text').value = msg.text || ''; openChatModal('chat-edit-modal'); }
      return;
    }
    if (delBtn) { delMsgId = delBtn.dataset.delMsg; document.getElementById('del-all-btn').classList.toggle('hidden', delBtn.dataset.canAll !== '1'); openChatModal('chat-delete-modal'); }
  });

  box.addEventListener('touchstart', function (e) {
    const b = e.target.closest('[data-msg-bubble]');
    if (!b || !e.touches || !e.touches[0]) return;
    swipeStart = { id: b.dataset.msgBubble, el: b, x: e.touches[0].clientX, y: e.touches[0].clientY };
  }, { passive: true });
  box.addEventListener('touchmove', function (e) {
    if (!swipeStart || !e.touches || !e.touches[0]) return;
    const dx = e.touches[0].clientX - swipeStart.x, dy = e.touches[0].clientY - swipeStart.y;
    if (dx > 8 && Math.abs(dy) < 30) swipeStart.el.style.transform = 'translateX(' + Math.min(54, dx) + 'px)';
  }, { passive: true });
  box.addEventListener('touchend', function (e) {
    if (!swipeStart) return;
    swipeStart.el.style.transform = '';
    const t = e.changedTouches && e.changedTouches[0];
    if (t && (t.clientX - swipeStart.x) > 48 && Math.abs(t.clientY - swipeStart.y) < 35) setReplyTo(swipeStart.id);
    swipeStart = null;
  }, { passive: true });

  document.getElementById('chat-reply-clear').addEventListener('click', clearReplyTo);
  document.getElementById('chat-file-btn').addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', function () {
    const f = fileInput.files && fileInput.files[0] ? fileInput.files[0] : null;
    if (!f) return;
    const ext = '.' + (f.name.split('.').pop() || '').toLowerCase();
    if (!ALLOWED_EXTS.has(ext)) { fileInput.value = ''; toast('Unsupported file type. Allowed: images, PDF, CSV, TXT, DOCX.', 'danger'); return; }
    if (f.size > MAX_FILE_BYTES) { fileInput.value = ''; toast('File is too large. Maximum size is 5 MB.', 'danger'); return; }
    pendingFile = f;
    document.getElementById('chat-file-icon').className = (['.jpg', '.jpeg', '.png', '.webp', '.gif'].includes(ext) ? 'fa-solid fa-image' : docIconClass(f.name)) + ' text-[var(--accent-primary)]';
    document.getElementById('chat-file-name').textContent = f.name + ' (' + fmtBytes(f.size) + ')';
    filePrev.classList.remove('hidden'); filePrev.classList.add('flex');
  });
  document.getElementById('chat-file-clear').addEventListener('click', function () { pendingFile = null; fileInput.value = ''; filePrev.classList.add('hidden'); filePrev.classList.remove('flex'); });

  const emojiGrid = document.getElementById('chat-emoji-grid');
  if (emojiGrid) {
    emojiGrid.innerHTML = EMOJIS.map((em) => '<button type="button" data-emoji-val="' + em + '" class="flex h-8 w-8 items-center justify-center rounded-lg text-base hover:bg-[var(--bg-elevated)]">' + em + '</button>').join('');
    emojiGrid.addEventListener('click', function (e) {
      const b = e.target.closest('[data-emoji-val]');
      if (!b) return;
      const val = b.dataset.emojiVal, s = textInput.selectionStart || textInput.value.length, end = textInput.selectionEnd || s;
      textInput.value = textInput.value.slice(0, s) + val + textInput.value.slice(end);
      textInput.focus(); textInput.setSelectionRange(s + val.length, s + val.length);
      emojiPicker.classList.add('hidden');
    });
  }
  document.getElementById('chat-emoji-btn').addEventListener('click', (e) => { e.stopPropagation(); emojiPicker.classList.toggle('hidden'); });
  document.addEventListener('click', function (e) {
    if (emojiPicker && !emojiPicker.classList.contains('hidden') && !e.target.closest('#chat-emoji-picker') && !e.target.closest('#chat-emoji-btn')) emojiPicker.classList.add('hidden');
    if (!e.target.closest('[data-msg-menu-btn]') && !e.target.closest('[data-msg-menu]')) document.querySelectorAll('[data-msg-menu]').forEach((m) => m.classList.add('hidden'));
  });

  textInput.addEventListener('keydown', function (e) { if (e.isComposing || e.keyCode === 229) e.preventDefault(); });
  document.getElementById('chat-composer').addEventListener('submit', async function (e) {
    e.preventDefault();
    if (!activeGroupId) return;
    const txt = textInput.value.trim(), sendBtn = document.getElementById('chat-send-btn');
    if (!txt && !pendingFile) return;
    const fd = new FormData();
    fd.append('action', 'send'); fd.append('group_id', activeGroupId); fd.append('text', txt);
    if (pendingFile) fd.append('file', pendingFile);
    if (replyToMsg) fd.append('reply_to_id', replyToMsg.msg_id);
    if (sendBtn) sendBtn.disabled = true;
    try {
      const data = await postApi(fd, true);
      if (data.ok) {
        textInput.value = ''; pendingFile = null; fileInput.value = '';
        filePrev.classList.add('hidden'); filePrev.classList.remove('flex');
        clearReplyTo();
        if (Array.isArray(data.messages)) { currentMessages = data.messages; renderMessages(currentMessages, true); }
        else fetchMessages(true);
      }
    } finally { if (sendBtn) sendBtn.disabled = false; }
  });

  document.getElementById('chat-voice-btn').addEventListener('click', async function () {
    if (!activeGroupId || !navigator.mediaDevices) return;
    const recStat = document.getElementById('chat-rec-status');
    if (recorder && recorder.state === 'recording') { recorder.stop(); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recChunks = []; recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (ev) => { if (ev.data.size > 0) recChunks.push(ev.data); };
      recorder.onstop = async function () {
        stream.getTracks().forEach((t) => t.stop()); recStat.classList.add('hidden');
        const fd = new FormData();
        fd.append('action', 'send'); fd.append('group_id', activeGroupId); fd.append('audio', new Blob(recChunks, { type: 'audio/webm' }), 'voice.webm');
        if (replyToMsg) fd.append('reply_to_id', replyToMsg.msg_id);
        const data = await postApi(fd, true);
        if (data.ok) { clearReplyTo(); if (Array.isArray(data.messages)) { currentMessages = data.messages; renderMessages(currentMessages, true); } else fetchMessages(true); }
      };
      recorder.start(); recStat.classList.remove('hidden');
    } catch (_) { toast('Microphone access denied or unavailable.', 'warning'); }
  });

  const gsBtn = document.getElementById('chat-group-settings-btn');
  if (gsBtn) {
    const gsDpInput = document.getElementById('gs-dp-input'), gsDpImg = document.getElementById('gs-dp-preview-img'), gsDpInit = document.getElementById('gs-dp-preview-init');
    gsBtn.addEventListener('click', function () {
      const g = groups.find((x) => x.group_id === activeGroupId);
      if (!g) return;
      pendingGroupDp = null;
      document.getElementById('gs-group-name').value = g.title || g.group_id;
      if (g.dp_url) { gsDpImg.src = g.dp_url; gsDpImg.classList.remove('hidden'); gsDpInit.classList.add('hidden'); }
      else { gsDpImg.classList.add('hidden'); gsDpInit.textContent = g.group_id.slice(0, 2); gsDpInit.classList.remove('hidden'); }
      openChatModal('chat-group-settings-modal');
    });
    document.getElementById('gs-dp-btn').addEventListener('click', () => gsDpInput.click());
    gsDpInput.addEventListener('change', function () {
      const f = gsDpInput.files && gsDpInput.files[0];
      if (!f) return;
      if (f.size > MAX_FILE_BYTES) { gsDpInput.value = ''; toast('Group photo must be 5 MB or smaller.', 'danger'); return; }
      if (typeof window.openImageCropperModal === 'function') {
        window.openImageCropperModal({ mode: 'avatar', aspect: '1:1', title: 'Crop Group Photo', file: f, fileName: f.name, onApply: (res) => { pendingGroupDp = res.file; gsDpImg.src = res.dataUrl; gsDpImg.classList.remove('hidden'); gsDpInit.classList.add('hidden'); } });
      } else { pendingGroupDp = f; }
      gsDpInput.value = '';
    });
    document.getElementById('chat-group-settings-form').addEventListener('submit', async function (e) {
      e.preventDefault();
      if (!activeGroupId) return;
      const fd = new FormData();
      fd.append('action', 'update_group'); fd.append('group_id', activeGroupId);
      fd.append('group_name', document.getElementById('gs-group-name').value.trim());
      if (pendingGroupDp) fd.append('group_dp', pendingGroupDp);
      const data = await postApi(fd, true);
      if (data.ok) {
        if (Array.isArray(data.groups)) groups = data.groups;
        if (data.group) { updateHeaderFromGroup(data.group); syncGroupCard(data.group); }
        window.closeChatModal('chat-group-settings-modal'); toast('Group updated.', 'success');
      }
    });
  }

  document.getElementById('chat-open-poll-btn').addEventListener('click', () => { if (activeGroupId) openChatModal('chat-poll-modal'); });
  document.getElementById('chat-poll-form').addEventListener('submit', async function (e) {
    e.preventDefault();
    const q = document.getElementById('poll-question').value.trim(), opts = Array.from(document.querySelectorAll('[data-poll-opt]')).map((i) => i.value.trim()).filter(Boolean);
    if (!q || opts.length < 2) return;
    const data = await postApi({ action: 'poll', group_id: activeGroupId, poll_question: q, poll_options: opts }, false);
    if (data.ok) { e.target.reset(); window.closeChatModal('chat-poll-modal'); if (Array.isArray(data.messages)) { currentMessages = data.messages; renderMessages(currentMessages, true); } else fetchMessages(true); }
  });
  document.getElementById('chat-edit-form').addEventListener('submit', async function (e) {
    e.preventDefault();
    const data = await postApi({ action: 'edit', group_id: activeGroupId, msg_id: document.getElementById('edit-msg-id').value, text: document.getElementById('edit-msg-text').value.trim() }, false);
    if (data.ok) { window.closeChatModal('chat-edit-modal'); fetchMessages(false); }
  });
  [['del-me-btn', 'me'], ['del-all-btn', 'everyone']].forEach(([id, scope]) => {
    document.getElementById(id).addEventListener('click', async () => { const r = await postApi({ action: 'delete', group_id: activeGroupId, msg_id: delMsgId, scope }, false); if (r.ok) { window.closeChatModal('chat-delete-modal'); fetchMessages(false); } });
  });
  initDrawerState();
  renderMessages(currentMessages, true);
  window.__epChatPollTimer = setInterval(() => {
    if (!document.getElementById('chat-messages-box')) { clearInterval(window.__epChatPollTimer); window.__epChatPollTimer = null; return; }
    if (!document.hidden && activeGroupId) fetchMessages(false);
  }, 2500);
})();
