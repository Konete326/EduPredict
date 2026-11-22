(function () {
  const ORBIT_KEY = 'ep_student_orbit_goals';
  const ORBIT_DEFS = [
    { key: 'attendance', label: 'Attendance Target %', unit: '%', def: 85, step: 5, min: 50, max: 100, r: 72 },
    { key: 'study_hours', label: 'Weekly Study Hours', unit: 'h', def: 8, step: 1, min: 2, max: 24, r: 54 },
    { key: 'coursework', label: 'Coursework Score %', unit: '%', def: 80, step: 5, min: 40, max: 100, r: 36 }
  ];
  let globalsBound = false, resizeTimer = null, contourRenderer = null;

  const byId = (id) => document.getElementById(id);
  const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));

  function readCssVar(name, fallback) {
    if (typeof getComputedStyle !== 'function' || !document.documentElement) return fallback;
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
  }

  function getTokens() {
    const dark = Boolean(document.documentElement && document.documentElement.classList && document.documentElement.classList.contains('dark'));
    return { bgSurface: readCssVar('--bg-surface', dark ? '#111827' : '#ffffff'), textPrimary: readCssVar('--text-primary', dark ? '#f8fafc' : '#0f172a'), textMuted: readCssVar('--text-muted', dark ? '#94a3b8' : '#64748b'), borderSubtle: readCssVar('--border-subtle', dark ? 'rgba(255,255,255,0.08)' : '#e2e8f0'), accentPrimary: readCssVar('--accent-primary', dark ? '#3b82f6' : '#2563eb'), statusSuccess: readCssVar('--status-success', dark ? '#22c55e' : '#16a34a'), statusWarning: readCssVar('--status-warning', dark ? '#f59e0b' : '#d97706') };
  }

  function parseContourSeries() {
    const fallbackLabels = ['Wk 1', 'Wk 2', 'Wk 3', 'Wk 4', 'Wk 5', 'Wk 6', 'Wk 7', 'Wk 8'];
    let raw = {};
    const node = byId('accuracy-contour-data');
    if (node) { try { raw = JSON.parse(node.textContent || '{}') || {}; } catch (e) { raw = {}; } }
    const ps = raw.portal_settings || {}, minAtt = Number(ps.min_attendance_pct || 75), highCut = Number(ps.high_risk_threshold || 70), medCut = Number(ps.medium_risk_threshold || 35);
    if (Array.isArray(raw.weeks) && raw.weeks.length >= 2) return { labels: raw.weeks.map((w, i) => String(w.label || ('Wk ' + (i + 1)))), values: raw.weeks.map((w) => clamp(Number(w.value ?? w.score ?? 75), 0, 100)), minAtt, highCut, medCut };
    if (Array.isArray(raw.labels) && Array.isArray(raw.values) && raw.values.length >= 2) return { labels: raw.labels.map(String), values: raw.values.map((v) => clamp(Number(v), 0, 100)), minAtt, highCut, medCut };
    const kpis = raw.kpis || {}, stab = Number(kpis.stable_share), agree = Number(kpis.risk_agreement), cov = Number(kpis.coverage_pct);
    const anchor = Number.isFinite(stab) && stab > 0 ? stab : (Number.isFinite(agree) && agree > 0 ? agree : (Number.isFinite(cov) && cov > 0 ? clamp(cov * 0.88, 68, 95) : 82));
    return { labels: fallbackLabels, values: [-9, -6, -7, -3, -1, 2, 5, 4].map((d) => Math.round(clamp(anchor + d, 42, 98) * 10) / 10), minAtt, highCut, medCut };
  }

  function catmullRomTrace(ctx, pts, minY, maxY) {
    if (!pts.length) return;
    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    for (let i = 0; i < pts.length - 1; i += 1) {
      const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
      for (let s = 1; s <= 14; s += 1) {
        const t = s / 14, t2 = t * t, t3 = t2 * t;
        const x = 0.5 * ((2 * p1.x) + (-p0.x + p2.x) * t + (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * t2 + (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * t3);
        const y = clamp(0.5 * ((2 * p1.y) + (-p0.y + p2.y) * t + (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * t2 + (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * t3), minY, maxY);
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();
  }

  function initAcademicContourChart() {
    const canvas = byId('academic-contour-canvas');
    if (!canvas || typeof canvas.getContext !== 'function') { contourRenderer = null; return; }
    const series = parseContourSeries(), rangeEl = byId('contour-strata-range'), strataValEl = byId('contour-strata-val');
    const tooltipEl = byId('contour-tooltip'), pinStatusEl = byId('contour-pin-status');
    let hoverIdx = null, pinnedIdx = null, strata = clamp(parseInt(rangeEl ? rangeEl.value : '7', 10) || 7, 4, 10), lastPts = [];

    const sumMean = series.values.reduce((a, b) => a + b, 0) / series.values.length;
    let peakIdx = 0;
    series.values.forEach((v, idx) => { if (v > series.values[peakIdx]) peakIdx = idx; });
    if (byId('contour-stat-mean')) byId('contour-stat-mean').textContent = sumMean.toFixed(1) + '%';
    if (byId('contour-stat-peak')) byId('contour-stat-peak').textContent = series.labels[peakIdx] + ' (' + series.values[peakIdx].toFixed(1) + '%)';
    if (byId('contour-stat-cutoffs')) byId('contour-stat-cutoffs').textContent = 'Att ' + series.minAtt + '% / High ' + series.highCut + '%';
    if (strataValEl) strataValEl.textContent = String(strata);

    function updateTooltip() {
      if (!tooltipEl) return;
      if (hoverIdx === null || !lastPts[hoverIdx]) { tooltipEl.classList.add('hidden'); return; }
      const pt = lastPts[hoverIdx], val = series.values[hoverIdx], deltaMean = val - sumMean;
      tooltipEl.textContent = '';
      const hdr = document.createElement('div');
      hdr.className = 'font-semibold text-[var(--text-primary)]';
      hdr.textContent = series.labels[hoverIdx] + ' · ' + val.toFixed(1) + '%';
      const sub = document.createElement('div');
      sub.className = 'text-[10px] font-mono text-[var(--text-muted)]';
      sub.textContent = 'Mean: ' + (deltaMean >= 0 ? '+' : '') + deltaMean.toFixed(1) + '%' + (pinnedIdx !== null && pinnedIdx !== hoverIdx ? ' | vs ' + series.labels[pinnedIdx] + ': ' + ((val - series.values[pinnedIdx]) >= 0 ? '+' : '') + (val - series.values[pinnedIdx]).toFixed(1) + '%' : '');
      tooltipEl.append(hdr, sub);
      tooltipEl.classList.remove('hidden');
      const boxW = canvas.parentElement ? canvas.parentElement.clientWidth : 360;
      tooltipEl.style.left = Math.round(clamp(pt.x + (pt.x > boxW * 0.65 ? -175 : 10), 6, Math.max(8, boxW - 185))) + 'px';
      tooltipEl.style.top = Math.round(clamp(pt.y - 42, 6, 130)) + 'px';
    }

    function draw() {
      const wrap = canvas.parentElement, w = Math.max(240, (wrap && wrap.clientWidth) || canvas.clientWidth || 560), h = Math.max(150, (wrap && wrap.clientHeight) || canvas.clientHeight || 192);
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.shadowBlur = 0; ctx.shadowColor = 'transparent';
      ctx.clearRect(0, 0, w, h);

      const t = getTokens(), padL = 38, padR = 14, padT = 16, padB = 26, plotW = Math.max(80, w - padL - padR), plotH = Math.max(60, h - padT - padB);
      const yMin = 30, yMax = 100, toY = (v) => padT + ((yMax - clamp(v, yMin, yMax)) / (yMax - yMin)) * plotH;
      ctx.font = "500 10px 'JetBrains Mono', ui-monospace, monospace";
      [40, 60, 80, 100].forEach((tick) => {
        const y = toY(tick);
        ctx.save(); ctx.strokeStyle = t.borderSubtle; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(w - padR, y); ctx.stroke();
        ctx.fillStyle = t.textMuted; ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
        ctx.fillText(tick + '%', padL - 6, y); ctx.restore();
      });

      const pts = series.values.map((val, i) => ({ x: padL + (i / Math.max(1, series.values.length - 1)) * plotW, y: toY(val) }));
      lastPts = pts;
      pts.forEach((p, i) => {
        const active = i === hoverIdx || i === pinnedIdx;
        ctx.save(); ctx.setLineDash([4, 4]); ctx.strokeStyle = active ? t.accentPrimary : t.borderSubtle;
        ctx.globalAlpha = active ? 0.8 : 0.65; ctx.lineWidth = active ? 1.4 : 1;
        ctx.beginPath(); ctx.moveTo(p.x, padT); ctx.lineTo(p.x, padT + plotH); ctx.stroke();
        ctx.setLineDash([]); ctx.globalAlpha = 1; ctx.fillStyle = active ? t.textPrimary : t.textMuted;
        ctx.textAlign = 'center'; ctx.textBaseline = 'top'; ctx.fillText(series.labels[i], p.x, padT + plotH + 7); ctx.restore();
      });

      const cutY = toY(series.minAtt);
      ctx.save(); ctx.setLineDash([5, 4]); ctx.strokeStyle = t.statusWarning; ctx.globalAlpha = 0.7; ctx.lineWidth = 1.25;
      ctx.beginPath(); ctx.moveTo(padL, cutY); ctx.lineTo(w - padR, cutY); ctx.stroke(); ctx.restore();

      for (let layer = 1; layer <= strata; layer += 1) {
        const ratio = layer / strata, layerPts = series.values.map((val, i) => ({ x: pts[i].x, y: toY(yMin + (val - yMin) * ratio) }));
        ctx.save(); ctx.shadowBlur = 0; ctx.strokeStyle = layer === strata ? t.accentPrimary : (ratio >= 0.7 ? t.statusSuccess : t.accentPrimary);
        ctx.globalAlpha = layer === strata ? 1 : (0.14 + ratio * 0.42); ctx.lineWidth = layer === strata ? 2.25 : 1.15;
        catmullRomTrace(ctx, layerPts, padT, padT + plotH); ctx.restore();
      }
      if (hoverIdx !== null && pts[hoverIdx]) {
        ctx.save(); ctx.setLineDash([3, 3]); ctx.strokeStyle = t.accentPrimary; ctx.globalAlpha = 0.45; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(padL, pts[hoverIdx].y); ctx.lineTo(w - padR, pts[hoverIdx].y); ctx.stroke(); ctx.restore();
      }
      pts.forEach((p, i) => {
        ctx.save(); ctx.shadowBlur = 0; ctx.fillStyle = i === pinnedIdx ? t.statusWarning : t.accentPrimary;
        ctx.strokeStyle = t.bgSurface; ctx.lineWidth = 1.8;
        ctx.beginPath(); ctx.arc(p.x, p.y, (i === hoverIdx || i === pinnedIdx) ? 5 : 3.2, 0, Math.PI * 2); ctx.fill(); ctx.stroke(); ctx.restore();
      });
    }

    contourRenderer = draw;
    draw();
    if (canvas.dataset.contourBound !== '1') {
      canvas.dataset.contourBound = '1';
      const nearestIndex = (clientX) => {
        const rx = clientX - ((canvas.getBoundingClientRect && canvas.getBoundingClientRect().left) || 0);
        let best = 0, dist = Infinity;
        lastPts.forEach((p, i) => { const d = Math.abs(p.x - rx); if (d < dist) { dist = d; best = i; } });
        return best;
      };
      canvas.addEventListener('mousemove', (e) => { const idx = nearestIndex(e.clientX); if (idx !== hoverIdx) { hoverIdx = idx; draw(); } updateTooltip(); });
      canvas.addEventListener('mouseleave', () => { hoverIdx = null; draw(); updateTooltip(); });
      canvas.addEventListener('click', (e) => {
        const idx = nearestIndex(e.clientX);
        pinnedIdx = pinnedIdx === idx ? null : idx;
        if (pinStatusEl) pinStatusEl.textContent = pinnedIdx === null ? 'Click any week node to pin & compare' : ('Pinned: ' + series.labels[pinnedIdx] + ' (' + series.values[pinnedIdx].toFixed(1) + '%)');
        draw(); updateTooltip();
      });
    }
    if (rangeEl && rangeEl.dataset.contourBound !== '1') {
      rangeEl.dataset.contourBound = '1';
      rangeEl.addEventListener('input', () => { strata = clamp(parseInt(rangeEl.value, 10) || 7, 4, 10); if (strataValEl) strataValEl.textContent = String(strata); draw(); });
    }
  }

  function initOrbitGoalsTracker() {
    const card = byId('orbit-goals-card');
    if (!card) return;
    const actuals = { attendance: clamp(parseFloat(card.getAttribute('data-att')) || 0, 0, 100), study_hours: Math.max(0, parseFloat(card.getAttribute('data-hours')) || 0), coursework: clamp(parseFloat(card.getAttribute('data-marks')) || 0, 0, 100) };
    const defaultTargets = { attendance: 85, study_hours: 8, coursework: 80 };
    let state = { selected: 'attendance', targets: Object.assign({}, defaultTargets) };
    try {
      const saved = JSON.parse(localStorage.getItem(ORBIT_KEY) || 'null');
      if (saved && typeof saved === 'object') {
        if (saved.selected && defaultTargets[saved.selected] !== undefined) state.selected = saved.selected;
        if (saved.targets) ORBIT_DEFS.forEach((d) => { const v = Number(saved.targets[d.key]); if (Number.isFinite(v)) state.targets[d.key] = clamp(v, d.min, d.max); });
      }
    } catch (e) {}
    const persist = () => { try { localStorage.setItem(ORBIT_KEY, JSON.stringify(state)); } catch (e) {} };
    const render = () => {
      let totalPct = 0;
      ORBIT_DEFS.forEach((d) => {
        const actual = actuals[d.key], target = state.targets[d.key], pct = Math.round(clamp((actual / Math.max(target, 1)) * 100, 0, 100)), selected = state.selected === d.key;
        totalPct += pct;
        const ring = card.querySelector('[data-orbit-ring="' + d.key + '"]');
        if (ring) { const circ = 2 * Math.PI * d.r; ring.style.strokeDasharray = circ.toFixed(2); ring.style.strokeDashoffset = (circ * (1 - pct / 100)).toFixed(2); ring.setAttribute('stroke-width', selected ? '11' : '8'); ring.style.opacity = selected ? '1' : '0.72'; }
        const leg = card.querySelector('[data-orbit-goal="' + d.key + '"]');
        if (leg) { leg.setAttribute('aria-pressed', selected ? 'true' : 'false'); leg.classList.toggle('border-[var(--accent-primary)]', selected); leg.classList.toggle('bg-[var(--accent-soft)]', selected); }
        const valEl = card.querySelector('[data-orbit-val="' + d.key + '"]'), pctEl = card.querySelector('[data-orbit-pct="' + d.key + '"]');
        if (valEl) valEl.textContent = (d.key === 'study_hours' ? actual.toFixed(1) : Math.round(actual)) + d.unit + ' / ' + target + d.unit;
        if (pctEl) pctEl.textContent = pct + '%';
      });
      if (byId('orbit-center-pct')) byId('orbit-center-pct').textContent = Math.round(totalPct / ORBIT_DEFS.length) + '%';
      const activeDef = ORBIT_DEFS.find((d) => d.key === state.selected) || ORBIT_DEFS[0];
      if (byId('orbit-active-label')) byId('orbit-active-label').textContent = activeDef.label;
      if (byId('orbit-active-target')) byId('orbit-active-target').textContent = state.targets[activeDef.key] + activeDef.unit;
      const spark = byId('orbit-sparkline');
      if (spark) {
        spark.textContent = '';
        const days = ['M', 'T', 'W', 'T', 'F', 'S', 'S'], weights = [0.84, 0.92, 0.88, 1.0, 0.95, 0.78, 0.9], selPct = Math.round(clamp((actuals[activeDef.key] / Math.max(state.targets[activeDef.key], 1)) * 100, 0, 100));
        days.forEach((day, idx) => {
          const barPct = clamp(Math.round(selPct * weights[idx]), 12, 100), col = document.createElement('div'), track = document.createElement('div'), fill = document.createElement('div'), lbl = document.createElement('span');
          col.className = 'flex flex-1 flex-col items-center gap-1'; track.className = 'flex h-10 w-full items-end rounded bg-[var(--bg-elevated)] p-0.5';
          fill.className = 'w-full rounded-sm transition-all duration-200 ' + (barPct >= 80 ? 'bg-[var(--status-success)]' : (barPct >= 55 ? 'bg-[var(--accent-primary)]' : 'bg-[var(--status-warning)]'));
          fill.style.height = barPct + '%'; lbl.className = 'text-[9px] font-mono text-[var(--text-muted)]'; lbl.textContent = day;
          track.appendChild(fill); col.append(track, lbl); spark.appendChild(col);
        });
      }
    };
    const stepTarget = (dir) => { const def = ORBIT_DEFS.find((d) => d.key === state.selected) || ORBIT_DEFS[0]; state.targets[def.key] = clamp(state.targets[def.key] + def.step * dir, def.min, def.max); persist(); render(); };
    if (card.dataset.orbitBound !== '1') {
      card.dataset.orbitBound = '1';
      card.querySelectorAll('[data-orbit-goal], [data-orbit-ring]').forEach((el) => el.addEventListener('click', () => { state.selected = el.getAttribute('data-orbit-goal') || el.getAttribute('data-orbit-ring') || 'attendance'; persist(); render(); }));
      card.querySelectorAll('[data-orbit-step]').forEach((btn) => btn.addEventListener('click', () => stepTarget(parseInt(btn.getAttribute('data-orbit-step') || '0', 10) >= 0 ? 1 : -1)));
      card.addEventListener('keydown', (e) => { if (!e.isComposing && e.keyCode !== 229) { if (e.key === 'ArrowRight' || e.key === 'ArrowUp') { e.preventDefault(); stepTarget(1); } else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') { e.preventDefault(); stepTarget(-1); } } });
      if (byId('orbit-reset-btn')) byId('orbit-reset-btn').addEventListener('click', () => { state.targets = Object.assign({}, defaultTargets); persist(); render(); });
    }
    render();
  }

  function initAcademicMarquee() {
    const reduced = typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    document.querySelectorAll('[data-ep-marquee]').forEach((wrap) => {
      const track = wrap.querySelector('[data-marquee-track]');
      if (!track || reduced || track.dataset.marqueeCloned === '1' || !track.children.length) return;
      Array.from(track.children).map((node) => { const c = node.cloneNode(true); c.setAttribute('aria-hidden', 'true'); return c; }).forEach((c) => track.appendChild(c));
      track.dataset.marqueeCloned = '1';
    });
  }

  function initAcademicWidgets() {
    initAcademicContourChart(); initOrbitGoalsTracker(); initAcademicMarquee();
    if (!globalsBound) {
      globalsBound = true;
      window.addEventListener('themeChanged', () => { if (typeof contourRenderer === 'function') contourRenderer(); });
      window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { if (typeof contourRenderer === 'function') contourRenderer(); }, 120); });
    }
  }

  if (typeof window.reinitEduPredictUI === 'function' && !window.reinitEduPredictUI._academicWrapped) {
    const orig = window.reinitEduPredictUI, wrapped = function () { orig(); initAcademicWidgets(); };
    wrapped._academicWrapped = true; window.reinitEduPredictUI = wrapped;
  }

  window.initAcademicWidgets = initAcademicWidgets;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initAcademicWidgets);
  else initAcademicWidgets();
})();
