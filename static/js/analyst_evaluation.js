(function () {
  function el(tag, cls, text, attrs) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        node.setAttribute(k, attrs[k]);
      });
    }
    return node;
  }

  function fmtMetric(val) {
    if (val === null || val === undefined || Number.isNaN(Number(val))) return 'N/A';
    return Number(val).toFixed(4);
  }

  function statusDotClass(status) {
    if (status === 'EVALUATED' || status === 'COMPLETED') return 'bg-[var(--status-success)]';
    if (status === 'INSUFFICIENT_DATA' || status === 'UNAVAILABLE' || status === 'PARTIAL' || status === 'NO_GENUINE_LABELS') {
      return 'bg-[var(--status-warning)]';
    }
    return 'bg-[var(--accent-primary)]';
  }

  function buildMetricTile(label, valueText) {
    const box = el('div', 'rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2');
    box.appendChild(el('p', 'text-[11px] text-[var(--text-muted)]', label));
    box.appendChild(el('p', 'mt-0.5 font-mono text-sm font-semibold text-[var(--text-primary)]', valueText));
    return box;
  }

  function buildConfusionMatrix(model) {
    const cm = model.metrics && model.metrics.confusion_matrix;
    if (!cm) return null;
    const region = el(
      'div',
      'overflow-x-auto rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]',
      undefined,
      { tabindex: '0', role: 'region', 'aria-label': (model.model_name || 'Model') + ' confusion matrix' }
    );
    const table = el('table', 'w-full border-collapse text-center text-xs tabular-nums');
    table.appendChild(el('caption', 'border-b border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-1.5 text-left text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]', 'Confusion Matrix'));
    const thead = el('thead');
    const hRow = el('tr', 'border-b border-[var(--border-subtle)] text-[11px] text-[var(--text-muted)]');
    hRow.appendChild(el('th', 'px-2.5 py-1.5 text-left font-medium', 'Actual \\ Pred', { scope: 'col' }));
    hRow.appendChild(el('th', 'px-2.5 py-1.5 font-medium', 'Pred 0', { scope: 'col' }));
    hRow.appendChild(el('th', 'px-2.5 py-1.5 font-medium', 'Pred 1', { scope: 'col' }));
    thead.appendChild(hRow);
    table.appendChild(thead);

    const tbody = el('tbody', 'divide-y divide-[var(--border-subtle)]');
    function makeCell(val, tagLabel, colorCls) {
      const td = el('td', 'px-2.5 py-1.5 font-mono font-semibold ' + colorCls, String(val) + ' ');
      td.appendChild(el('span', 'text-[10px] font-normal text-[var(--text-muted)]', tagLabel));
      return td;
    }
    const r0 = el('tr');
    r0.appendChild(el('th', 'px-2.5 py-1.5 text-left font-medium text-[var(--text-secondary)]', 'Actual 0', { scope: 'row' }));
    r0.appendChild(makeCell(cm.tn, 'TN', 'text-[var(--status-success)]'));
    r0.appendChild(makeCell(cm.fp, 'FP', 'text-[var(--status-warning)]'));
    tbody.appendChild(r0);

    const r1 = el('tr');
    r1.appendChild(el('th', 'px-2.5 py-1.5 text-left font-medium text-[var(--text-secondary)]', 'Actual 1', { scope: 'row' }));
    r1.appendChild(makeCell(cm.fn, 'FN', 'text-[var(--status-danger)]'));
    r1.appendChild(makeCell(cm.tp, 'TP', 'text-[var(--status-success)]'));
    tbody.appendChild(r1);

    table.appendChild(tbody);
    region.appendChild(table);
    return region;
  }

  function buildModelCard(model) {
    const article = el('article', 'min-w-0 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-canvas)] p-4 flex flex-col justify-between gap-3');
    const top = el('div', 'space-y-2.5');

    const headRow = el('div', 'flex items-start justify-between gap-2');
    headRow.appendChild(el('h4', 'text-sm font-semibold text-[var(--text-primary)] leading-snug', model.model_name || 'Model'));
    const badge = el('span', 'inline-flex shrink-0 items-center gap-1.5 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2 py-0.5 text-[11px] font-medium text-[var(--text-secondary)]');
    badge.appendChild(el('span', 'h-1.5 w-1.5 rounded-full ' + statusDotClass(model.status), undefined, { 'aria-hidden': 'true' }));
    badge.appendChild(el('span', '', model.status || 'UNKNOWN'));
    headRow.appendChild(badge);
    top.appendChild(headRow);

    const dl = el('dl', 'grid grid-cols-3 gap-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-2.5 text-xs');
    function addMeta(title, value, cls) {
      const wrap = el('div', 'min-w-0');
      wrap.appendChild(el('dt', 'text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]', title));
      wrap.appendChild(el('dd', cls, value));
      dl.appendChild(wrap);
    }
    addMeta('Genuine Labels', model.uses_genuine_labels ? 'Yes' : 'No', 'mt-0.5 truncate font-medium ' + (model.uses_genuine_labels ? 'text-[var(--status-success)]' : 'text-[var(--status-warning)]'));
    addMeta('Train Split', String(model.train_samples || 0), 'mt-0.5 tabular-nums font-mono font-semibold text-[var(--text-primary)]');
    addMeta('Test Split', String(model.test_samples || 0), 'mt-0.5 tabular-nums font-mono font-semibold text-[var(--text-primary)]');
    top.appendChild(dl);

    if (model.metrics) {
      const grid = el('div', 'grid grid-cols-2 gap-2 tabular-nums');
      if (model.task_type === 'classification') {
        grid.appendChild(buildMetricTile('Accuracy', fmtMetric(model.metrics.accuracy)));
        grid.appendChild(buildMetricTile('Precision', fmtMetric(model.metrics.precision)));
        grid.appendChild(buildMetricTile('Recall', fmtMetric(model.metrics.recall)));
        grid.appendChild(buildMetricTile('F1-Score', fmtMetric(model.metrics.f1_score)));
        top.appendChild(grid);
        const cmNode = buildConfusionMatrix(model);
        if (cmNode) top.appendChild(cmNode);
      } else if (model.task_type === 'regression') {
        grid.appendChild(buildMetricTile('MAE', fmtMetric(model.metrics.mae)));
        grid.appendChild(buildMetricTile('MSE', fmtMetric(model.metrics.mse)));
        grid.appendChild(buildMetricTile('RMSE', fmtMetric(model.metrics.rmse)));
        grid.appendChild(buildMetricTile('R\u00B2 Score', fmtMetric(model.metrics.r2_score)));
        top.appendChild(grid);
      }
    } else {
      const unavail = el('div', 'rounded-lg border border-dashed border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3 space-y-1');
      unavail.appendChild(el('p', 'text-xs font-semibold text-[var(--text-primary)]', model.status === 'UNSUPERVISED' ? 'Unsupervised Mode' : 'Metrics Unavailable'));
      unavail.appendChild(el('p', 'text-xs leading-relaxed text-[var(--text-muted)]', 'Real-world scores are hidden because verified ground-truth labels are not available for train/test validation.'));
      top.appendChild(unavail);
    }
    article.appendChild(top);

    const warnings = model.warnings || [];
    const limitations = model.limitations || [];
    if (warnings.length || limitations.length) {
      const footer = el('footer', 'border-t border-[var(--border-subtle)] pt-2.5 space-y-1.5 text-[11px] leading-relaxed text-[var(--text-secondary)]');
      footer.appendChild(el('p', 'text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]', 'Warnings & Limitations'));
      const list = el('ul', 'space-y-1');
      warnings.forEach(function (w) {
        const li = el('li', 'flex items-start gap-1.5');
        li.appendChild(el('i', 'fa-solid fa-circle-info mt-0.5 shrink-0 text-[var(--accent-primary)]', undefined, { 'aria-hidden': 'true' }));
        li.appendChild(el('span', '', w));
        list.appendChild(li);
      });
      limitations.forEach(function (l) {
        const li = el('li', 'flex items-start gap-1.5');
        li.appendChild(el('i', 'fa-solid fa-triangle-exclamation mt-0.5 shrink-0 text-[var(--status-warning)]', undefined, { 'aria-hidden': 'true' }));
        li.appendChild(el('span', '', l));
        list.appendChild(li);
      });
      footer.appendChild(list);
      article.appendChild(footer);
    }
    return article;
  }

  function renderEvaluationPayload(payload) {
    const suiteBadge = document.getElementById('eval-suite-status');
    if (suiteBadge) {
      suiteBadge.innerHTML = '';
      suiteBadge.appendChild(el('span', 'h-1.5 w-1.5 rounded-full ' + statusDotClass(payload.status), undefined, { 'aria-hidden': 'true' }));
      suiteBadge.appendChild(el('span', '', payload.status || 'UNAVAILABLE'));
    }

    const pills = document.getElementById('eval-dataset-pills');
    const summary = payload.dataset_summary;
    if (pills && summary) {
      pills.innerHTML = '';
      pills.appendChild(el('span', 'rounded-md border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 tabular-nums', 'Records: ' + summary.total_records));
      pills.appendChild(el('span', 'rounded-md border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 tabular-nums', 'Dropout Labels: ' + summary.genuine_dropout_labels));
      pills.appendChild(el('span', 'rounded-md border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 tabular-nums', 'GPA Labels: ' + summary.genuine_gpa_labels));
    }

    const warningsWrap = document.getElementById('eval-suite-warnings');
    if (warningsWrap) {
      warningsWrap.innerHTML = '';
      const suiteWarnings = payload.warnings || [];
      warningsWrap.classList.toggle('hidden', suiteWarnings.length === 0);
      suiteWarnings.forEach(function (w) {
        const row = el('div', 'rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3.5 py-2 text-xs text-[var(--text-secondary)] flex items-start gap-2');
        row.appendChild(el('i', 'fa-solid fa-triangle-exclamation mt-0.5 shrink-0 text-[var(--status-warning)]', undefined, { 'aria-hidden': 'true' }));
        row.appendChild(el('span', '', w));
        warningsWrap.appendChild(row);
      });
    }

    const cardsWrap = document.getElementById('ml-evaluation-cards');
    if (cardsWrap) {
      cardsWrap.innerHTML = '';
      const modelsMap = payload.models || {};
      ['dropout_classifier', 'gpa_regressor', 'anomaly_detector'].forEach(function (key) {
        if (modelsMap[key]) cardsWrap.appendChild(buildModelCard(modelsMap[key]));
      });
    }
  }

  function initAnalystEvaluation() {
    const btn = document.getElementById('refresh-evaluation-btn');
    if (!btn || btn.dataset.evalBound === '1') return;
    btn.dataset.evalBound = '1';

    btn.addEventListener('click', function () {
      const baseUrl = btn.getAttribute('data-eval-url') || '/analyst-panel/evaluation/';
      const sep = baseUrl.indexOf('?') === -1 ? '?' : '&';
      const url = baseUrl + sep + 'refresh=1';
      const loadingBanner = document.getElementById('eval-loading-banner');
      const errorBanner = document.getElementById('eval-error-banner');
      const errorText = document.getElementById('eval-error-text');
      const liveStatus = document.getElementById('eval-live-status');
      const icon = document.getElementById('refresh-evaluation-icon');
      const label = document.getElementById('refresh-evaluation-label');

      btn.disabled = true;
      if (icon) icon.classList.add('fa-spin');
      if (label) label.textContent = 'Checking...';
      if (loadingBanner) loadingBanner.classList.remove('hidden');
      if (errorBanner) errorBanner.classList.add('hidden');

      fetch(url, { method: 'GET', credentials: 'same-origin', headers: { Accept: 'application/json' } })
        .then(function (resp) {
          const contentType = resp.headers.get('content-type') || '';
          if (!contentType.includes('application/json')) {
            throw new Error('Evaluation request was redirected or denied.');
          }
          return resp.json().then(function (data) {
            if (!resp.ok) throw new Error(data.error || ('Request failed (' + resp.status + ')'));
            return data;
          });
        })
        .then(function (payload) {
          renderEvaluationPayload(payload);
          if (liveStatus) liveStatus.textContent = 'Model evaluation refreshed. Status: ' + (payload.status || 'DONE');
        })
        .catch(function (err) {
          if (errorText) errorText.textContent = err && err.message ? err.message : 'Could not refresh evaluation.';
          if (errorBanner) errorBanner.classList.remove('hidden');
          if (liveStatus) liveStatus.textContent = 'Model evaluation refresh failed.';
        })
        .finally(function () {
          btn.disabled = false;
          if (icon) icon.classList.remove('fa-spin');
          if (label) label.textContent = 'Re-check Evaluation';
          if (loadingBanner) loadingBanner.classList.add('hidden');
        });
    });
  }

  window.initAnalystEvaluation = initAnalystEvaluation;
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAnalystEvaluation, { once: true });
  } else {
    initAnalystEvaluation();
  }
})();
