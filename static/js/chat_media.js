(function () {
  const MAX_IMAGES = 5;
  const MAX_FILES = 5;
  const MAX_FILE_BYTES = 10 * 1024 * 1024;
  const IMG_EXTS = new Set(['.jpg', '.jpeg', '.png', '.webp', '.gif']);
  const DOC_EXTS = new Set(['.pdf', '.csv', '.txt', '.doc', '.docx']);

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function fmtBytes(n) {
    return n >= 1048576 ? (n / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round((n || 0) / 1024)) + ' KB';
  }

  function docIconClass(name) {
    const ext = (name || '').split('.').pop().toLowerCase();
    if (ext === 'pdf') return 'fa-solid fa-file-pdf text-rose-500';
    if (ext === 'csv') return 'fa-solid fa-file-csv text-emerald-500';
    if (ext === 'doc' || ext === 'docx') return 'fa-solid fa-file-word text-blue-500';
    return 'fa-solid fa-file-lines text-[var(--accent-primary)]';
  }

  function validateFiles(fileList, kind, existingCount, toastFn) {
    const incoming = Array.from(fileList || []);
    const limit = kind === 'image' ? MAX_IMAGES : MAX_FILES;
    const allowed = kind === 'image' ? IMG_EXTS : DOC_EXTS;
    const label = kind === 'image' ? 'images' : 'documents';
    if (existingCount + incoming.length > limit) {
      if (toastFn) toastFn('Maximum ' + limit + ' ' + label + ' allowed per message.', 'danger');
      return [];
    }
    const valid = [];
    for (let i = 0; i < incoming.length; i++) {
      const f = incoming[i];
      const ext = '.' + (f.name.split('.').pop() || '').toLowerCase();
      if (!allowed.has(ext)) {
        if (toastFn) toastFn('Unsupported file type: ' + f.name, 'danger');
        return [];
      }
      if (f.size > MAX_FILE_BYTES) {
        if (toastFn) toastFn(f.name + ' exceeds the 10 MB limit.', 'danger');
        return [];
      }
      valid.push(f);
    }
    return valid;
  }

  function extractImages(m) {
    const list = [];
    const raw = Array.isArray(m.images) ? m.images : (Array.isArray(m.image_urls) ? m.image_urls : []);
    raw.forEach(function (item, idx) {
      if (typeof item === 'string' && item) list.push({ url: item, name: 'Image ' + (idx + 1) + '.jpg' });
      else if (item && item.url) list.push({ url: item.url, name: item.name || ('Image ' + (idx + 1) + '.jpg') });
    });
    if (!list.length && m.image_url) list.push({ url: m.image_url, name: m.image_name || 'Photo.jpg' });
    return list;
  }

  function extractFiles(m) {
    const list = [];
    const raw = Array.isArray(m.files) ? m.files : (Array.isArray(m.attachments) ? m.attachments : []);
    raw.forEach(function (item) {
      if (item && item.url) list.push({ url: item.url, name: item.name || 'Document', size: Number(item.size || 0) });
    });
    if (!list.length && m.file_url) list.push({ url: m.file_url, name: m.file_name || 'Document', size: Number(m.file_size || 0) });
    return list;
  }

  function renderImagesHtml(m) {
    const imgs = extractImages(m);
    if (!imgs.length) return '';
    if (imgs.length === 1) {
      const im = imgs[0];
      return '<div class="relative mb-1 overflow-hidden rounded-[10px] border border-[var(--border-subtle)] bg-[var(--bg-surface)]">' +
        '<button type="button" data-preview-btn="1" data-preview-url="' + esc(im.url) + '" data-preview-name="' + esc(im.name) + '" data-preview-image="1" class="block w-full text-left focus:outline-none">' +
        '<img src="' + esc(im.url) + '" alt="' + esc(im.name) + '" class="max-h-56 w-full object-cover">' +
        '</button>' +
        '<a href="' + esc(im.url) + '" download="' + esc(im.name) + '" title="Download image" class="absolute bottom-2 right-2 inline-flex h-7 w-7 items-center justify-center rounded-full bg-black/60 text-white hover:bg-black/80"><i class="fa-solid fa-download text-[11px]"></i></a>' +
        '</div>';
    }
    const payload = esc(JSON.stringify(imgs));
    const first = imgs[0];
    return '<div data-img-slider="0" data-slider-items="' + payload + '" class="relative mb-1 overflow-hidden rounded-[10px] border border-[var(--border-subtle)] bg-[var(--bg-surface)]">' +
      '<button type="button" data-preview-btn="1" data-slider-preview="1" data-preview-url="' + esc(first.url) + '" data-preview-name="' + esc(first.name) + '" data-preview-image="1" class="block w-full focus:outline-none">' +
      '<img data-slider-img="1" src="' + esc(first.url) + '" alt="' + esc(first.name) + '" class="max-h-56 w-full object-cover">' +
      '</button>' +
      '<button type="button" data-slider-prev="1" aria-label="Previous image" class="absolute left-1.5 top-1/2 -translate-y-1/2 inline-flex h-7 w-7 items-center justify-center rounded-full bg-black/60 text-white hover:bg-black/80"><i class="fa-solid fa-chevron-left text-[11px]"></i></button>' +
      '<button type="button" data-slider-next="1" aria-label="Next image" class="absolute right-1.5 top-1/2 -translate-y-1/2 inline-flex h-7 w-7 items-center justify-center rounded-full bg-black/60 text-white hover:bg-black/80"><i class="fa-solid fa-chevron-right text-[11px]"></i></button>' +
      '<div class="flex items-center justify-between gap-2 bg-[var(--bg-canvas)]/90 px-2.5 py-1 text-[10px] text-[var(--text-secondary)]">' +
      '<span data-slider-counter="1" class="font-mono font-semibold">1 / ' + imgs.length + '</span>' +
      '<button type="button" data-dl-all="' + payload + '" class="inline-flex items-center gap-1 font-semibold text-[var(--accent-primary)] hover:underline"><i class="fa-solid fa-download text-[10px]"></i>Download All</button>' +
      '</div></div>';
  }

  function renderFilesHtml(m) {
    const files = extractFiles(m);
    if (!files.length) return '';
    let html = '<div class="mb-1 space-y-1.5">';
    files.forEach(function (f) {
      html += '<div class="flex items-center gap-2 rounded-[10px] border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2.5 py-1.5 text-xs">' +
        '<button type="button" data-preview-btn="1" data-preview-url="' + esc(f.url) + '" data-preview-name="' + esc(f.name) + '" data-preview-image="0" class="flex min-w-0 flex-1 items-center gap-2 text-left hover:opacity-85">' +
        '<i class="' + docIconClass(f.name) + ' text-sm shrink-0"></i>' +
        '<div class="min-w-0 flex-1"><p class="truncate font-semibold text-[var(--text-primary)]">' + esc(f.name) + '</p>' +
        '<p class="text-[10px] text-[var(--text-muted)]">' + (f.size ? fmtBytes(f.size) : 'Preview') + '</p></div></button>' +
        '<a href="' + esc(f.url) + '" download="' + esc(f.name) + '" title="Download file" class="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-[var(--accent-primary)] hover:bg-[var(--bg-elevated)]"><i class="fa-solid fa-download text-xs"></i></a>' +
        '</div>';
    });
    if (files.length > 1) {
      html += '<button type="button" data-dl-all="' + esc(JSON.stringify(files)) + '" class="inline-flex items-center gap-1 text-[11px] font-semibold text-[var(--accent-primary)] hover:underline"><i class="fa-solid fa-download text-[10px]"></i>Download All (' + files.length + ')</button>';
    }
    html += '</div>';
    return html;
  }

  function triggerDownload(url, name) {
    const a = document.createElement('a');
    a.href = url;
    if (name) a.download = name;
    a.rel = 'noopener';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  function downloadAll(items) {
    (items || []).forEach(function (it, idx) {
      if (!it || !it.url) return;
      setTimeout(function () { triggerDownload(it.url, it.name || ('file-' + (idx + 1))); }, idx * 220);
    });
  }

  function bindMediaEvents(boxEl) {
    if (!boxEl) return;
    boxEl.addEventListener('click', function (e) {
      const prevBtn = e.target.closest('[data-slider-prev]');
      const nextBtn = e.target.closest('[data-slider-next]');
      if (prevBtn || nextBtn) {
        const wrap = (prevBtn || nextBtn).closest('[data-img-slider]');
        if (!wrap) return;
        const items = JSON.parse(wrap.getAttribute('data-slider-items') || '[]');
        if (!items.length) return;
        let idx = Number(wrap.getAttribute('data-img-slider') || 0);
        idx = prevBtn ? (idx - 1 + items.length) % items.length : (idx + 1) % items.length;
        wrap.setAttribute('data-img-slider', String(idx));
        const cur = items[idx];
        const imgEl = wrap.querySelector('[data-slider-img]');
        const pBtn = wrap.querySelector('[data-slider-preview]');
        const cntEl = wrap.querySelector('[data-slider-counter]');
        if (imgEl) { imgEl.src = cur.url; imgEl.alt = cur.name; }
        if (pBtn) { pBtn.setAttribute('data-preview-url', cur.url); pBtn.setAttribute('data-preview-name', cur.name); }
        if (cntEl) cntEl.textContent = (idx + 1) + ' / ' + items.length;
        return;
      }
      const dlAllBtn = e.target.closest('[data-dl-all]');
      if (dlAllBtn) {
        try { downloadAll(JSON.parse(dlAllBtn.getAttribute('data-dl-all') || '[]')); } catch (_) {}
        return;
      }
      const pvBtn = e.target.closest('[data-preview-btn]');
      if (pvBtn && typeof window.openFilePreviewModal === 'function') {
        window.openFilePreviewModal(pvBtn);
      }
    });
  }

  function renderBubbleHtml(m, opts) {
    const sp = m.sender_profile || {}, align = m.is_mine ? 'justify-end' : 'justify-start';
    const bubble = m.is_mine ? 'bg-[var(--accent-soft)] border-[var(--accent-primary)]/25 rounded-tr-[4px]' : 'bg-[var(--bg-elevated)] border-[var(--border-subtle)] rounded-tl-[4px]';
    const isDeleted = m.msg_type === 'DELETED' || m.deleted_for_all;
    let quoteHtml = '';
    if (m.reply_to && !m.deleted_for_all) {
      const rq = m.reply_to;
      const rqTxt = rq.text || (rq.msg_type === 'FILE' ? '[Document] ' + (rq.file_name || '') : (rq.msg_type === 'IMAGE' ? '[Photo]' : (rq.msg_type === 'AUDIO' ? '[Voice note]' : 'Message')));
      quoteHtml = '<button type="button" data-jump-msg="' + esc(rq.msg_id) + '" class="mb-1 block w-full text-left rounded-r-[8px] border-l-4 border-[var(--accent-primary)] bg-[var(--bg-surface)]/80 px-2 py-0.5 text-[11px] hover:bg-[var(--bg-surface)]"><span class="block font-semibold text-[var(--accent-primary)] truncate">' + esc(rq.sender_name || 'Member') + '</span><span class="block text-[var(--text-secondary)] truncate">' + esc(rqTxt) + '</span></button>';
    }
    const canEdit = m.is_mine && m.msg_type === 'TEXT', canAll = m.is_mine || opts.currentRole === 'ADMIN';
    const menuItems = '<button type="button" data-reply-msg="' + esc(m.msg_id) + '" class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[var(--text-primary)] hover:bg-[var(--bg-elevated)]"><i class="fa-solid fa-reply text-[10px]"></i>Reply</button>' +
      (canEdit ? '<button type="button" data-edit-msg="' + esc(m.msg_id) + '" class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[var(--text-primary)] hover:bg-[var(--bg-elevated)]"><i class="fa-solid fa-pen text-[10px]"></i>Edit</button>' : '') +
      (opts.isStaff ? '<button type="button" data-msg-info="' + esc(m.msg_id) + '" class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[var(--text-primary)] hover:bg-[var(--bg-elevated)]"><i class="fa-solid fa-circle-info text-[10px]"></i>Message Info</button>' : '') +
      '<button type="button" data-del-msg="' + esc(m.msg_id) + '" data-can-all="' + (canAll ? '1' : '0') + '" class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[var(--status-danger)] hover:bg-[var(--bg-elevated)]"><i class="fa-solid fa-trash text-[10px]"></i>Delete</button>';
    const menuBtnCls = m.is_mine ? 'float-right ml-1 -mr-1 opacity-75 sm:opacity-0 sm:group-hover:opacity-100 focus-within:opacity-100' : 'shrink-0';
    const menuHtml = !isDeleted ? ('<div class="relative ' + menuBtnCls + '"><button type="button" data-msg-menu-btn="' + esc(m.msg_id) + '" title="Message options" class="inline-flex h-5 w-5 items-center justify-center rounded-full text-[var(--text-muted)] hover:bg-[var(--bg-surface)] hover:text-[var(--text-primary)]"><i class="fa-solid fa-ellipsis-vertical text-[10px]"></i></button><div data-msg-menu="' + esc(m.msg_id) + '" class="hidden absolute right-0 top-5 z-30 w-36 rounded-[10px] border border-[var(--border-subtle)] bg-[var(--bg-surface)] py-1 shadow-xl text-xs">' + menuItems + '</div></div>') : '';
    const hdrHtml = !m.is_mine ? '<div class="flex items-center justify-between gap-2 mb-0.5"><button type="button" data-profile-msg="' + esc(m.msg_id) + '" class="truncate text-[11px] font-semibold leading-tight text-[var(--accent-primary)] hover:underline">' + esc(sp.full_name || 'Member') + '</button>' + menuHtml + '</div>' : menuHtml;
    const metaInline = '<span class="inline-flex items-center gap-1 text-[10px] leading-none text-[var(--text-muted)] select-none whitespace-nowrap">' + esc(m.created_at_str || '') + (m.edited ? ' · edited' : '') + opts.ticksHtml + '</span>';
    let body = '', usedInlineMeta = false;
    if (isDeleted) {
      body = '<p class="italic text-xs text-[var(--text-muted)]"><i class="fa-solid fa-ban mr-1"></i>' + esc(m.text || 'This message was deleted') + '</p>';
    } else if (m.msg_type === 'ASSIGNMENT' && m.assignment) {
      const a = m.assignment;
      body = '<div class="rounded-[10px] border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-2 space-y-0.5"><div class="flex items-center justify-between gap-2"><span class="text-[10px] font-bold uppercase text-[var(--accent-primary)]"><i class="fa-solid fa-file-pen mr-1"></i>New ' + esc(a.test_type || 'Assignment') + '</span><span class="text-[10px] font-mono text-[var(--text-muted)]">' + esc(a.max_marks || 0) + ' marks</span></div><p class="text-[13px] font-semibold text-[var(--text-primary)]">' + esc(a.title) + '</p>' + (a.due_date ? '<p class="text-[11px] text-[var(--text-secondary)]">Due: ' + esc(a.due_date) + '</p>' : '') + (a.url ? '<a href="' + esc(a.url) + '" class="inline-flex items-center gap-1 text-xs font-semibold text-[var(--accent-primary)] hover:underline">View Test &rarr;</a>' : '') + '</div>';
    } else if (m.msg_type === 'POLL' && m.poll) {
      const p = m.poll;
      body = '<div class="space-y-1"><p class="text-[13px] font-semibold text-[var(--text-primary)]"><i class="fa-solid fa-square-poll-vertical mr-1.5 text-[var(--accent-primary)]"></i>' + esc(p.question) + '</p>' + (p.options || []).map(function (o) {
        return '<button type="button" data-vote-msg="' + esc(m.msg_id) + '" data-vote-idx="' + o.idx + '" class="relative w-full overflow-hidden rounded-[8px] border px-2.5 py-1 text-left text-xs ' + (p.my_vote === o.idx ? 'border-[var(--accent-primary)] font-semibold' : 'border-[var(--border-subtle)] bg-[var(--bg-surface)]') + '"><span class="absolute inset-y-0 left-0 bg-[var(--accent-primary)]/15" style="width:' + (o.pct || 0) + '%"></span><span class="relative flex items-center justify-between gap-2"><span>' + esc(o.text) + '</span><span class="font-mono text-[11px] text-[var(--text-muted)]">' + (o.votes || 0) + ' (' + (o.pct || 0) + '%)</span></span></button>';
      }).join('') + '<p class="text-[10px] text-[var(--text-muted)]">' + (p.total_votes || 0) + ' vote(s)</p></div>';
    } else {
      const imgs = renderImagesHtml(m), fls = renderFilesHtml(m), aud = m.audio_url ? '<audio controls src="' + esc(m.audio_url) + '" class="mb-1 h-8 w-56 max-w-full"></audio>' : '';
      body += imgs + fls + aud;
      if (m.text) {
        if (!imgs && !fls && !aud) {
          body += '<p class="text-[13px] leading-[1.35] text-[var(--text-primary)] whitespace-pre-wrap break-words">' + esc(m.text) + '<span class="float-right ml-2 mt-1.5 inline-flex items-center gap-1">' + metaInline + '</span></p>';
          usedInlineMeta = true;
        } else {
          body += '<p class="text-[13px] leading-[1.35] text-[var(--text-primary)] whitespace-pre-wrap break-words">' + esc(m.text) + '</p>';
        }
      }
    }
    const footerHtml = usedInlineMeta ? '' : '<div class="mt-0.5 flex items-center justify-end gap-1 leading-none">' + metaInline + '</div>';
    return '<div class="flex ' + align + '"><div data-msg-bubble="' + esc(m.msg_id) + '" class="group relative flow-root max-w-[88%] sm:max-w-[70%] rounded-[12px] border px-2.5 py-1.5 transition-transform duration-150 ' + bubble + '">' + hdrHtml + quoteHtml + body + footerHtml + '</div></div>';
  }

  window.EPChatMedia = {
    MAX_IMAGES: MAX_IMAGES,
    MAX_FILES: MAX_FILES,
    MAX_FILE_BYTES: MAX_FILE_BYTES,
    esc: esc,
    fmtBytes: fmtBytes,
    docIconClass: docIconClass,
    validateFiles: validateFiles,
    renderImagesHtml: renderImagesHtml,
    renderFilesHtml: renderFilesHtml,
    renderBubbleHtml: renderBubbleHtml,
    bindMediaEvents: bindMediaEvents,
  };
})();
