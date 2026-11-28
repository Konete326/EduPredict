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
    bindMediaEvents: bindMediaEvents,
  };
})();
