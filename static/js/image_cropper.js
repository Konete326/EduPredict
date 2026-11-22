(function () {
  let cropper = null, cropOpts = null, usingFallback = false, fbImg = null, dragFb = null;
  let fbState = { aspect: NaN, zoom: 1, rotate: 0, panX: 0, panY: 0 };
  let activeObjUrl = null, suppressAvatarChange = false, ticketAttachments = [], lightboxZoomed = false, globalsBound = false;
  const byId = (id) => document.getElementById(id), setText = (id, v) => { const el = byId(id); if (el) el.textContent = v; };
  const setVal = (id, v) => { const el = byId(id); if (el) el.value = v; }, onId = (id, ev, fn) => { const el = byId(id); if (el) el.addEventListener(ev, fn); };
  const parseAspect = (k) => (k === '1:1' ? 1 : (k === '16:9' ? 16 / 9 : (k === '4:3' ? 4 / 3 : NaN)));
  const fmtBytes = (n) => (n >= 1048576 ? (n / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round((n || 0) / 1024)) + ' KB');
  const notify = (msg, sev) => { if (typeof window.showToast === 'function') window.showToast(msg, sev || 'info'); };
  const mk = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const syncModalState = (el, open) => { if (!el) return; el.classList.toggle('hidden', !open); el.classList.toggle('flex', open); el.setAttribute('aria-hidden', open ? 'false' : 'true'); if (typeof window.syncBodyScrollLock === 'function') window.syncBodyScrollLock(); };
  const revokeObjUrl = () => { if (activeObjUrl && typeof URL !== 'undefined' && URL.revokeObjectURL) { URL.revokeObjectURL(activeObjUrl); activeObjUrl = null; } };
  function setAspectButtons(aspectKey, lockAvatar) {
    const bar = byId('cropper-aspect-bar'); if (!bar) return;
    bar.querySelectorAll('[data-crop-aspect]').forEach((btn) => {
      const k = btn.getAttribute('data-crop-aspect'), active = k === aspectKey, locked = Boolean(lockAvatar && k !== '1:1');
      btn.setAttribute('aria-pressed', active ? 'true' : 'false'); btn.disabled = locked;
      btn.className = 'rounded-lg border px-2.5 py-1 text-xs font-semibold transition-colors ' + (active ? 'border-[var(--accent-primary)] bg-[var(--accent-soft)] text-[var(--accent-primary)]' : 'border-[var(--border-subtle)] bg-[var(--bg-canvas)] text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)]') + (locked ? ' opacity-40' : '');
    });
  }
  const computeFallbackBox = (w, h) => { const r = fbState.aspect, mw = w * 0.82, mh = h * 0.82; return (!r || Number.isNaN(r)) ? { bw: mw, bh: mh } : ((mw / mh > r) ? { bw: mh * r, bh: mh } : { bw: mw, bh: mw / r }); };
  function paintTransformed(ctx, outW, outH, stageW, stageH, scaleOut) {
    const iw = fbImg.naturalWidth || stageW, ih = fbImg.naturalHeight || stageH, fit = Math.min(stageW / iw, stageH / ih) * 0.9;
    ctx.save(); ctx.translate(outW / 2 + fbState.panX * scaleOut, outH / 2 + fbState.panY * scaleOut);
    ctx.rotate((fbState.rotate * Math.PI) / 180); ctx.scale(fbState.zoom * fit * scaleOut, fbState.zoom * fit * scaleOut);
    ctx.drawImage(fbImg, -iw / 2, -ih / 2); ctx.restore();
  }
  function exportFallbackCanvas(maxSide) {
    const src = byId('cropper-fallback-canvas'); if (!src || !fbImg) return null;
    const cw = src.width || 440, ch = src.height || 260, { bw, bh } = computeFallbackBox(cw, ch), s = Math.min(maxSide / Math.max(bw, bh), 2);
    const out = document.createElement('canvas'); out.width = Math.max(1, Math.round(bw * s)); out.height = Math.max(1, Math.round(bh * s));
    const ctx = out.getContext('2d'); if (ctx) paintTransformed(ctx, out.width, out.height, cw, ch, s); return ctx ? out : null;
  }
  function drawFallback() {
    const canvas = byId('cropper-fallback-canvas'); if (!canvas || !fbImg) return;
    canvas.width = 440; canvas.height = 260;
    const ctx = canvas.getContext('2d'), w = canvas.width, h = canvas.height; if (!ctx) return;
    ctx.clearRect(0, 0, w, h); paintTransformed(ctx, w, h, w, h, 1);
    const { bw, bh } = computeFallbackBox(w, h), bx = (w - bw) / 2, by = (h - bh) / 2;
    ctx.fillStyle = 'rgba(15, 23, 42, 0.45)';
    ctx.fillRect(0, 0, w, by); ctx.fillRect(0, by + bh, w, h - by - bh); ctx.fillRect(0, by, bx, bh); ctx.fillRect(bx + bw, by, w - bx - bw, bh);
    ctx.strokeStyle = '#3b82f6'; ctx.lineWidth = 2; ctx.strokeRect(bx, by, bw, bh);
    const box = byId('cropper-avatar-live-preview'), snap = exportFallbackCanvas(96);
    if (box && snap) { box.textContent = ''; const p = mk('img', 'h-full w-full object-cover'); p.alt = 'Avatar preview'; p.src = snap.toDataURL('image/jpeg', 0.82); box.appendChild(p); }
  }
  const destroyCropper = () => { if (cropper) { cropper.destroy(); cropper = null; } usingFallback = false; fbImg = null; setText('cropper-avatar-live-preview', ''); revokeObjUrl(); };
  const closeImageCropperModal = () => { destroyCropper(); syncModalState(byId('image-cropper-modal'), false); };
  function openImageCropperModal(options) {
    const opts = options || {}, modal = byId('image-cropper-modal'), img = byId('cropper-target-image'), fbCanvas = byId('cropper-fallback-canvas');
    const stageWrap = byId('cropper-stage-wrap'), zoomEl = byId('cropper-zoom-range'); if (!modal || !img) return;
    destroyCropper(); cropOpts = opts;
    const isAvatar = opts.mode === 'avatar', defAspect = opts.aspect || (isAvatar ? '1:1' : 'free');
    setText('image-cropper-title', opts.title || (isAvatar ? 'Crop Profile Photo' : 'Crop Screenshot'));
    if (stageWrap) stageWrap.classList.toggle('ep-crop-circle', isAvatar);
    if (byId('cropper-avatar-live-wrap')) byId('cropper-avatar-live-wrap').classList.toggle('hidden', !isAvatar);
    setAspectButtons(defAspect, isAvatar); setVal('cropper-zoom-range', '1');
    let src = opts.src || '';
    if (opts.file && typeof URL !== 'undefined' && URL.createObjectURL) { activeObjUrl = URL.createObjectURL(opts.file); src = activeObjUrl; }
    if (!src) return;
    syncModalState(modal, true);
    img.onload = () => {
      if (typeof window.Cropper === 'function') {
        usingFallback = false; img.classList.remove('hidden'); if (fbCanvas) fbCanvas.classList.add('hidden');
        cropper = new window.Cropper(img, {
          aspectRatio: parseAspect(defAspect), viewMode: 1, dragMode: 'move', autoCropArea: 0.9, responsive: true, background: false, preview: '#cropper-avatar-live-preview',
          ready() { const cd = cropper.getCanvasData(); cropper._epBaseRatio = cd.naturalWidth ? (cd.width / cd.naturalWidth) : 1; setVal('cropper-zoom-range', '1'); },
          zoom(ev) { if (zoomEl && cropper._epBaseRatio) zoomEl.value = Math.min(3, Math.max(0.5, ev.detail.ratio / cropper._epBaseRatio)).toFixed(2); }
        });
      } else {
        usingFallback = true; fbImg = img; img.classList.add('hidden'); if (fbCanvas) fbCanvas.classList.remove('hidden');
        fbState = { aspect: parseAspect(defAspect), zoom: 1, rotate: 0, panX: 0, panY: 0 }; drawFallback();
      }
    };
    img.onerror = () => { closeImageCropperModal(); notify('Unable to load selected image.', 'warning'); };
    if (/^https?:/i.test(src)) img.crossOrigin = 'anonymous'; else img.removeAttribute('crossorigin');
    img.src = src;
  }

  function dataUrlToBlob(dataUrl) {
    const parts = dataUrl.split(','), mime = (parts[0].match(/:(.*?);/) || [])[1] || 'image/jpeg', bin = atob(parts[1] || ''), arr = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i += 1) arr[i] = bin.charCodeAt(i);
    return new Blob([arr], { type: mime });
  }
  function applyCurrentCrop() {
    const isAvatar = cropOpts && cropOpts.mode === 'avatar';
    const canvas = (!usingFallback && cropper)
      ? cropper.getCroppedCanvas(isAvatar ? { width: 512, height: 512, imageSmoothingEnabled: true, imageSmoothingQuality: 'high' } : { maxWidth: 1440, maxHeight: 1440, imageSmoothingEnabled: true, imageSmoothingQuality: 'high' })
      : exportFallbackCanvas(isAvatar ? 512 : 1280);
    if (!canvas) return;
    let dataUrl = ''; try { dataUrl = canvas.toDataURL('image/jpeg', 0.86); } catch (err) { notify('Please choose a local image file to crop.', 'warning'); return; }
    const done = (blob) => {
      const b = blob || dataUrlToBlob(dataUrl), base = (cropOpts && cropOpts.fileName) || (isAvatar ? 'avatar.jpg' : 'screenshot.jpg');
      const cleanName = (base.replace(/\.[^.]+$/, '') || 'cropped') + '.jpg';
      const file = typeof File === 'function' ? new File([b], cleanName, { type: b.type || 'image/jpeg' }) : b;
      const cb = cropOpts && cropOpts.onApply; closeImageCropperModal();
      if (typeof cb === 'function') cb({ blob: b, file, dataUrl, fileName: cleanName });
    };
    if (typeof canvas.toBlob === 'function') canvas.toBlob(done, 'image/jpeg', 0.88); else done(null);
  }
  function updateProfileAvatars(dataUrl) {
    const pImg = byId('profile-avatar-preview'), pInit = byId('profile-avatar-initials');
    if (pImg) { pImg.src = dataUrl; pImg.classList.remove('hidden'); }
    if (pInit) pInit.classList.add('hidden');
    [['header.ep-topbar a[href$="/profile/"]', 'h-6 w-6 rounded-full object-cover shrink-0'], ['#mobile-sidebar-drawer a[href$="/profile/"]', 'h-8 w-8 shrink-0 rounded-full border border-[var(--border-subtle)] object-cover']].forEach(([sel, cls]) => {
      const link = document.querySelector(sel); if (!link) return;
      let img = link.querySelector('img');
      if (!img) { const ph = link.querySelector('span, div'); img = mk('img', cls); img.alt = 'Avatar'; if (ph) ph.replaceWith(img); else link.prepend(img); }
      img.src = dataUrl;
    });
  }
  function applyCroppedProfileAvatar(input, res) {
    updateProfileAvatars(res.dataUrl); suppressAvatarChange = true;
    try { const dt = new DataTransfer(); dt.items.add(res.file); input.files = dt.files; input.dispatchEvent(new Event('change', { bubbles: true })); } catch (err) {}
    suppressAvatarChange = false; notify('Photo cropped. Click Upload Photo to save.', 'info');
  }
  const openAvatarCrop = (input, opts) => openImageCropperModal(Object.assign({ mode: 'avatar', aspect: '1:1', title: 'Crop Profile Photo', onApply: (res) => applyCroppedProfileAvatar(input, res) }, opts));

  function renderTicketAttachments() {
    const chipsEl = byId('ticket-attachment-chips'), inputsEl = byId('ticket-attachments-inputs'); if (!chipsEl || !inputsEl) return;
    chipsEl.textContent = ''; inputsEl.textContent = '';
    ticketAttachments.forEach((att, idx) => {
      const chip = mk('div', 'inline-flex items-center gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-canvas)] p-1.5 pr-2 text-xs');
      const tBtn = mk('button', 'h-8 w-8 shrink-0 overflow-hidden rounded-lg border border-[var(--border-subtle)]'); tBtn.type = 'button';
      tBtn.addEventListener('click', () => openImageLightbox(att.dataUrl, att.name));
      const tImg = mk('img', 'h-full w-full object-cover'); tImg.src = att.dataUrl; tImg.alt = att.name; tBtn.appendChild(tImg);
      const info = mk('div', 'min-w-0 max-w-[9rem]'); info.append(mk('p', 'truncate font-medium text-[var(--text-primary)]', att.name), mk('p', 'text-[10px] text-[var(--text-muted)]', fmtBytes(att.size)));
      const rm = mk('button', 'inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-[var(--text-muted)] hover:bg-[var(--bg-elevated)] hover:text-[var(--status-danger)]');
      rm.type = 'button'; rm.setAttribute('aria-label', 'Remove screenshot'); rm.innerHTML = '<i class="fa-solid fa-xmark text-xs"></i>';
      rm.addEventListener('click', () => { ticketAttachments.splice(idx, 1); renderTicketAttachments(); });
      chip.append(tBtn, info, rm); chipsEl.appendChild(chip);
      const hidden = mk('input'); hidden.type = 'hidden'; hidden.name = 'attachment_urls'; hidden.value = att.dataUrl; inputsEl.appendChild(hidden);
    });
  }
  function handleTicketImageFile(file) {
    if (!file) return;
    if (ticketAttachments.length >= 3) { notify('Maximum 3 screenshots allowed per ticket.', 'warning'); return; }
    if (!file.type || !file.type.startsWith('image/')) { notify('Please select a valid image file.', 'warning'); return; }
    if (file.size > 5 * 1048576) { notify('Screenshot must be 5 MB or smaller.', 'warning'); return; }
    openImageCropperModal({ mode: 'screenshot', aspect: 'free', title: 'Crop Screenshot', file, fileName: file.name || 'screenshot.png', onApply: (res) => { if (ticketAttachments.length < 3) { ticketAttachments.push({ name: res.fileName, size: res.blob.size, dataUrl: res.dataUrl }); renderTicketAttachments(); } } });
  }
  function openSupportTicketModal(opts) {
    const modal = byId('support-ticket-modal'), o = opts || {}; if (!modal) return;
    if (o.reset !== false) { setVal('ticket-subject-input', o.subject || ''); setVal('ticket-message-input', o.message || ''); ticketAttachments = []; renderTicketAttachments(); }
    syncModalState(modal, true); if (byId('ticket-subject-input')) setTimeout(() => byId('ticket-subject-input').focus(), 20);
  }
  const closeSupportTicketModal = () => syncModalState(byId('support-ticket-modal'), false);
  function setLightboxZoom(zoomed) {
    lightboxZoomed = Boolean(zoomed); const img = byId('lightbox-image'), btn = byId('lightbox-zoom-btn');
    if (img) { img.classList.toggle('scale-150', lightboxZoomed); img.classList.toggle('cursor-zoom-out', lightboxZoomed); img.classList.toggle('cursor-zoom-in', !lightboxZoomed); }
    if (btn) btn.innerHTML = lightboxZoomed ? '<i class="fa-solid fa-magnifying-glass-minus text-xs"></i><span>Reset</span>' : '<i class="fa-solid fa-magnifying-glass-plus text-xs"></i><span>Zoom</span>';
  }
  function openImageLightbox(src, caption) {
    const modal = byId('image-lightbox-modal'), img = byId('lightbox-image'), dl = byId('lightbox-download-btn');
    if (!modal || !img || !src) return;
    img.src = src; setText('lightbox-caption', caption || 'Attachment Preview');
    if (dl) { dl.href = src; dl.download = (caption || 'attachment').replace(/[^a-z0-9._-]+/gi, '_') + '.jpg'; }
    setLightboxZoom(false); syncModalState(modal, true);
  }
  const closeImageLightbox = () => { setLightboxZoom(false); syncModalState(byId('image-lightbox-modal'), false); };

  function bindDrawerQuickActions() {
    [['drawer-edit-reply-btn', 'openReplyTicketModal'], ['drawer-delete-reply-btn', 'openDeleteReplyModal'], ['drawer-toggle-status-btn', 'openToggleTicketModal']].forEach(([id, fnName]) => {
      const el = byId(id);
      if (el && el.dataset.bound !== '1') {
        el.dataset.bound = '1';
        el.addEventListener('click', () => { const btn = window._epActiveTicketBtn; closeTicketDetailDrawer(); if (typeof window[fnName] === 'function') window[fnName](btn); });
      }
    });
  }
  function openTicketDetailDrawer(btn) {
    const drawer = byId('ticket-detail-drawer'), d = btn ? btn.dataset : {}; if (!drawer) return;
    if (!drawer._epParent) drawer._epParent = drawer.parentElement;
    if (document.body && drawer.parentElement !== document.body) document.body.appendChild(drawer);
    window._epActiveTicketBtn = btn || null;
    bindDrawerQuickActions();
    const status = String(d.status || 'OPEN').toUpperCase(), resolved = status === 'RESOLVED', stEl = byId('drawer-ticket-status');
    setText('drawer-ticket-id', d.ticketId || '-');
    if (stEl) { stEl.textContent = status; stEl.className = 'inline-flex items-center rounded-md border border-[var(--border-subtle)] px-2 py-0.5 text-[11px] font-semibold ' + (resolved ? 'bg-[var(--accent-soft)] text-[var(--status-success)]' : 'bg-[var(--bg-elevated)] text-[var(--status-warning)]'); }
    setText('drawer-ticket-user', (d.userName || 'Portal User') + (d.role ? ' (' + d.role + ')' : ''));
    setText('drawer-ticket-date', d.createdAt || '-'); setText('drawer-ticket-subject', d.subject || ''); setText('drawer-ticket-message', d.message || d.feedbackText || '');
    const attBox = byId('drawer-ticket-attachments'), urls = String(d.attachments || '').split('|').map((s) => s.trim()).filter(Boolean);
    if (attBox) {
      attBox.textContent = '';
      if (!urls.length) attBox.appendChild(mk('p', 'col-span-full text-xs text-[var(--text-muted)]', 'No screenshots attached.'));
      else urls.forEach((url, idx) => {
        const b = mk('button', 'group relative overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-canvas)] focus:outline-none'); b.type = 'button';
        b.addEventListener('click', () => openImageLightbox(url, 'Ticket ' + (d.ticketId || '') + ' - Image ' + (idx + 1)));
        const im = mk('img', 'h-20 w-full object-cover transition-transform group-hover:scale-105'); im.src = url; im.alt = 'Attachment ' + (idx + 1);
        b.appendChild(im); attBox.appendChild(b);
      });
    }
    const repBox = byId('drawer-ticket-reply-box'), replyText = String(d.adminReply || '').trim(), delBtn = byId('drawer-delete-reply-btn');
    if (repBox) { repBox.classList.toggle('hidden', !replyText); setText('drawer-ticket-reply-text', replyText); setText('drawer-ticket-reply-meta', [d.repliedBy ? 'By ' + d.repliedBy : '', d.repliedAt || ''].filter(Boolean).join(' · ')); }
    if (delBtn) delBtn.classList.toggle('hidden', !replyText);
    setVal('drawer-reply-ticket-id', d.ticketId || ''); setVal('drawer-reply-text', replyText);
    if (d.filterStatus !== undefined) setVal('drawer-reply-filter-status', d.filterStatus);
    drawer.classList.remove('hidden'); drawer.setAttribute('aria-hidden', 'false');
    if (typeof window.syncBodyScrollLock === 'function') window.syncBodyScrollLock(); else if (document.body) document.body.classList.add('drawer-open', 'ep-overlay-blur');
  }
  function closeTicketDetailDrawer() {
    const drawer = byId('ticket-detail-drawer');
    if (drawer) {
      drawer.classList.add('hidden'); drawer.setAttribute('aria-hidden', 'true');
      if (drawer.parentElement === document.body && drawer._epParent) {
        const connected = drawer._epParent.isConnected !== undefined ? drawer._epParent.isConnected : (!document.body.contains || document.body.contains(drawer._epParent));
        if (connected) drawer._epParent.appendChild(drawer);
        else if (drawer.remove) drawer.remove();
        else if (drawer.parentElement && drawer.parentElement.removeChild) drawer.parentElement.removeChild(drawer);
      }
    }
    if (typeof window.syncBodyScrollLock === 'function') window.syncBodyScrollLock(); else if (document.body) document.body.classList.remove('drawer-open', 'ep-overlay-blur');
  }

  function bindGlobalCropperEventsOnce() {
    if (globalsBound) return; globalsBound = true;
    const setDzDrag = (dz, on) => { dz.classList.toggle('border-[var(--accent-primary)]', on); dz.classList.toggle('bg-[var(--accent-soft)]', on); };
    onId('cropper-aspect-bar', 'click', (e) => {
      const btn = e.target.closest('[data-crop-aspect]'); if (!btn || btn.disabled) return;
      const k = btn.getAttribute('data-crop-aspect'), ratio = parseAspect(k); setAspectButtons(k, cropOpts && cropOpts.mode === 'avatar');
      if (cropper) cropper.setAspectRatio(ratio); else if (usingFallback) { fbState.aspect = ratio; drawFallback(); }
    });
    onId('cropper-zoom-range', 'input', () => { const v = parseFloat(byId('cropper-zoom-range').value) || 1; if (cropper) cropper.zoomTo((cropper._epBaseRatio || 1) * v); else if (usingFallback) { fbState.zoom = v; drawFallback(); } });
    onId('cropper-reset-btn', 'click', () => { setVal('cropper-zoom-range', '1'); if (cropper) cropper.reset(); else if (usingFallback) { fbState.zoom = 1; fbState.rotate = 0; fbState.panX = 0; fbState.panY = 0; drawFallback(); } });
    [['cropper-rotate-left', () => { if (cropper) cropper.rotate(-90); else if (usingFallback) { fbState.rotate -= 90; drawFallback(); } }],
      ['cropper-rotate-right', () => { if (cropper) cropper.rotate(90); else if (usingFallback) { fbState.rotate += 90; drawFallback(); } }],
      ['cropper-apply-btn', applyCurrentCrop], ['lightbox-zoom-btn', () => setLightboxZoom(!lightboxZoomed)],
      ['lightbox-image', () => setLightboxZoom(!lightboxZoomed)], ['lightbox-stage', (e) => { if (e.target === byId('lightbox-stage')) closeImageLightbox(); }]
    ].forEach(([id, fn]) => onId(id, 'click', fn));
    onId('cropper-fallback-canvas', 'pointerdown', (e) => { dragFb = { x: e.clientX, y: e.clientY, px: fbState.panX, py: fbState.panY }; });
    window.addEventListener('pointermove', (e) => { if (dragFb) { fbState.panX = dragFb.px + (e.clientX - dragFb.x); fbState.panY = dragFb.py + (e.clientY - dragFb.y); drawFallback(); } });
    window.addEventListener('pointerup', () => { dragFb = null; });
    const dz = byId('ticket-screenshot-dropzone'), sInput = byId('ticket-screenshot-input');
    if (dz && sInput) {
      dz.addEventListener('click', () => sInput.click());
      dz.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); sInput.click(); } });
      dz.addEventListener('dragover', (e) => { e.preventDefault(); setDzDrag(dz, true); });
      dz.addEventListener('dragleave', () => setDzDrag(dz, false));
      dz.addEventListener('drop', (e) => { e.preventDefault(); setDzDrag(dz, false); handleTicketImageFile(e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]); });
      sInput.addEventListener('change', () => { const f = sInput.files && sInput.files[0]; sInput.value = ''; handleTicketImageFile(f); });
    }
    document.addEventListener('paste', (e) => {
      const tm = byId('support-ticket-modal'), cm = byId('image-cropper-modal');
      if (!tm || tm.classList.contains('hidden') || (cm && !cm.classList.contains('hidden'))) return;
      const items = Array.from((e.clipboardData && e.clipboardData.items) || []), imgItem = items.find((it) => it.type && it.type.startsWith('image/'));
      const file = imgItem ? imgItem.getAsFile() : (e.clipboardData && e.clipboardData.files && e.clipboardData.files[0]);
      if (file && file.type && file.type.startsWith('image/')) { e.preventDefault(); handleTicketImageFile(file); }
    });
    document.addEventListener('keydown', (e) => {
      if (e.isComposing || e.keyCode === 229 || e.key !== 'Escape') return;
      const lb = byId('image-lightbox-modal'), cm = byId('image-cropper-modal'), dr = byId('ticket-detail-drawer');
      if (lb && !lb.classList.contains('hidden')) { e.stopPropagation(); closeImageLightbox(); }
      else if (cm && !cm.classList.contains('hidden')) { e.stopPropagation(); closeImageCropperModal(); }
      else if (dr && !dr.classList.contains('hidden')) { e.stopPropagation(); closeTicketDetailDrawer(); }
    }, true);
  }
  function initImageCropperFeatures() {
    bindGlobalCropperEventsOnce();
    const avatarInput = byId('profile-avatar-file'), cropBtn = byId('profile-crop-photo-btn'), db = document.querySelector('[data-drawer-backdrop="ticket-detail-drawer"]');
    if (avatarInput && avatarInput.dataset.cropBound !== '1') {
      avatarInput.dataset.cropBound = '1';
      avatarInput.addEventListener('change', () => { const f = !suppressAvatarChange && avatarInput.files && avatarInput.files[0]; if (f && f.type && f.type.startsWith('image/') && f.size <= 5 * 1048576) openAvatarCrop(avatarInput, { file: f, fileName: f.name }); });
    }
    if (cropBtn && cropBtn.dataset.cropBtnBound !== '1') {
      cropBtn.dataset.cropBtnBound = '1';
      cropBtn.addEventListener('click', () => {
        if (avatarInput && avatarInput.files && avatarInput.files[0]) { openAvatarCrop(avatarInput, { file: avatarInput.files[0], fileName: avatarInput.files[0].name }); return; }
        const preview = byId('profile-avatar-preview'), src = preview && !preview.classList.contains('hidden') ? preview.getAttribute('src') : '';
        if (src) openAvatarCrop(avatarInput, { src, fileName: 'avatar.jpg' }); else if (avatarInput) avatarInput.click();
      });
    }
    if (db && db.dataset.bound !== '1') { db.dataset.bound = '1'; db.addEventListener('click', closeTicketDetailDrawer); }
  }
  if (typeof window.reinitEduPredictUI === 'function' && !window.reinitEduPredictUI._cropperWrapped) {
    const orig = window.reinitEduPredictUI, wrapped = function () { closeTicketDetailDrawer(); orig(); initImageCropperFeatures(); };
    wrapped._cropperWrapped = true; window.reinitEduPredictUI = wrapped;
  }
  Object.assign(window, { openImageCropperModal, closeImageCropperModal, openSupportTicketModal, closeSupportTicketModal, openImageLightbox, closeImageLightbox, openTicketDetailDrawer, closeTicketDetailDrawer, initImageCropperFeatures });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initImageCropperFeatures); else initImageCropperFeatures();
})();
