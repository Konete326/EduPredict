(function () {
  const VIEW_PREFIX = 'ep_dir_view:', RING_CIRC = 201.06;
  let globalsBound = false, drawerCloseTimer = null, fetchSeq = 0;

  const byId = (id) => document.getElementById(id);
  const mk = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = String(text); return n; };
  const setText = (id, val) => { const el = byId(id); if (el) el.textContent = val == null ? '' : String(val); };

  function fallbackCopy(val) {
    try {
      const ta = document.createElement('textarea');
      ta.value = val; ta.setAttribute('readonly', 'true'); ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return ok;
    } catch (e) { return false; }
  }

  function copyTextToClipboard(text) {
    const val = String(text || '');
    if (!val) return Promise.resolve(false);
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      return navigator.clipboard.writeText(val).then(() => true).catch(() => fallbackCopy(val));
    }
    return Promise.resolve(fallbackCopy(val));
  }

  function flashCopiedState(btn) {
    if (!btn) return;
    if (btn._copyTimer) clearTimeout(btn._copyTimer);
    if (btn.dataset.origHtml === undefined) btn.dataset.origHtml = btn.innerHTML;
    btn.textContent = '✓ Copied';
    btn.classList.add('text-[var(--status-success)]');
    btn._copyTimer = setTimeout(() => {
      if (btn.dataset.origHtml !== undefined) { btn.innerHTML = btn.dataset.origHtml; delete btn.dataset.origHtml; }
      btn.classList.remove('text-[var(--status-success)]');
      btn._copyTimer = null;
    }, 1400);
  }

  function resolveContainer(target) {
    if (!target) return null;
    if (typeof target === 'string') return byId(target);
    return target.closest ? (target.closest('[data-directory-cards]') || target) : target;
  }

  function setDirectoryView(target, mode, persist) {
    const container = resolveContainer(target);
    if (!container) return;
    const nextMode = mode === 'cards' ? 'cards' : 'table';
    container.setAttribute('data-directory-mode', nextMode);
    const tableWrap = container.querySelector('[data-directory-table-view]'), cardsWrap = container.querySelector('[data-directory-cards-view]');
    if (tableWrap) { tableWrap.classList.add('hidden'); tableWrap.classList.toggle('md:block', nextMode === 'table'); }
    if (cardsWrap) { cardsWrap.classList.toggle('md:hidden', nextMode === 'table'); cardsWrap.classList.toggle('md:grid', nextMode === 'cards'); }
    container.querySelectorAll('[data-directory-view-toggle] [data-set-view]').forEach((btn) => {
      const active = btn.getAttribute('data-set-view') === nextMode;
      btn.setAttribute('aria-pressed', active ? 'true' : 'false');
      btn.classList.toggle('bg-[var(--bg-surface)]', active);
      btn.classList.toggle('text-[var(--accent-primary)]', active);
      btn.classList.toggle('shadow-sm', active);
      btn.classList.toggle('text-[var(--text-secondary)]', !active);
    });
    if (persist !== false && container.id) {
      try { localStorage.setItem(VIEW_PREFIX + container.id, nextMode); } catch (e) {}
    }
  }

  function renderDrawerBadge(riskLevel, riskStatus, score) {
    const badge = byId('s360-risk-badge');
    if (!badge) return;
    const dotCls = riskStatus === 'danger' ? 'bg-[var(--status-danger)]' : (riskStatus === 'warning' ? 'bg-[var(--status-warning)]' : (riskStatus === 'success' ? 'bg-[var(--status-success)]' : 'bg-[var(--accent-primary)]'));
    badge.textContent = '';
    badge.append(mk('span', 'h-1.5 w-1.5 rounded-full ' + dotCls), mk('span', '', String(riskLevel || 'INFO').toUpperCase() + (score != null ? ' (' + Math.round(Number(score) * 100) + '%)' : '')));
  }

  function renderDrawerSummary(s) {
    const avatarBox = byId('s360-avatar');
    if (avatarBox) {
      avatarBox.textContent = '';
      if (s.avatar_url) { const im = mk('img', 'h-full w-full object-cover'); im.src = s.avatar_url; im.alt = s.full_name || s.student_id || 'Student'; avatarBox.appendChild(im); }
      else avatarBox.textContent = s.initials || 'ST';
    }
    setText('s360-name', s.full_name || s.student_id || 'Student');
    const idBtn = byId('s360-id');
    if (idBtn) {
      if (idBtn._copyTimer) { clearTimeout(idBtn._copyTimer); idBtn._copyTimer = null; }
      delete idBtn.dataset.origHtml; idBtn.classList.remove('text-[var(--status-success)]');
      idBtn.setAttribute('data-copy-text', s.student_id || ''); idBtn.textContent = '';
      idBtn.append(mk('span', '', s.student_id || '-'), mk('i', 'fa-regular fa-copy text-[10px]'));
    }
    renderDrawerBadge(s.risk_level, s.risk_status, s.dropout_risk_score);
    const att = Math.max(0, Math.min(100, Number(s.avg_attendance) || 0));
    setText('s360-att-pct', att.toFixed(1) + '%');
    const ring = byId('s360-att-ring');
    if (ring) {
      ring.style.stroke = att >= 75 ? 'var(--status-success)' : (att >= 60 ? 'var(--status-warning)' : 'var(--status-danger)');
      ring.style.strokeDashoffset = String(RING_CIRC);
      requestAnimationFrame(() => { ring.style.strokeDashoffset = (RING_CIRC * (1 - att / 100)).toFixed(2); });
    }
    setText('s360-gpa', s.predicted_gpa != null ? Number(s.predicted_gpa).toFixed(2) : (s.previous_gpa != null ? Number(s.previous_gpa).toFixed(2) : '-'));
    setText('s360-marks', s.avg_marks != null ? Number(s.avg_marks).toFixed(1) : '-');
    setText('s360-batch', s.batch || '-');

    const reasonsEl = byId('s360-reasons');
    if (reasonsEl) {
      reasonsEl.textContent = '';
      const reasons = Array.isArray(s.risk_reasons) && s.risk_reasons.length ? s.risk_reasons : [s.recommendation || 'Attendance and grades are currently being monitored.'];
      reasons.forEach((txt) => { const li = mk('li', 'flex items-start gap-2'); li.append(mk('i', 'fa-solid fa-circle-dot mt-1 text-[9px] text-[var(--accent-primary)] shrink-0'), mk('span', '', txt)); reasonsEl.appendChild(li); });
    }
    const coursesEl = byId('s360-courses');
    if (coursesEl) {
      coursesEl.textContent = '';
      const courses = Array.isArray(s.courses) ? s.courses : [];
      if (!courses.length) coursesEl.appendChild(mk('p', 'rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-canvas)] px-3 py-2.5 text-xs text-[var(--text-muted)]', 'No course enrollments recorded yet.'));
      else courses.forEach((c) => {
        const row = mk('div', 'flex items-center justify-between gap-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-canvas)] px-3 py-2 text-xs');
        row.append(mk('span', 'font-mono font-semibold text-[var(--accent-primary)]', c.course_code || '-'), mk('span', 'tabular-nums text-[var(--text-secondary)]', 'Att ' + Number(c.attendance_pct || 0).toFixed(1) + '% · Marks ' + Number(c.internal_marks || 0).toFixed(1)));
        coursesEl.appendChild(row);
      });
    }
    const alertsEl = byId('s360-alerts');
    if (alertsEl) {
      alertsEl.textContent = '';
      const alerts = Array.isArray(s.recent_alerts) ? s.recent_alerts : [];
      if (!alerts.length) alertsEl.appendChild(mk('p', 'rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-canvas)] px-3 py-2.5 text-xs text-[var(--text-muted)]', 'No recent alerts for this student.'));
      else alerts.forEach((a) => {
        const card = mk('div', 'rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-canvas)] p-2.5 space-y-1 text-xs');
        const top = mk('div', 'flex items-center justify-between gap-2');
        top.append(mk('span', 'font-semibold text-[var(--text-primary)] truncate', a.title || 'Alert'), mk('span', 'font-mono text-[10px] text-[var(--text-muted)] shrink-0', a.created || ''));
        card.append(top, mk('p', 'text-[11px] text-[var(--text-secondary)]', a.message || ''));
        alertsEl.appendChild(card);
      });
    }
    const attrs = s.edit_attrs || {}, firstCourse = (Array.isArray(s.courses) && s.courses[0] && s.courses[0].course_code) || '';
    const applyBtnAttrs = (btn) => {
      if (!btn) return;
      Object.assign(btn.dataset, {
        studentId: attrs.student_id || s.student_id || '', fullName: attrs.full_name || s.full_name || '',
        batch: attrs.batch || s.batch || '2026-A', courseCode: attrs.course_code || firstCourse || 'CS-101',
        attendancePct: String(attrs.attendance_pct ?? s.avg_attendance ?? '85'), internalMarks: String(attrs.internal_marks ?? s.avg_marks ?? '75'),
        assignmentScore: String(attrs.assignment_score ?? s.avg_marks ?? '75'), lmsHoursWeekly: String(attrs.lms_hours_weekly ?? '8'),
        previousGpa: String(attrs.previous_gpa ?? s.previous_gpa ?? '3.0')
      });
    };
    const editBtn = byId('s360-edit-marks-btn'), alertBtn = byId('s360-send-alert-btn');
    if (editBtn) { applyBtnAttrs(editBtn); editBtn.classList.toggle('hidden', typeof window.openUpdateMarksModal !== 'function'); }
    if (alertBtn) { applyBtnAttrs(alertBtn); alertBtn.classList.toggle('hidden', typeof window.openSendAlertModal !== 'function'); }
  }

  function closeStudent360Drawer(immediate) {
    const drawer = byId('student-360-drawer');
    if (!drawer) return;
    if (drawerCloseTimer) { clearTimeout(drawerCloseTimer); drawerCloseTimer = null; }
    drawer.classList.remove('is-drawer-open');
    drawer.setAttribute('aria-hidden', 'true');
    const finish = () => { drawer.classList.add('hidden'); drawer.classList.remove('flex'); if (typeof window.syncBodyScrollLock === 'function') window.syncBodyScrollLock(); };
    if (immediate) finish();
    else drawerCloseTimer = setTimeout(() => { drawerCloseTimer = null; finish(); }, 220);
  }

  function openStudent360Drawer(sid) {
    const cleanId = String(sid || '').trim(), drawer = byId('student-360-drawer');
    if (!cleanId || !drawer) return;
    if (drawerCloseTimer) { clearTimeout(drawerCloseTimer); drawerCloseTimer = null; }
    const token = ++fetchSeq;
    drawer.classList.remove('is-drawer-open', 'hidden'); drawer.classList.add('flex'); drawer.setAttribute('aria-hidden', 'false');
    void drawer.offsetWidth; requestAnimationFrame(() => drawer.classList.add('is-drawer-open'));
    if (typeof window.syncBodyScrollLock === 'function') window.syncBodyScrollLock();
    setText('s360-name', 'Student ' + cleanId);
    if (byId('s360-loading')) byId('s360-loading').classList.remove('hidden');
    if (byId('s360-error')) byId('s360-error').classList.add('hidden');
    if (byId('s360-body')) byId('s360-body').classList.add('hidden');
    if (byId('s360-edit-marks-btn')) byId('s360-edit-marks-btn').classList.add('hidden');
    if (byId('s360-send-alert-btn')) byId('s360-send-alert-btn').classList.add('hidden');
    if (byId('s360-att-ring')) byId('s360-att-ring').style.strokeDashoffset = String(RING_CIRC);

    fetch('/students/' + encodeURIComponent(cleanId) + '/summary/', { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then((res) => res.json().catch(() => ({ ok: false, error: 'Unable to read summary.' })))
      .then((data) => {
        if (token !== fetchSeq) return;
        if (byId('s360-loading')) byId('s360-loading').classList.add('hidden');
        if (!data || !data.ok || !data.summary) {
          if (byId('s360-error')) { byId('s360-error').textContent = (data && data.error) || 'Student summary unavailable.'; byId('s360-error').classList.remove('hidden'); }
          return;
        }
        renderDrawerSummary(data.summary);
        if (byId('s360-body')) byId('s360-body').classList.remove('hidden');
      })
      .catch(() => {
        if (token !== fetchSeq) return;
        if (byId('s360-loading')) byId('s360-loading').classList.add('hidden');
        if (byId('s360-error')) { byId('s360-error').textContent = 'Could not load student summary.'; byId('s360-error').classList.remove('hidden'); }
      });
  }

  function bindAnalystStudent360Cells() {
    const table = byId('analyst-predictions-table');
    if (!table) return;
    table.querySelectorAll('tbody tr:not([data-empty-row])').forEach((tr) => {
      const cell = tr.querySelector('td');
      if (!cell || cell.dataset.s360Bound === '1') return;
      const sid = (cell.textContent || '').trim();
      if (!sid) return;
      cell.dataset.s360Bound = '1'; cell.textContent = '';
      const btn = mk('button', 'inline-flex items-center gap-1.5 font-mono text-xs font-semibold text-[var(--accent-primary)] hover:underline');
      btn.type = 'button'; btn.title = 'Open Student 360 summary';
      btn.append(mk('span', '', sid), mk('i', 'fa-solid fa-up-right-from-square text-[10px] opacity-70'));
      btn.addEventListener('click', () => openStudent360Drawer(sid));
      cell.appendChild(btn);
    });
  }

  function bindGlobalsOnce() {
    if (globalsBound) return;
    globalsBound = true;
    document.addEventListener('click', (e) => {
      const copyBtn = e.target.closest('[data-copy-text]');
      if (copyBtn) { e.stopPropagation(); const text = copyBtn.getAttribute('data-copy-text'); if (text) copyTextToClipboard(text).then(() => flashCopiedState(copyBtn)); return; }
      const viewBtn = e.target.closest('[data-directory-view-toggle] [data-set-view]');
      if (viewBtn) setDirectoryView(viewBtn, viewBtn.getAttribute('data-set-view'), true);
    });
    const editBtn = byId('s360-edit-marks-btn'), alertBtn = byId('s360-send-alert-btn');
    if (editBtn) editBtn.addEventListener('click', () => { closeStudent360Drawer(true); if (typeof window.openUpdateMarksModal === 'function') window.openUpdateMarksModal(editBtn); });
    if (alertBtn) alertBtn.addEventListener('click', () => { closeStudent360Drawer(true); if (typeof window.openSendAlertModal === 'function') window.openSendAlertModal(alertBtn); });
    document.addEventListener('keydown', (e) => {
      if (e.isComposing || e.keyCode === 229 || e.key !== 'Escape') return;
      const drawer = byId('student-360-drawer');
      if (drawer && !drawer.classList.contains('hidden')) closeStudent360Drawer();
    });
  }

  function updateStreamCellBadge(cell, dotCls, labelText) {
    if (!cell) return;
    const dot = cell.querySelector('span.rounded-full');
    const pill = dot ? dot.parentElement : cell.querySelector('span');
    const lbl = pill ? Array.from(pill.children).find((el) => el !== dot) : null;
    if (dot) {
      dot.classList.remove('bg-[var(--status-success)]', 'bg-[var(--status-warning)]', 'bg-[var(--status-danger)]', 'bg-[var(--accent-primary)]');
      dot.classList.add(dotCls);
    }
    if (lbl) lbl.textContent = labelText;
    else if (pill && !dot) pill.textContent = labelText;
    else if (!pill) cell.textContent = labelText;
  }

  function syncStreamPredictionTable(events) {
    const table = byId('analyst-predictions-table');
    if (!table || !Array.isArray(events) || !events.length) return;
    const evMap = new Map();
    events.forEach((ev) => {
      const sid = String(ev && ev.student_id ? ev.student_id : '').trim().toUpperCase();
      if (sid) evMap.set(sid, ev);
    });
    if (!evMap.size) return;
    const container = table.closest ? table.closest('[data-paginated-container]') : null;
    const mobileCards = container ? container.querySelectorAll('[data-mobile-card][data-page-item]') : [];
    table.querySelectorAll('tbody tr:not([data-empty-row])').forEach((tr, idx) => {
      const sid = (tr.cells[0]?.textContent || '').trim().toUpperCase();
      const ev = sid ? evMap.get(sid) : null;
      if (!ev || tr.cells.length < 10) return;
      const rawAtt = ev.attendance_pct != null ? ev.attendance_pct : ev.attendance;
      const attNum = rawAtt != null && String(rawAtt).trim() !== '' && typeof rawAtt !== 'boolean' ? Number(rawAtt) : NaN;
      const attText = Number.isFinite(attNum) ? attNum.toFixed(1) + '%' : null;
      const gpaNum = ev.predicted_gpa != null && String(ev.predicted_gpa).trim() !== '' && typeof ev.predicted_gpa !== 'boolean' ? Number(ev.predicted_gpa) : NaN;
      const gpaText = Number.isFinite(gpaNum) ? gpaNum.toFixed(2) : '-';
      const risk = String(ev.risk_level || '').trim().toUpperCase();
      const riskDot = risk === 'HIGH' ? 'bg-[var(--status-danger)]' : (risk === 'MEDIUM' ? 'bg-[var(--status-warning)]' : 'bg-[var(--status-success)]');
      const riskText = ev.risk_text || ev.risk_level || '';
      const isAnom = Boolean(ev.is_anomaly);
      const anomDot = isAnom ? 'bg-[var(--status-danger)]' : 'bg-[var(--status-success)]';
      const anomText = isAnom ? 'Flagged' : 'Normal';
      if (attText !== null) tr.cells[4].textContent = attText;
      tr.cells[6].textContent = gpaText;
      updateStreamCellBadge(tr.cells[7], riskDot, riskText);
      updateStreamCellBadge(tr.cells[8], anomDot, anomText);
      tr.cells[9].textContent = ev.tip || tr.cells[9].textContent;
      const card = mobileCards[idx];
      if (card && card.children.length >= 10) {
        const valBox = (k) => { const row = card.children[k]; return row ? ((row.querySelector ? row.querySelector('div.text-right') : null) || (row.children ? row.children[1] : null)) : null; };
        if (attText !== null && valBox(4)) valBox(4).textContent = attText;
        if (valBox(6)) valBox(6).textContent = gpaText;
        updateStreamCellBadge(valBox(7), riskDot, riskText);
        updateStreamCellBadge(valBox(8), anomDot, anomText);
        if (valBox(9)) valBox(9).textContent = ev.tip || valBox(9).textContent;
      }
    });
    if (container && container._paginationController && typeof container._paginationController.refreshSearchText === 'function') container._paginationController.refreshSearchText();
  }

  function initDirectoryUI() {
    bindGlobalsOnce();
    document.querySelectorAll('[data-directory-cards]').forEach((container) => {
      let saved = 'table';
      if (container.id) { try { const raw = localStorage.getItem(VIEW_PREFIX + container.id); if (raw === 'cards' || raw === 'table') saved = raw; } catch (e) {} }
      setDirectoryView(container, saved, false);
    });
    bindAnalystStudent360Cells();
  }

  if (typeof window.reinitEduPredictUI === 'function' && !window.reinitEduPredictUI._dirWrapped) {
    const orig = window.reinitEduPredictUI;
    const wrapped = function () {
      if (window._epAnalystStreamTimer) { clearInterval(window._epAnalystStreamTimer); window._epAnalystStreamTimer = null; }
      closeStudent360Drawer(true);
      orig();
      initDirectoryUI();
      if (typeof window.initAnalystPage === 'function' && byId('live-stream-toggle-btn')) window.initAnalystPage();
    };
    wrapped._dirWrapped = true;
    window.reinitEduPredictUI = wrapped;
  }

  Object.assign(window, { initDirectoryUI, setDirectoryView, openStudent360Drawer, closeStudent360Drawer, copyTextToClipboard, syncStreamPredictionTable });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initDirectoryUI);
  else initDirectoryUI();
})();
