(function () {
  const prefersReducedMotion = () => typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

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
    const duration = 500;
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

  function resolveKpiFilterToken(rawFilter) {
    const val = String(rawFilter || '').trim().toLowerCase();
    if (!val) return '';
    if (val.includes('high')) return 'high';
    if (val.includes('medium')) return 'medium';
    if (val.includes('low')) return 'low';
    if (val.includes('pending')) return 'pending';
    if (val.includes('open')) return 'open';
    if (val.includes('resolved')) return 'resolved';
    if (val.includes('drop') || val.includes('anomal')) return 'drop';
    if (val.includes('teacher')) return 'teacher';
    if (val.includes('student')) return 'student';
    if (val.includes('help') || val.includes('attention')) return 'help';
    return '';
  }

  function handleKpiCardActivate(card) {
    const searchInput = document.querySelector('input[data-table-search]');
    const hasTable = Boolean(document.querySelector('[data-paginated-container], main table'));
    if (!searchInput || !hasTable) return;
    const token = resolveKpiFilterToken(card.getAttribute('data-kpi-filter') || card.getAttribute('data-kpi-label'));
    const wasActive = card.getAttribute('data-kpi-active') === 'true';
    document.querySelectorAll('[data-dot-kpi]').forEach((node) => node.removeAttribute('data-kpi-active'));
    if (wasActive || !token) {
      searchInput.value = '';
    } else {
      card.setAttribute('data-kpi-active', 'true');
      searchInput.value = token;
    }
    searchInput.dispatchEvent(new Event('input', { bubbles: true }));
  }

  function initDotKpiCards() {
    const reduced = prefersReducedMotion();
    document.querySelectorAll('[data-dot-kpi]').forEach((card) => {
      if (card.dataset.dotReady === '1') return;
      card.dataset.dotReady = '1';
      const rawValue = card.getAttribute('data-kpi-value') || '';
      animateCounter(card.querySelector('[data-kpi-counter]'), rawValue, reduced);
      card.addEventListener('click', () => handleKpiCardActivate(card));
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleKpiCardActivate(card);
        }
      });
    });
  }

  window.initDotKpiCards = initDotKpiCards;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initDotKpiCards);
  else initDotKpiCards();
})();
