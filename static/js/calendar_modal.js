(function () {
  const NOTES_KEY = 'ep_calendar_notes_v1';
  const NOTE_HEX = { yellow: '#ffd83d', pink: '#ff9dc3', mint: '#8ee5b0', sky: '#9bcdff' };
  const MONTHS_LONG = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const WEEKDAYS_LONG = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  const modal = document.getElementById('ep-tearoff-calendar-modal');
  if (!modal) return;
  const $id = (id) => document.getElementById(id);

  const sheetHost = $id('toc-sheet-host');
  const activeSheet = $id('toc-active-sheet');
  const crumbHost = $id('toc-crumb-host');
  const monthHeading = $id('toc-month-heading');
  const sheetCounter = $id('toc-sheet-counter');
  const monthTicks = $id('toc-month-ticks');
  const dayGrid = $id('toc-day-grid');
  const sideMonthYear = $id('toc-side-month-year');
  const todayBtn = $id('toc-today-btn');
  const bigDay = $id('toc-big-day');
  const sideWeekday = $id('toc-side-weekday');
  const sideFullDate = $id('toc-side-full-date');
  const sideNotes = $id('toc-side-notes');
  const pinBtn = $id('toc-pin-btn');
  const pinLabel = $id('toc-pin-label');
  const noteEditor = $id('toc-note-editor');
  const noteDateLabel = $id('toc-note-date-label');
  const noteInput = $id('toc-note-input');
  const noteSaveBtn = $id('toc-note-save');
  const noteDeleteBtn = $id('toc-note-delete');
  const noteColorsEl = $id('toc-note-colors');
  const prevBtn = $id('toc-prev-month');
  const nextBtn = $id('toc-next-month');
  const tearPullBtn = $id('toc-tear-pull-btn');
  const clearBtn = $id('toc-clear-btn');
  const cancelBtn = $id('toc-cancel-btn');
  const applyBtn = $id('toc-apply-btn');
  const closeXBtn = $id('toc-close-x');

  let targetInput = null;
  let viewYear = new Date().getFullYear();
  let viewMonth = new Date().getMonth();
  let selectedKey = '';
  let minKey = '';
  let maxKey = '';
  let activeNoteColor = 'yellow';
  let tearing = false;
  let pointerDownOnBackdrop = false;

  const pad2 = (n) => String(n).padStart(2, '0');
  const toKey = (y, m, d) => y + '-' + pad2(m + 1) + '-' + pad2(d);
  const parseKey = (key) => {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(key || '').trim());
    if (!m) return null;
    const y = Number(m[1]), mo = Number(m[2]) - 1, d = Number(m[3]);
    const dt = new Date(y, mo, d);
    return dt.getFullYear() === y && dt.getMonth() === mo && dt.getDate() === d ? { y, m: mo, d, weekday: dt.getDay() } : null;
  };
  const todayKey = () => {
    const now = new Date();
    return toKey(now.getFullYear(), now.getMonth(), now.getDate());
  };
  const isKeyAllowed = (key) => (!minKey || key >= minKey) && (!maxKey || key <= maxKey);

  function loadNotes() {
    try {
      const parsed = JSON.parse(localStorage.getItem(NOTES_KEY) || '{}');
      return parsed && typeof parsed === 'object' ? parsed : {};
    } catch (e) {
      return {};
    }
  }

  function saveNotes(notes) {
    try {
      localStorage.setItem(NOTES_KEY, JSON.stringify(notes));
    } catch (e) {}
  }

  function spawnCrumbs() {
    if (!crumbHost) return;
    crumbHost.innerHTML = '';
    for (let i = 0; i < 12; i++) {
      const bit = document.createElement('span');
      bit.className = 'toc-crumb';
      bit.style.left = (8 + i * 7.5) + '%';
      bit.style.setProperty('--s', (2 + Math.random() * 2.5).toFixed(1) + 'px');
      bit.style.setProperty('--x1', ((Math.random() - 0.5) * 48).toFixed(1) + 'px');
      bit.style.setProperty('--y1', (36 + Math.random() * 72).toFixed(1) + 'px');
      bit.style.setProperty('--r', ((Math.random() - 0.5) * 520).toFixed(0) + 'deg');
      bit.style.setProperty('--d', (0.42 + Math.random() * 0.35).toFixed(2) + 's');
      crumbHost.appendChild(bit);
    }
  }

  function renderSidePanel(notes) {
    const tKey = todayKey();
    const sel = parseKey(selectedKey) || parseKey(tKey);
    const activeKey = sel ? toKey(sel.y, sel.m, sel.d) : tKey;
    if (sideMonthYear) sideMonthYear.textContent = MONTHS_SHORT[viewMonth].toUpperCase() + ' ' + viewYear;
    if (todayBtn) todayBtn.classList.toggle('hidden', tKey.startsWith(viewYear + '-' + pad2(viewMonth + 1) + '-') && selectedKey === tKey);
    if (bigDay && sel) {
      bigDay.textContent = sel.d;
      bigDay.classList.remove('toc-big');
      void bigDay.offsetWidth;
      bigDay.classList.add('toc-big');
    }
    if (sideWeekday && sel) sideWeekday.textContent = WEEKDAYS_LONG[sel.weekday];
    if (sideFullDate) sideFullDate.textContent = activeKey;
    if (pinLabel && sel) pinLabel.textContent = (notes[activeKey] ? 'Edit note on the ' : 'Pin a note on the ') + sel.d;
    if (!sideNotes) return;

    const prefix = viewYear + '-' + pad2(viewMonth + 1) + '-';
    const monthEntries = Object.keys(notes).filter((k) => k.startsWith(prefix)).sort();
    sideNotes.innerHTML = '';
    if (!monthEntries.length) {
      const li = document.createElement('li');
      li.className = 'italic text-white/70';
      li.textContent = 'Nothing pinned in ' + MONTHS_LONG[viewMonth] + ' yet.';
      sideNotes.appendChild(li);
      return;
    }
    monthEntries.slice(0, 3).forEach((k) => {
      const item = notes[k] || {};
      const li = document.createElement('li');
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'flex w-full items-center gap-2 rounded-lg px-1.5 py-0.5 text-left hover:bg-white/15';
      const dot = document.createElement('span');
      dot.className = 'h-2.5 w-2.5 shrink-0 rounded-[2px]';
      dot.style.background = NOTE_HEX[item.color] || NOTE_HEX.yellow;
      const dayEl = document.createElement('span');
      dayEl.className = 'w-5 shrink-0 font-semibold tabular-nums';
      dayEl.textContent = k.slice(8, 10);
      const txt = document.createElement('span');
      txt.className = 'truncate italic';
      txt.textContent = item.text || 'Note';
      btn.append(dot, dayEl, txt);
      btn.addEventListener('click', () => {
        if (!isKeyAllowed(k)) return;
        selectedKey = k;
        renderAll();
        openNoteEditor();
      });
      li.appendChild(btn);
      sideNotes.appendChild(li);
    });
  }

  function renderMonthTicks() {
    if (!monthTicks) return;
    monthTicks.innerHTML = '';
    MONTHS_SHORT.forEach((label, idx) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'toc-tick';
      btn.textContent = label;
      btn.setAttribute('aria-current', idx === viewMonth ? 'true' : 'false');
      btn.addEventListener('click', () => {
        if (idx !== viewMonth) switchMonth(viewYear, idx, idx > viewMonth ? 1 : -1);
      });
      monthTicks.appendChild(btn);
    });
  }

  function renderGrid(notes) {
    if (!dayGrid) return;
    dayGrid.innerHTML = '';
    const tKey = todayKey();
    const firstDay = new Date(viewYear, viewMonth, 1).getDay();
    for (let i = 0; i < 42; i++) {
      const dt = new Date(viewYear, viewMonth, 1 - firstDay + i);
      const y = dt.getFullYear(), m = dt.getMonth(), d = dt.getDate();
      const key = toKey(y, m, d);
      const inMonth = m === viewMonth && y === viewYear;
      const wd = dt.getDay();
      const allowed = isKeyAllowed(key);

      const cell = document.createElement('div');
      cell.className = 'toc-cell';
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'toc-day-btn';
      btn.textContent = pad2(d);
      btn.dataset.tocDay = key;
      btn.dataset.out = inMonth ? 'false' : 'true';
      btn.dataset.weekend = wd === 0 || wd === 6 ? 'true' : 'false';
      btn.dataset.today = key === tKey ? 'true' : 'false';
      btn.dataset.selected = key === selectedKey ? 'true' : 'false';
      btn.disabled = !allowed;
      btn.setAttribute('aria-label', WEEKDAYS_LONG[wd] + ', ' + MONTHS_LONG[m] + ' ' + d + ', ' + y);
      btn.addEventListener('click', () => {
        if (!allowed) return;
        selectedKey = key;
        if (!inMonth) switchMonth(y, m, y > viewYear || (y === viewYear && m > viewMonth) ? 1 : -1);
        else renderAll();
      });
      btn.addEventListener('dblclick', () => {
        if (!allowed) return;
        selectedKey = key;
        applySelection();
      });
      cell.appendChild(btn);
      if (notes[key] && notes[key].text) {
        const dot = document.createElement('span');
        dot.className = 'toc-note-dot';
        dot.style.background = NOTE_HEX[notes[key].color] || NOTE_HEX.yellow;
        cell.appendChild(dot);
      }
      dayGrid.appendChild(cell);
    }
  }

  function renderAll() {
    const notes = loadNotes();
    if (monthHeading) {
      monthHeading.innerHTML = '';
      const yrSpan = document.createElement('span');
      yrSpan.className = 'font-light text-[var(--text-muted)]';
      yrSpan.textContent = String(viewYear);
      monthHeading.append(document.createTextNode(MONTHS_LONG[viewMonth] + ' '), yrSpan);
    }
    if (sheetCounter) sheetCounter.textContent = 'Sheet ' + pad2(viewMonth + 1) + '/12';
    renderMonthTicks();
    renderGrid(notes);
    renderSidePanel(notes);
  }

  function switchMonth(nextY, nextM, dir) {
    if (tearing || !activeSheet || !sheetHost) {
      viewYear = nextY;
      viewMonth = nextM;
      renderAll();
      return;
    }
    if (dir > 0) {
      tearing = true;
      const clone = activeSheet.cloneNode(true);
      clone.removeAttribute('id');
      clone.classList.add('toc-paper-tear-out');
      clone.style.zIndex = '24';
      sheetHost.appendChild(clone);
      spawnCrumbs();
      viewYear = nextY;
      viewMonth = nextM;
      renderAll();
      window.setTimeout(() => {
        clone.remove();
        tearing = false;
      }, 450);
    } else {
      viewYear = nextY;
      viewMonth = nextM;
      renderAll();
      activeSheet.classList.remove('toc-paper-enter');
      void activeSheet.offsetWidth;
      activeSheet.classList.add('toc-paper-enter');
    }
  }

  function stepMonth(delta) {
    const dt = new Date(viewYear, viewMonth + delta, 1);
    switchMonth(dt.getFullYear(), dt.getMonth(), delta > 0 ? 1 : -1);
  }

  function updateSwatchState() {
    if (!noteColorsEl) return;
    noteColorsEl.querySelectorAll('[data-note-color]').forEach((btn) => {
      const active = btn.getAttribute('data-note-color') === activeNoteColor;
      btn.style.outline = active ? '2px solid #ffffff' : 'none';
      btn.style.outlineOffset = '1px';
    });
  }

  function openNoteEditor() {
    if (!noteEditor || !noteInput) return;
    const notes = loadNotes();
    const key = selectedKey || todayKey();
    const existing = notes[key] || { text: '', color: 'yellow' };
    activeNoteColor = existing.color || 'yellow';
    if (noteDateLabel) noteDateLabel.textContent = 'Note · ' + key;
    noteInput.value = existing.text || '';
    updateSwatchState();
    noteEditor.classList.remove('hidden');
    noteInput.focus();
  }

  function openModal(inputEl) {
    targetInput = inputEl || null;
    minKey = targetInput ? String(targetInput.min || '').trim() : '';
    maxKey = targetInput ? String(targetInput.max || '').trim() : '';
    const initial = targetInput ? parseKey(targetInput.value) : null;
    const fallback = parseKey(maxKey && todayKey() > maxKey ? maxKey : todayKey());
    const start = initial || fallback || { y: new Date().getFullYear(), m: new Date().getMonth(), d: new Date().getDate() };
    viewYear = start.y;
    viewMonth = start.m;
    selectedKey = toKey(start.y, start.m, start.d);
    if (noteEditor) noteEditor.classList.add('hidden');
    if (clearBtn) clearBtn.classList.toggle('hidden', Boolean(targetInput && targetInput.required));
    renderAll();
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    document.body.classList.add('overflow-hidden', 'ep-overlay-blur');
  }

  function closeModal() {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    document.body.classList.remove('overflow-hidden', 'ep-overlay-blur');
    if (noteEditor) noteEditor.classList.add('hidden');
    targetInput = null;
  }

  function dispatchValue(val) {
    if (!targetInput) return;
    targetInput.value = val;
    targetInput.dispatchEvent(new Event('input', { bubbles: true }));
    targetInput.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function applySelection() {
    if (selectedKey && isKeyAllowed(selectedKey)) dispatchValue(selectedKey);
    closeModal();
  }

  if (prevBtn) prevBtn.addEventListener('click', () => stepMonth(-1));
  if (nextBtn) nextBtn.addEventListener('click', () => stepMonth(1));
  if (tearPullBtn) tearPullBtn.addEventListener('click', () => stepMonth(1));
  if (todayBtn) {
    todayBtn.addEventListener('click', () => {
      const t = todayKey();
      const parsed = parseKey(t);
      if (!parsed) return;
      if (isKeyAllowed(t)) selectedKey = t;
      const dir = parsed.y > viewYear || (parsed.y === viewYear && parsed.m > viewMonth) ? 1 : -1;
      if (parsed.y !== viewYear || parsed.m !== viewMonth) switchMonth(parsed.y, parsed.m, dir);
      else renderAll();
    });
  }
  if (pinBtn) pinBtn.addEventListener('click', openNoteEditor);
  if (noteColorsEl) {
    noteColorsEl.querySelectorAll('[data-note-color]').forEach((btn) => {
      btn.addEventListener('click', () => {
        activeNoteColor = btn.getAttribute('data-note-color') || 'yellow';
        updateSwatchState();
      });
    });
  }
  if (noteSaveBtn) {
    noteSaveBtn.addEventListener('click', () => {
      const key = selectedKey || todayKey();
      const notes = loadNotes();
      const text = String(noteInput ? noteInput.value : '').trim();
      if (text) notes[key] = { text, color: activeNoteColor };
      else delete notes[key];
      saveNotes(notes);
      if (noteEditor) noteEditor.classList.add('hidden');
      renderAll();
    });
  }
  if (noteDeleteBtn) {
    noteDeleteBtn.addEventListener('click', () => {
      const notes = loadNotes();
      delete notes[selectedKey || todayKey()];
      saveNotes(notes);
      if (noteEditor) noteEditor.classList.add('hidden');
      renderAll();
    });
  }
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      if (targetInput && !targetInput.required) dispatchValue('');
      closeModal();
    });
  }
  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);
  if (closeXBtn) closeXBtn.addEventListener('click', closeModal);
  if (applyBtn) applyBtn.addEventListener('click', applySelection);

  modal.addEventListener('pointerdown', (e) => { pointerDownOnBackdrop = e.target === modal; });
  modal.addEventListener('click', (e) => {
    if (e.target === modal && pointerDownOnBackdrop) closeModal();
    pointerDownOnBackdrop = false;
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modal.classList.contains('hidden')) closeModal();
  });
  document.addEventListener('click', (e) => {
    const input = e.target && e.target.closest ? e.target.closest('input[type="date"]') : null;
    if (!input || input.disabled || input.readOnly || input.getAttribute('data-native-date') === 'true') return;
    e.preventDefault();
    openModal(input);
  });

  window.openTearOffCalendarModal = openModal;
})();
