(function () {
  let progressFadeTimer = null, progressResetTimer = null, globalsBound = false;
  const progressBar = () => document.getElementById('ep-top-progress');

  const EduPredictProgress = {
    start() {
      const bar = progressBar(); if (!bar) return;
      clearTimeout(progressFadeTimer); clearTimeout(progressResetTimer);
      bar.style.transitionDuration = '0ms'; bar.style.width = '0%'; bar.style.opacity = '1'; void bar.offsetWidth;
      bar.style.transitionDuration = ''; bar.style.width = '72%';
    },
    done() {
      const bar = progressBar(); if (!bar) return;
      clearTimeout(progressFadeTimer); clearTimeout(progressResetTimer);
      bar.style.opacity = '1'; bar.style.width = '100%';
      progressFadeTimer = setTimeout(() => { bar.style.opacity = '0'; progressResetTimer = setTimeout(() => { bar.style.width = '0%'; }, 220); }, 180);
    }
  };

  function unlockButton(btn) {
    if (!btn) return;
    btn.disabled = false; btn.removeAttribute('aria-busy');
    if (btn.dataset.origHtml !== undefined) { btn.innerHTML = btn.dataset.origHtml; delete btn.dataset.origHtml; }
    else if (btn.dataset.origVal !== undefined) { btn.value = btn.dataset.origVal; delete btn.dataset.origVal; }
    delete btn.dataset.epLocked;
  }

  function resetSubmitLocks(targetForm) {
    const forms = targetForm ? [targetForm] : Array.from(document.querySelectorAll('form[data-ep-submitting="1"]'));
    forms.forEach((form) => {
      if (form._epLockTimer) { clearTimeout(form._epLockTimer); form._epLockTimer = null; }
      delete form.dataset.epSubmitting; form.querySelectorAll('[data-ep-locked="1"]').forEach(unlockButton);
    });
    if (!targetForm) document.querySelectorAll('[data-ep-locked="1"]').forEach(unlockButton);
  }

  function isDownloadOrSkippedForm(form, submitter) {
    if (!form || form.hasAttribute('data-no-lock') || form.hasAttribute('data-no-loading') || form.hasAttribute('data-download') || form.getAttribute('target') === '_blank') return true;
    if (submitter && (submitter.hasAttribute('data-no-lock') || submitter.hasAttribute('data-no-loading') || submitter.hasAttribute('download'))) return true;
    const action = ((submitter && submitter.getAttribute('formaction')) || form.getAttribute('action') || '').toLowerCase();
    return action.includes('download') || action.includes('export') || action.includes('/backup/') || Boolean(form.querySelector('input[name="export"], input[name="download"]'));
  }

  function initGlobalSubmitGuards() {
    if (globalsBound) return;
    globalsBound = true;
    document.addEventListener('submit', (e) => { if (e.target && e.target.tagName === 'FORM' && e.target.dataset.epSubmitting === '1') e.preventDefault(); }, true);
    document.addEventListener('submit', (e) => {
      const form = e.target;
      if (!form || form.tagName !== 'FORM' || e.defaultPrevented || (typeof form.checkValidity === 'function' && !form.checkValidity())) return;
      const submitter = e.submitter || form.querySelector('button[type="submit"], button:not([type]), input[type="submit"]');
      if (isDownloadOrSkippedForm(form, submitter)) return;
      form.dataset.epSubmitting = '1';
      if (submitter) {
        submitter.dataset.epLocked = '1'; submitter.setAttribute('aria-busy', 'true');
        if (!submitter.disabled) {
          if (submitter.tagName === 'BUTTON') { submitter.dataset.origHtml = submitter.innerHTML; submitter.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-xs" aria-hidden="true"></i><span>Processing...</span>'; }
          else { submitter.dataset.origVal = submitter.value; submitter.value = 'Processing...'; }
          submitter.disabled = true;
        }
      }
      EduPredictProgress.start();
      if (form._epLockTimer) clearTimeout(form._epLockTimer);
      form._epLockTimer = setTimeout(() => { resetSubmitLocks(form); EduPredictProgress.done(); }, 12000);
    }, false);
    window.addEventListener('pageshow', () => { resetSubmitLocks(); const bar = progressBar(); if (bar) { bar.style.opacity = '0'; bar.style.width = '0%'; } });
  }

  function renderHighlightedText(el, rawText, query) {
    if (!el) return;
    el.textContent = '';
    if (!query) { el.textContent = rawText; return; }
    const lowerText = rawText.toLowerCase(), lowerQuery = query.toLowerCase();
    let cursor = 0, idx = lowerText.indexOf(lowerQuery);
    while (idx !== -1) {
      if (idx > cursor) el.appendChild(document.createTextNode(rawText.slice(cursor, idx)));
      const mark = document.createElement('mark');
      mark.className = 'rounded-sm bg-[var(--accent-soft)] px-0.5 text-[var(--accent-primary)] font-semibold';
      mark.textContent = rawText.slice(idx, idx + lowerQuery.length);
      el.appendChild(mark);
      cursor = idx + lowerQuery.length; idx = lowerText.indexOf(lowerQuery, cursor);
    }
    if (cursor < rawText.length) el.appendChild(document.createTextNode(rawText.slice(cursor)));
  }

  function initFaqProWidgets() {
    document.querySelectorAll('[data-faq-pro]').forEach((root) => {
      if (root.dataset.faqReady === '1') return;
      root.dataset.faqReady = '1';
      const searchInput = root.querySelector('input[data-faq-search]'), clearBtn = root.querySelector('button[data-faq-clear]'), emptyEl = root.querySelector('p[data-faq-empty]');
      const items = Array.from(root.querySelectorAll('[data-faq-item]')).map((item) => {
        const trigger = item.querySelector('button[data-faq-trigger]'), qEl = item.querySelector('[data-faq-question]'), aEl = item.querySelector('[data-faq-answer]');
        return { item, trigger, qEl, aEl, qText: qEl ? qEl.textContent.trim() : '', aText: aEl ? aEl.textContent.trim() : '', defaultOpen: item.classList.contains('is-open') };
      });
      const setOpen = (entry, open) => { entry.item.classList.toggle('is-open', open); if (entry.trigger) entry.trigger.setAttribute('aria-expanded', open ? 'true' : 'false'); };
      const applyFaqFilter = (raw) => {
        const q = String(raw || '').trim(), lowerQ = q.toLowerCase();
        let matched = 0, firstOpened = false;
        if (clearBtn) clearBtn.classList.toggle('hidden', !q);
        items.forEach((entry) => {
          const hit = !lowerQ || entry.qText.toLowerCase().includes(lowerQ) || entry.aText.toLowerCase().includes(lowerQ);
          entry.item.classList.toggle('hidden', !hit); renderHighlightedText(entry.qEl, entry.qText, q); renderHighlightedText(entry.aEl, entry.aText, q);
          if (hit) matched += 1;
          setOpen(entry, q ? (hit && !firstOpened ? (firstOpened = true) : false) : entry.defaultOpen);
        });
        if (emptyEl) emptyEl.classList.toggle('hidden', matched > 0 || items.length === 0);
      };
      items.forEach((entry) => { if (entry.trigger) entry.trigger.addEventListener('click', () => setOpen(entry, !entry.item.classList.contains('is-open'))); });
      if (searchInput) searchInput.addEventListener('input', (e) => { if (!e.isComposing && e.keyCode !== 229) applyFaqFilter(searchInput.value); });
      if (clearBtn) clearBtn.addEventListener('click', () => { if (searchInput) { searchInput.value = ''; searchInput.focus(); } applyFaqFilter(''); });
    });
  }

  const CSV_ALIASES = {
    student_id: 'student_id', roll_no: 'student_id', roll_number: 'student_id', enrollment: 'student_id', enrollment_no: 'student_id', reg_no: 'student_id', registration_no: 'student_id', id: 'student_id', std_id: 'student_id', student: 'student_id', student_id_number: 'student_id',
    full_name: 'full_name', name: 'full_name', student_name: 'full_name',
    course_code: 'course_code', course: 'course_code', course_id: 'course_code', subject: 'course_code', class: 'course_code',
    batch: 'batch', batch_name: 'batch', section: 'batch',
    attendance_pct: 'attendance_pct', attendance: 'attendance_pct', att: 'attendance_pct', att_pct: 'attendance_pct', attendance_rate: 'attendance_pct', attendance_percentage: 'attendance_pct',
    internal_marks: 'internal_marks', marks: 'internal_marks', mark: 'internal_marks', score: 'internal_marks', test_score: 'internal_marks', exam_score: 'internal_marks', quiz_marks: 'internal_marks', exam_marks: 'internal_marks', total_marks: 'internal_marks', obtained_marks: 'internal_marks', internal_mark: 'internal_marks', class_marks: 'internal_marks',
    assignment_score: 'assignment_score', assignment: 'assignment_score', assignments: 'assignment_score',
    lms_hours_weekly: 'lms_hours_weekly', lms_hours: 'lms_hours_weekly', study_hours: 'lms_hours_weekly', hours: 'lms_hours_weekly',
    previous_gpa: 'previous_gpa', prev_gpa: 'previous_gpa', cgpa: 'previous_gpa', gpa: 'previous_gpa',
    dropout_label: 'dropout_label', actual_dropout: 'dropout_label', dropped_out: 'dropout_label', is_dropout: 'dropout_label', dropout: 'dropout_label', dropout_status: 'dropout_label', target_dropout: 'dropout_label',
    actual_gpa: 'actual_gpa', final_gpa: 'actual_gpa', next_gpa: 'actual_gpa', target_gpa: 'actual_gpa', semester_gpa: 'actual_gpa', earned_gpa: 'actual_gpa'
  };

  function mapCsvHeader(raw) {
    const clean = String(raw || '').trim();
    const norm = clean.toLowerCase().replace(/%/g, 'pct').replace(/[\s\-.]+/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '');
    return { raw: clean || '-', canonical: CSV_ALIASES[norm] || norm || clean || '-' };
  }

  function parseCsvPreviewRows(text, maxRows) {
    return String(text || '').replace(/^\uFEFF/, '').split(/\r?\n/).filter((l) => l.trim().length > 0).slice(0, maxRows).map((line) => {
      const cols = [];
      let cur = '', inQ = false;
      for (let i = 0; i < line.length; i += 1) {
        const ch = line[i];
        if (ch === '"') { if (inQ && line[i + 1] === '"') { cur += '"'; i += 1; } else inQ = !inQ; }
        else if (ch === ',' && !inQ) { cols.push(cur.trim()); cur = ''; }
        else cur += ch;
      }
      cols.push(cur.trim());
      return cols;
    });
  }

  function renderCsvMapperPreview(root, text) {
    let box = root.querySelector('[data-csv-mapper-preview]');
    const parsed = parseCsvPreviewRows(text, 4);
    if (!parsed.length || !parsed[0].length) { if (box) { box.textContent = ''; box.classList.add('hidden'); } return; }
    if (!box) {
      box = document.createElement('div');
      box.setAttribute('data-csv-mapper-preview', '');
      box.className = 'rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-2.5 space-y-2 text-xs';
      root.appendChild(box);
    }
    box.textContent = ''; box.classList.remove('hidden');
    const mapped = parsed[0].map(mapCsvHeader), dataRows = parsed.slice(1, 4);
    const head = document.createElement('div'), ttl = document.createElement('span'), meta = document.createElement('span');
    head.className = 'flex items-center justify-between gap-2';
    ttl.className = 'text-[11px] font-semibold text-[var(--text-primary)]'; ttl.textContent = 'Smart CSV Column Auto-Mapper';
    meta.className = 'font-mono text-[10px] text-[var(--text-muted)]'; meta.textContent = mapped.length + ' cols · ' + dataRows.length + ' preview rows';
    head.append(ttl, meta);
    const badges = document.createElement('div');
    badges.className = 'flex flex-wrap gap-1';
    mapped.forEach((m) => {
      const pill = document.createElement('span');
      pill.className = 'inline-flex items-center rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-secondary)]';
      pill.textContent = m.raw + ' -> ' + m.canonical;
      badges.appendChild(pill);
    });
    box.append(head, badges);
    if (!dataRows.length) return;
    const wrap = document.createElement('div'), tbl = document.createElement('table'), thead = document.createElement('thead'), trH = document.createElement('tr'), tbody = document.createElement('tbody');
    wrap.className = 'overflow-x-auto rounded border border-[var(--border-subtle)]';
    tbl.className = 'w-full border-collapse text-left text-[11px] tabular-nums';
    trH.className = 'border-b border-[var(--border-subtle)] bg-[var(--bg-elevated)]';
    mapped.forEach((m) => {
      const th = document.createElement('th');
      th.className = 'px-2 py-1 font-mono text-[10px] font-semibold text-[var(--text-muted)] whitespace-nowrap';
      th.textContent = m.canonical;
      trH.appendChild(th);
    });
    thead.appendChild(trH);
    tbody.className = 'divide-y divide-[var(--border-subtle)]';
    dataRows.forEach((row) => {
      const tr = document.createElement('tr');
      mapped.forEach((_, idx) => {
        const td = document.createElement('td');
        td.className = 'px-2 py-1 text-[var(--text-primary)] max-w-[8rem] truncate';
        td.textContent = row[idx] !== undefined ? row[idx] : '';
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    tbl.append(thead, tbody); wrap.appendChild(tbl); box.appendChild(wrap);
  }

  function initGradientUploaders() {
    document.querySelectorAll('[data-gradient-uploader]').forEach((root) => {
      if (root.dataset.uploaderReady === '1') return;
      root.dataset.uploaderReady = '1';
      const q = (s) => root.querySelector(s), dropzone = q('[data-uploader-dropzone]'), input = q('[data-uploader-input]'), preview = q('[data-uploader-preview]');
      const img = q('[data-uploader-img]'), nameEl = q('[data-uploader-name]'), metaEl = q('[data-uploader-meta]'), clearBtn = q('[data-uploader-clear]'), browseBtn = q('[data-uploader-browse]'), progressEl = q('[data-upload-progress]');
      if (!input) return;
      const defImgSrc = img ? (img.getAttribute('src') || '') : '', defPreview = Boolean(preview && !preview.classList.contains('hidden')), defName = nameEl ? nameEl.textContent : '', defMeta = metaEl ? metaEl.textContent : '', maxMb = parseFloat(root.getAttribute('data-max-mb') || '0') || 0;
      const revokeObjUrl = () => { if (root._epObjUrl && typeof URL !== 'undefined' && URL.revokeObjectURL) { URL.revokeObjectURL(root._epObjUrl); root._epObjUrl = null; } };
      const clearCsvBox = () => { root._epCsvSeq = (root._epCsvSeq || 0) + 1; const cb = q('[data-csv-mapper-preview]'); if (cb) { cb.textContent = ''; cb.classList.add('hidden'); } };
      const resetUploader = () => {
        input.value = ''; revokeObjUrl(); clearCsvBox();
        if (img) { if (defImgSrc) { img.src = defImgSrc; img.classList.remove('hidden'); } else { img.removeAttribute('src'); img.classList.add('hidden'); } }
        if (preview) preview.classList.toggle('hidden', !defPreview); if (nameEl) nameEl.textContent = defName; if (metaEl) metaEl.textContent = defMeta;
        if (progressEl) { progressEl.classList.remove('w-full', 'w-0'); progressEl.style.width = defImgSrc ? '100%' : '0%'; }
        if (clearBtn) clearBtn.classList.add('hidden');
      };
      const applyFile = (file) => {
        if (!file) { resetUploader(); return; }
        if (maxMb > 0 && file.size > maxMb * 1048576) { if (typeof window.showToast === 'function') window.showToast('File size exceeds ' + maxMb + ' MB limit.', 'warning'); resetUploader(); return; }
        revokeObjUrl();
        if (nameEl) nameEl.textContent = file.name;
        if (metaEl) metaEl.textContent = (file.size >= 1048576 ? (file.size / 1048576).toFixed(2) + ' MB' : Math.max(1, Math.round(file.size / 1024)) + ' KB') + (file.type ? ' · ' + file.type.split('/').pop().toUpperCase() : '');
        if (preview) preview.classList.remove('hidden');
        if (img) { if (file.type && file.type.startsWith('image/') && typeof URL !== 'undefined' && URL.createObjectURL) { root._epObjUrl = URL.createObjectURL(file); img.src = root._epObjUrl; img.classList.remove('hidden'); } else { img.removeAttribute('src'); img.classList.add('hidden'); } }
        if (progressEl) { progressEl.classList.remove('w-full', 'w-0'); progressEl.style.width = '0%'; requestAnimationFrame(() => { progressEl.style.width = '100%'; }); }
        if (clearBtn) clearBtn.classList.remove('hidden');
        if (/\.csv$/i.test(file.name || '') && typeof FileReader !== 'undefined') {
          const seq = (root._epCsvSeq || 0) + 1; root._epCsvSeq = seq;
          const reader = new FileReader();
          reader.onload = () => { if (root._epCsvSeq === seq) renderCsvMapperPreview(root, reader.result || ''); };
          reader.readAsText(file.slice(0, 4096));
        } else clearCsvBox();
      };
      input.addEventListener('change', () => applyFile(input.files && input.files[0]));
      if (browseBtn) browseBtn.addEventListener('click', (e) => { e.preventDefault(); input.click(); });
      if (clearBtn) clearBtn.addEventListener('click', (e) => { e.preventDefault(); e.stopPropagation(); resetUploader(); });
      if (dropzone) {
        const setDrag = (on) => { dropzone.classList.toggle('border-[var(--accent-primary)]', on); dropzone.classList.toggle('bg-[var(--accent-soft)]', on); };
        dropzone.addEventListener('click', (e) => { if (!e.target.closest('[data-uploader-clear], [data-uploader-browse], input[type="file"], label')) input.click(); });
        dropzone.addEventListener('keydown', (e) => { if ((e.key === 'Enter' || e.key === ' ') && e.target === dropzone) { e.preventDefault(); input.click(); } });
        dropzone.addEventListener('dragover', (e) => { e.preventDefault(); setDrag(true); });
        dropzone.addEventListener('dragleave', (e) => { e.preventDefault(); if (!dropzone.contains(e.relatedTarget)) setDrag(false); });
        dropzone.addEventListener('drop', (e) => {
          e.preventDefault(); setDrag(false);
          const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]; if (!file) return;
          try { const dt = new DataTransfer(); dt.items.add(file); input.files = dt.files; } catch (err) {}
          applyFile(file); if (input.hasAttribute('data-auto-submit')) input.dispatchEvent(new Event('change', { bubbles: true }));
        });
      }
    });
  }

  function buildNotifItemNode(notif) {
    const row = document.createElement('div');
    row.className = 'flex items-start gap-2.5 px-4 py-3 hover:bg-[var(--bg-elevated)] transition-colors';
    const dot = document.createElement('span');
    const sev = String(notif.severity || '').toUpperCase();
    dot.className = 'mt-1 h-2 w-2 shrink-0 rounded-full ' + (sev === 'DANGER' ? 'bg-[var(--status-danger)]' : (sev === 'WARNING' ? 'bg-[var(--status-warning)]' : 'bg-[var(--accent-primary)]'));
    const body = document.createElement('div');
    body.className = 'min-w-0 flex-1';
    const titleEl = document.createElement('p');
    titleEl.className = 'truncate text-xs font-semibold text-[var(--text-primary)]';
    titleEl.textContent = notif.title || 'Alert';
    const msgEl = document.createElement('p');
    msgEl.className = 'mt-0.5 text-xs text-[var(--text-secondary)]';
    msgEl.textContent = notif.message || '';
    body.append(titleEl, msgEl);
    if (notif.feedback_text) {
      const fbEl = document.createElement('p');
      fbEl.className = 'mt-1 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-[11px] italic text-[var(--text-muted)] line-clamp-2';
      fbEl.textContent = '"' + notif.feedback_text + '"';
      body.appendChild(fbEl);
    }
    if (notif.reply_text) {
      const repBox = document.createElement('div');
      repBox.className = 'mt-1 rounded-md bg-[var(--accent-soft)] px-2 py-1 text-[11px] text-[var(--text-primary)]';
      const repLbl = document.createElement('span');
      repLbl.className = 'font-semibold text-[var(--accent-primary)]';
      repLbl.textContent = 'Admin Reply: ';
      const repVal = document.createElement('span');
      repVal.textContent = notif.reply_text;
      repBox.append(repLbl, repVal);
      body.appendChild(repBox);
    }
    row.append(dot, body);
    return row;
  }

  function renderNotificationFeed(data) {
    const badge = document.getElementById('notification-unread-badge');
    const listEl = document.getElementById('notification-list');
    const count = Math.max(0, parseInt(data.unread_count, 10) || 0);
    if (badge) {
      badge.textContent = String(count);
      badge.classList.toggle('hidden', count <= 0);
    }
    if (!listEl) return;
    listEl.textContent = '';
    const items = Array.isArray(data.notifications) ? data.notifications : [];
    if (!items.length) {
      const empty = document.createElement('div');
      empty.className = 'px-4 py-6 text-center text-xs text-[var(--text-muted)]';
      empty.textContent = 'No new alerts.';
      listEl.appendChild(empty);
      return;
    }
    items.forEach((item) => listEl.appendChild(buildNotifItemNode(item)));
  }

  function initLiveNotifications() {
    const bell = document.getElementById('notification-bell-btn');
    if (!bell || typeof fetch !== 'function') return;
    const badge = document.getElementById('notification-unread-badge');
    if (window._epLastUnreadCount === undefined) window._epLastUnreadCount = badge && !badge.classList.contains('hidden') ? (parseInt(badge.textContent, 10) || 0) : 0;
    const pollFeed = () => {
      if (document.visibilityState !== 'visible' || !document.getElementById('notification-bell-btn')) return;
      fetch('/notifications/feed/', { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (!data || !data.ok) return;
          const nextCount = Math.max(0, parseInt(data.unread_count, 10) || 0), prevCount = typeof window._epLastUnreadCount === 'number' ? window._epLastUnreadCount : 0;
          renderNotificationFeed(data);
          if (nextCount > prevCount && Array.isArray(data.notifications) && data.notifications.length && typeof window.showToast === 'function') {
            const top = data.notifications[0];
            window.showToast((top.title || 'Alert') + ': ' + (top.message || ''), 'info');
          }
          window._epLastUnreadCount = nextCount;
        })
        .catch(() => {});
    };
    if (!window._epVisNotifBound) {
      window._epVisNotifBound = true;
      document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') pollFeed(); });
    }
    if (!window._epLiveNotifTimer) window._epLiveNotifTimer = setInterval(pollFeed, 15000);
  }

  function initEduPredictWidgets() { initGlobalSubmitGuards(); initFaqProWidgets(); initGradientUploaders(); initLiveNotifications(); }
  Object.assign(window, { EduPredictProgress, resetEduPredictSubmitLocks: resetSubmitLocks, initEduPredictWidgets });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initEduPredictWidgets); else initEduPredictWidgets();
})();
