(function () {
  const prefersReducedMotion = () => typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function hashString(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i += 1) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }

  function parseSeries(rawSeries, seedText) {
    if (rawSeries) {
      const nums = String(rawSeries).split(/[\s,|]+/).map((s) => parseFloat(s)).filter((n) => Number.isFinite(n));
      if (nums.length) {
        const min = Math.min(...nums), max = Math.max(...nums), span = max - min;
        return Array.from({ length: 14 }, (_, idx) => {
          const val = nums[idx % nums.length];
          return span === 0 ? Math.min(7, Math.max(2, Math.round(val) || 4)) : Math.min(7, Math.max(2, Math.round(2 + ((val - min) / span) * 5)));
        });
      }
    }
    let state = hashString(seedText || 'ep-dot-kpi') || 1;
    return Array.from({ length: 14 }, (_, idx) => {
      state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
      const base = (state % 5) + 2;
      return idx >= 7 ? Math.min(7, base + 1) : base;
    });
  }

  function animateCounter(counterEl, rawValue, reduced) {
    if (!counterEl) return;
    const raw = String(rawValue == null ? '' : rawValue).trim();
    if (reduced || !/^\d+(\.\d+)?%?$/.test(raw)) {
      counterEl.textContent = raw;
      return;
    }
    const hasPct = raw.endsWith('%');
    const numStr = hasPct ? raw.slice(0, -1) : raw;
    const target = parseFloat(numStr);
    const decimals = numStr.indexOf('.') !== -1 ? numStr.split('.')[1].length : 0;
    const duration = 650;
    const start = performance.now();
    function step(now) {
      const t = Math.min(1, (now - start) / duration);
      const current = target * (1 - Math.pow(1 - t, 4));
      counterEl.textContent = (decimals ? current.toFixed(decimals) : Math.round(current)) + (hasPct ? '%' : '');
      if (t < 1) window.requestAnimationFrame(step);
      else counterEl.textContent = raw;
    }
    window.requestAnimationFrame(step);
  }

  function renderMatrix(matrixEl, tooltipEl, series, reduced) {
    while (matrixEl.firstChild) matrixEl.removeChild(matrixEl.firstChild);
    series.forEach((count, colIdx) => {
      const col = document.createElement('div');
      col.className = 'ep-dot-col';
      const isActive = colIdx >= 7;
      for (let rowIdx = 0; rowIdx < count; rowIdx += 1) {
        const dot = document.createElement('span');
        dot.className = 'ep-dot ' + (isActive ? 'ep-dot-active' : 'ep-dot-muted');
        if (!reduced) dot.style.animationDelay = ((colIdx * 24) + (rowIdx * 18)) + 'ms';
        col.appendChild(dot);
      }
      if (tooltipEl) {
        col.addEventListener('mouseenter', function () {
          tooltipEl.textContent = 'Pt ' + (colIdx + 1) + ': ' + count + '/7';
          const center = col.offsetLeft + (col.offsetWidth / 2);
          const maxLeft = Math.max(24, matrixEl.clientWidth - 24);
          tooltipEl.style.left = Math.max(24, Math.min(maxLeft, center)) + 'px';
          tooltipEl.classList.add('is-visible');
        });
        col.addEventListener('mouseleave', function () { tooltipEl.classList.remove('is-visible'); });
      }
      matrixEl.appendChild(col);
    });
  }

  function initDotKpiCards() {
    const reduced = prefersReducedMotion();
    document.querySelectorAll('[data-dot-kpi]').forEach((card) => {
      if (card.dataset.dotReady === '1') return;
      card.dataset.dotReady = '1';
      const rawValue = card.getAttribute('data-kpi-value') || '';
      const label = card.getAttribute('data-kpi-label') || '';
      const rawSeries = card.getAttribute('data-dot-series') || '';
      animateCounter(card.querySelector('[data-kpi-counter]'), rawValue, reduced);
      const matrixEl = card.querySelector('[data-dot-matrix]');
      if (matrixEl) renderMatrix(matrixEl, card.querySelector('[data-dot-tooltip]'), parseSeries(rawSeries, label + '|' + rawValue), reduced);
    });
  }

  window.initDotKpiCards = initDotKpiCards;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initDotKpiCards);
  else initDotKpiCards();
})();
