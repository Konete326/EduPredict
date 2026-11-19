(function () {
  const TOKEN_TO_CSS = {
    bg_canvas: '--bg-canvas', bg_surface: '--bg-surface', bg_elevated: '--bg-elevated', bg_overlay: '--bg-overlay',
    text_primary: '--text-primary', text_secondary: '--text-secondary', text_muted: '--text-muted', border_subtle: '--border-subtle',
    accent_primary: '--accent-primary', accent_hover: '--accent-hover', accent_soft: '--accent-soft',
    shell_sidebar_bg: '--shell-sidebar-bg', shell_topbar_bg: '--shell-topbar-bg'
  };
  const DEFAULTS = { mode: 'light', shell_theme: 'white', accent: 'indigo', preset: 'neutral', density: 'comfortable', sync_shell: true };
  const STUDIO_CONTROLS = [
    ['[data-theme-mode]', 'data-theme-mode', 'mode'],
    ['[data-shell-theme-btn]', 'data-shell-theme-btn', 'shell_theme'],
    ['[data-accent-swatch]', 'data-accent-swatch', 'accent'],
    ['[data-surface-preset]', 'data-surface-preset', 'preset'],
    ['[data-theme-density]', 'data-theme-density', 'density']
  ];

  let catalog = { modes: [], shell_themes: [], swatches: [], presets: [], save_url: '/theme/preferences/' };
  let shellMap = {}, swatchMap = {}, presetMap = {};
  let currentPrefs = null, saveTimer = null, transitionTimer = null;

  const byId = (id) => document.getElementById(id);
  const readJsonScript = (id) => { const el = byId(id); if (!el) return null; try { return JSON.parse(el.textContent || '{}'); } catch (e) { return null; } };
  const getScopeKey = (p) => 'ep_theme_prefs:' + (p.user_id || 'guest') + ':' + (p.role || 'PORTAL');
  const submitForm = (form) => { if (form) { if (typeof form.requestSubmit === 'function') form.requestSubmit(); else form.submit(); } };
  const getCsrfToken = () => { const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/); return m ? decodeURIComponent(m[1]) : (document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || ''); };
  const toLookup = (list) => {
    const out = {};
    if (Array.isArray(list)) list.forEach((item) => { if (item && item.slug) out[item.slug] = item; });
    else if (list && typeof list === 'object') Object.entries(list).forEach(([k, v]) => { if (v) out[v.slug || k] = v; });
    return out;
  };

  function computeTokens(prefs) {
    const isDark = prefs.mode === 'dark';
    const shell = shellMap[prefs.shell_theme] || shellMap.white || {};
    const swatch = swatchMap[prefs.accent] || swatchMap.indigo || {};
    const preset = presetMap[prefs.preset] || presetMap.neutral || {};
    return {
      bg_canvas: isDark ? (preset.canvas_dark || '#090d16') : (preset.canvas_light || '#f8fafc'),
      bg_surface: isDark ? (preset.surface_dark || '#111827') : (preset.surface_light || '#ffffff'),
      bg_elevated: isDark ? (preset.elevated_dark || '#1e293b') : (preset.elevated_light || '#f1f5f9'),
      bg_overlay: isDark ? 'rgba(2, 6, 23, 0.78)' : 'rgba(15, 23, 42, 0.55)',
      text_primary: isDark ? '#f8fafc' : '#0f172a',
      text_secondary: isDark ? '#cbd5e1' : '#475569',
      text_muted: isDark ? '#94a3b8' : '#64748b',
      border_subtle: isDark ? '#1e293b' : '#e2e8f0',
      accent_primary: swatch.hex || (isDark ? '#6366f1' : '#4f46e5'),
      accent_hover: swatch.hover || (isDark ? '#818cf8' : '#4338ca'),
      accent_soft: isDark ? (swatch.soft_dark || 'rgba(99, 102, 241, 0.14)') : (swatch.soft_light || '#eef2ff'),
      shell_sidebar_bg: isDark ? (shell.sidebar_bg_dark || '#111827') : (shell.sidebar_bg_light || '#ffffff'),
      shell_topbar_bg: isDark ? (shell.topbar_bg_dark || '#111827') : (shell.topbar_bg_light || '#ffffff'),
      force_dark_chrome: Boolean(shell.force_dark_chrome)
    };
  }

  function normalizePrefs(raw) {
    const base = Object.assign({}, DEFAULTS, currentPrefs || {}, raw || {}), doc = document.documentElement;
    const mode = base.mode === 'dark' ? 'dark' : 'light';
    const shellTheme = shellMap[base.shell_theme] ? base.shell_theme : (Object.keys(shellMap).length ? 'white' : (base.shell_theme || 'white'));
    const accent = swatchMap[base.accent] ? base.accent : (Object.keys(swatchMap).length ? 'indigo' : (base.accent || 'indigo'));
    const preset = presetMap[base.preset] ? base.preset : (Object.keys(presetMap).length ? 'neutral' : (base.preset || 'neutral'));
    const density = base.density === 'compact' ? 'compact' : 'comfortable';
    const role = String(base.role || doc.getAttribute('data-active-role') || 'PORTAL').toUpperCase();
    const userId = String(base.user_id || doc.getAttribute('data-user-id') || 'guest');
    const norm = { role, user_id: userId, mode, shell_theme: shellTheme, accent, preset, density, sync_shell: Boolean(base.sync_shell) };
    norm.tokens = (Object.keys(shellMap).length || !raw || !raw.tokens) ? computeTokens(norm) : Object.assign(computeTokens(norm), raw.tokens);
    return norm;
  }

  function setSavePillState(stateText, saving) {
    const pill = byId('theme-studio-save-pill');
    if (!pill) return;
    const labelEl = pill.querySelector('span'), iconEl = pill.querySelector('i');
    if (labelEl) labelEl.textContent = stateText; else pill.textContent = stateText;
    pill.classList.toggle('text-[var(--status-success)]', !saving);
    pill.classList.toggle('text-[var(--text-muted)]', Boolean(saving));
    if (iconEl) iconEl.className = saving ? 'fa-solid fa-spinner fa-spin text-[10px]' : 'fa-solid fa-circle-check text-[10px]';
  }

  function syncStudioUI(prefs) {
    const modal = byId('theme-studio-modal');
    if (modal) {
      STUDIO_CONTROLS.forEach(([sel, attr, key]) => modal.querySelectorAll(sel).forEach((b) => b.setAttribute('aria-pressed', String(b.getAttribute(attr) === prefs[key]))));
      if (byId('theme-studio-sync-toggle')) byId('theme-studio-sync-toggle').setAttribute('aria-checked', prefs.sync_shell ? 'true' : 'false');
    }
    if (byId('theme-studio-topbar-dot')) byId('theme-studio-topbar-dot').style.backgroundColor = prefs.tokens.accent_primary;
    const swatchObj = swatchMap[prefs.accent] || {}, shellObj = shellMap[prefs.shell_theme] || {};
    const textTargets = [
      ['theme-preview-swatch-name', swatchObj.label || prefs.accent],
      ['theme-preview-scope-text', prefs.role],
      ['theme-preview-mode-text', prefs.mode === 'dark' ? 'OLED Dark' : 'Light Mode'],
      ['theme-preview-shell-text', shellObj.label || prefs.shell_theme],
      ['theme-preview-hex-text', prefs.tokens.accent_primary]
    ];
    textTargets.forEach(([id, val]) => { if (byId(id)) byId(id).textContent = val; });
  }

  function applyDomAndStorage(prefs, animate) {
    const doc = document.documentElement;
    if (animate) {
      doc.classList.add('theme-transitioning');
      if (transitionTimer) clearTimeout(transitionTimer);
      transitionTimer = setTimeout(() => doc.classList.remove('theme-transitioning'), 260);
    }
    doc.classList.toggle('dark', prefs.mode === 'dark');
    doc.classList.toggle('density-compact', prefs.density === 'compact');
    doc.setAttribute('data-shell-theme', prefs.shell_theme);
    doc.setAttribute('data-dark-chrome', (prefs.mode === 'dark' || prefs.tokens.force_dark_chrome) ? 'true' : 'false');
    doc.style.colorScheme = prefs.mode === 'dark' ? 'dark' : 'light';
    Object.entries(TOKEN_TO_CSS).forEach(([k, cssVar]) => { if (prefs.tokens[k]) doc.style.setProperty(cssVar, prefs.tokens[k]); });
    syncStudioUI(prefs);
    try { localStorage.setItem(getScopeKey(prefs), JSON.stringify(prefs)); localStorage.setItem('edupredict_theme', prefs.mode); } catch (e) {}
    window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: prefs.mode, prefs, tokens: prefs.tokens } }));
  }

  function postThemePrefs(payload) {
    const token = getCsrfToken(), headers = { 'Content-Type': 'application/json', 'X-Requested-With': 'EduPredict-Theme' };
    if (token) headers['X-CSRFToken'] = token;
    setSavePillState('Saving...', true);
    if (typeof window.clearEduPredictPageCache === 'function') window.clearEduPredictPageCache();
    return fetch(catalog.save_url || '/theme/preferences/', { method: 'POST', credentials: 'same-origin', headers, body: JSON.stringify(payload) })
      .then((r) => (r.ok ? r.json() : null))
      .then((res) => {
        if (res && res.theme_prefs) {
          currentPrefs = normalizePrefs(res.theme_prefs);
          try { localStorage.setItem(getScopeKey(currentPrefs), JSON.stringify(currentPrefs)); } catch (e) {}
          syncStudioUI(currentPrefs);
        }
        setSavePillState('Auto-Saved', false);
        if (typeof window.clearEduPredictPageCache === 'function') window.clearEduPredictPageCache();
      })
      .catch(() => setSavePillState('Auto-Saved', false));
  }

  function schedulePersist(prefs) {
    if (saveTimer) clearTimeout(saveTimer);
    setSavePillState('Saving...', true);
    if (typeof window.clearEduPredictPageCache === 'function') window.clearEduPredictPageCache();
    const body = { mode: prefs.mode, shell_theme: prefs.shell_theme, accent: prefs.accent, preset: prefs.preset, density: prefs.density, sync_shell: prefs.sync_shell };
    saveTimer = setTimeout(() => postThemePrefs(body), 180);
  }

  function applyEduPredictThemePrefs(patch, options) {
    const opts = options || {}, nextPatch = Object.assign({}, patch || {});
    const candidateSync = nextPatch.sync_shell !== undefined ? Boolean(nextPatch.sync_shell) : Boolean((currentPrefs || DEFAULTS).sync_shell);
    const shellObj = shellMap[nextPatch.shell_theme || (currentPrefs || DEFAULTS).shell_theme];
    if (candidateSync && shellObj && shellObj.accent_sync && !nextPatch.accent && (nextPatch.shell_theme || nextPatch.sync_shell === true) && swatchMap[shellObj.accent_sync]) {
      nextPatch.accent = shellObj.accent_sync;
    }
    currentPrefs = normalizePrefs(nextPatch);
    applyDomAndStorage(currentPrefs, opts.animate !== false);
    if (opts.persist !== false) schedulePersist(currentPrefs);
    return currentPrefs;
  }

  function resetEduPredictThemePrefs() {
    if (saveTimer) clearTimeout(saveTimer);
    currentPrefs = normalizePrefs(Object.assign({}, DEFAULTS, { role: currentPrefs?.role, user_id: currentPrefs?.user_id }));
    applyDomAndStorage(currentPrefs, true);
    postThemePrefs({ action: 'reset' });
    return currentPrefs;
  }

  function toggleStudioModal(open) {
    const modal = byId('theme-studio-modal');
    if (!modal || (!open && modal.classList.contains('hidden'))) return;
    if (open && currentPrefs) syncStudioUI(currentPrefs);
    modal.classList.toggle('hidden', !open);
    modal.classList.toggle('flex', open);
    modal.setAttribute('aria-hidden', open ? 'false' : 'true');
    if (typeof window.syncBodyScrollLock === 'function') window.syncBodyScrollLock();
    else if (document.body) document.body.classList.toggle('modal-open', open);
  }
  const openThemeStudioModal = () => toggleStudioModal(true);
  const closeThemeStudioModal = () => toggleStudioModal(false);

  function buildStudentLookup() {
    const map = new Map(), list = readJsonScript('teacher-students-picker-data');
    if (Array.isArray(list)) list.forEach((s) => { const sid = String(s?.student_id || '').trim().toUpperCase(); if (sid) map.set(sid, Object.assign({}, s, { student_id: sid })); });
    document.querySelectorAll('#teacher-roster-table [data-student-id]').forEach((el) => {
      const sid = String(el.getAttribute('data-student-id') || '').trim().toUpperCase();
      if (!sid) return;
      const cur = map.get(sid) || { student_id: sid };
      if (!cur.full_name && el.dataset.fullName) cur.full_name = el.dataset.fullName;
      if (!cur.course_code && el.dataset.courseCode) cur.course_code = el.dataset.courseCode;
      if (el.dataset.internalMarks !== undefined) cur.internal_marks = el.dataset.internalMarks;
      if (el.dataset.attendancePct !== undefined) cur.attendance_pct = el.dataset.attendancePct;
      map.set(sid, cur);
    });
    return map;
  }

  function nextSuggestedStudentId(lookup) {
    let maxNum = 0;
    lookup.forEach((_, sid) => { const m = sid.match(/(\d+)$/); if (m) maxNum = Math.max(maxNum, parseInt(m[1], 10) || 0); });
    return 'STD-2026-' + String(maxNum + 1).padStart(3, '0');
  }

  function initSmartAutomation() {
    document.querySelectorAll('input[type="file"][data-auto-submit="true"]').forEach((input) => {
      if (input.dataset.autoSubmitBound === '1') return;
      input.dataset.autoSubmitBound = '1';
      input.addEventListener('change', () => {
        const file = input.files && input.files[0];
        if (!file) return;
        const form = input.closest('form');
        const nameEl = (form && form.querySelector('[data-file-name]')) || byId('teacher-file-name');
        if (nameEl) { nameEl.textContent = 'Selected: ' + file.name; nameEl.classList.remove('hidden'); nameEl.classList.add('text-[var(--accent-primary)]', 'font-semibold'); }
        const btn = form ? form.querySelector('button[type="submit"], input[type="submit"]') : null;
        if (btn && btn.tagName === 'BUTTON') { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-xs"></i><span>Uploading &amp; Predicting...</span>'; }
        else if (btn) { btn.disabled = true; btn.value = 'Uploading & Predicting...'; }
        submitForm(form);
      });
    });

    document.querySelectorAll('select[data-auto-filter="true"]').forEach((sel) => {
      if (sel.dataset.autoFilterBound === '1') return;
      sel.dataset.autoFilterBound = '1';
      sel.addEventListener('change', () => submitForm(sel.closest('form')));
    });

    const idInput = byId('entry-student-id');
    if (idInput && idInput.dataset.autoFillBound !== '1') {
      idInput.dataset.autoFillBound = '1';
      idInput.addEventListener('focus', () => { if (!idInput.value.trim()) idInput.value = nextSuggestedStudentId(buildStudentLookup()); });
      const syncFromId = (e) => {
        if (e && (e.isComposing || e.keyCode === 229)) return;
        const match = buildStudentLookup().get(idInput.value.trim().toUpperCase());
        if (!match) return;
        if (byId('entry-full-name') && match.full_name) byId('entry-full-name').value = match.full_name;
        if (byId('entry-course') && match.course_code) byId('entry-course').value = match.course_code;
        if (byId('entry-marks') && match.internal_marks !== undefined && match.internal_marks !== '') byId('entry-marks').value = match.internal_marks;
        if (byId('entry-att') && match.attendance_pct !== undefined && match.attendance_pct !== '') byId('entry-att').value = match.attendance_pct;
      };
      idInput.addEventListener('input', syncFromId);
      idInput.addEventListener('change', syncFromId);
    }
  }

  function initThemeStudio() {
    const parsedCatalog = readJsonScript('ep-theme-catalog-data');
    if (parsedCatalog && typeof parsedCatalog === 'object') catalog = Object.assign(catalog, parsedCatalog);
    shellMap = toLookup(catalog.shell_themes); swatchMap = toLookup(catalog.swatches); presetMap = toLookup(catalog.presets);
    const serverPrefs = readJsonScript('ep-theme-prefs-data') || {};
    let merged = Object.assign({}, serverPrefs);
    try {
      const scoped = localStorage.getItem(getScopeKey(normalizePrefs(merged)));
      if (scoped) {
        const parsed = JSON.parse(scoped);
        if (parsed && (!parsed.user_id || parsed.user_id === merged.user_id) && (!parsed.role || parsed.role === merged.role)) {
          merged = Object.assign({}, serverPrefs, parsed, { role: merged.role, user_id: merged.user_id });
        }
      }
    } catch (e) {}
    currentPrefs = normalizePrefs(merged);
    applyDomAndStorage(currentPrefs, false);
    const modal = byId('theme-studio-modal');
    if (modal && modal.dataset.studioBound !== '1') {
      modal.dataset.studioBound = '1';
      modal.addEventListener('click', (e) => {
        for (const [sel, attr, key] of STUDIO_CONTROLS) {
          const btn = e.target.closest(sel);
          if (btn) { applyEduPredictThemePrefs({ [key]: btn.getAttribute(attr) }); return; }
        }
        if (e.target.closest('#theme-studio-sync-toggle')) { applyEduPredictThemePrefs({ sync_shell: !currentPrefs.sync_shell }); return; }
        if (e.target.closest('#theme-studio-reset-btn')) resetEduPredictThemePrefs();
      });
    }
    initSmartAutomation();
  }

  Object.assign(window, { openThemeStudioModal, closeThemeStudioModal, applyEduPredictThemePrefs, resetEduPredictThemePrefs, initSmartAutomation });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initThemeStudio);
  else initThemeStudio();
})();
