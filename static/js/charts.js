(function () {
  const managedCharts = new Map();
  let pluginRegistered = false;

  function readCssVar(name, fallback) {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
  }

  function getThemeTokens() {
    const isDark = document.documentElement.classList.contains('dark');
    return {
      isDark: isDark,
      bgCanvas: readCssVar('--bg-canvas', isDark ? '#090d16' : '#f8fafc'),
      bgSurface: readCssVar('--bg-surface', isDark ? '#111827' : '#ffffff'),
      bgElevated: readCssVar('--bg-elevated', isDark ? '#1e293b' : '#f1f5f9'),
      textPrimary: readCssVar('--text-primary', isDark ? '#f8fafc' : '#0f172a'),
      textSecondary: readCssVar('--text-secondary', isDark ? '#cbd5e1' : '#475569'),
      textMuted: readCssVar('--text-muted', isDark ? '#94a3b8' : '#64748b'),
      borderSubtle: readCssVar('--border-subtle', isDark ? 'rgba(255, 255, 255, 0.08)' : '#e2e8f0'),
      accentPrimary: readCssVar('--accent-primary', isDark ? '#3b82f6' : '#2563eb'),
      accentHover: readCssVar('--accent-hover', isDark ? '#60a5fa' : '#1d4ed8'),
      accentSoft: readCssVar('--accent-soft', isDark ? 'rgba(59, 130, 246, 0.16)' : '#eff6ff'),
      statusSuccess: readCssVar('--status-success', isDark ? '#22c55e' : '#16a34a'),
      statusWarning: readCssVar('--status-warning', isDark ? '#f59e0b' : '#d97706'),
      statusDanger: readCssVar('--status-danger', isDark ? '#ef4444' : '#dc2626')
    };
  }

  function ensureDoughnutCenterPlugin() {
    if (pluginRegistered || typeof Chart === 'undefined' || typeof Chart.register !== 'function') return;
    pluginRegistered = true;
    Chart.register({
      id: 'epDoughnutCenterLabel',
      afterDraw: function (chart) {
        if (!chart || chart.config.type !== 'doughnut') return;
        const meta = chart.getDatasetMeta(0);
        if (!meta || !meta.data || !meta.data.length) return;
        const values = (chart.data.datasets[0] && chart.data.datasets[0].data) || [];
        const total = values.reduce((acc, v) => acc + (Number(v) || 0), 0);
        const arc = meta.data[0];
        const ctx = chart.ctx;
        const tokens = getThemeTokens();
        ctx.save();
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = tokens.textPrimary;
        ctx.font = "600 18px 'JetBrains Mono', 'Inter', ui-sans-serif, sans-serif";
        ctx.fillText(String(total), arc.x, arc.y - 6);
        ctx.fillStyle = tokens.textMuted;
        ctx.font = "500 10px 'Inter', ui-sans-serif, sans-serif";
        ctx.fillText('TOTAL', arc.x, arc.y + 12);
        ctx.restore();
      }
    });
  }

  function applyGlobalChartDefaults() {
    if (typeof Chart === 'undefined') return;
    ensureDoughnutCenterPlugin();
    const tokens = getThemeTokens();
    Chart.defaults.color = tokens.textSecondary;
    Chart.defaults.borderColor = 'rgba(148, 163, 184, 0.15)';
    Chart.defaults.font.family = "'Inter', ui-sans-serif, system-ui, sans-serif";
    if (Chart.defaults.datasets) {
      Chart.defaults.datasets.bar = Object.assign(Chart.defaults.datasets.bar || {}, {
        borderRadius: 6,
        borderSkipped: false,
        maxBarThickness: 36
      });
      Chart.defaults.datasets.doughnut = Object.assign(Chart.defaults.datasets.doughnut || {}, {
        cutout: '72%',
        borderWidth: 0
      });
    }
    if (Chart.defaults.plugins && Chart.defaults.plugins.legend) {
      Chart.defaults.plugins.legend.position = 'top';
      Chart.defaults.plugins.legend.align = 'end';
      if (Chart.defaults.plugins.legend.labels) {
        Chart.defaults.plugins.legend.labels.color = tokens.textSecondary;
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.legend.labels.pointStyle = 'circle';
        Chart.defaults.plugins.legend.labels.boxWidth = 8;
        Chart.defaults.plugins.legend.labels.boxHeight = 8;
      }
    }
    if (Chart.defaults.plugins && Chart.defaults.plugins.tooltip) {
      Object.assign(Chart.defaults.plugins.tooltip, {
        backgroundColor: '#0f172a',
        titleColor: '#f8fafc',
        bodyColor: '#e2e8f0',
        borderColor: 'rgba(255, 255, 255, 0.12)',
        borderWidth: 1,
        padding: 10,
        cornerRadius: 8,
        displayColors: true,
        boxPadding: 4
      });
    }
  }

  function applyTokensToConfig(config, tokens) {
    if (!config) return;
    const chartType = config.type;
    if (chartType === 'doughnut') {
      config.options = config.options || {};
      if (!config.options.cutout) config.options.cutout = '72%';
      if (config.data && Array.isArray(config.data.datasets)) {
        config.data.datasets.forEach((ds) => {
          ds.borderWidth = 0;
        });
      }
    } else if (chartType === 'bar' && config.data && Array.isArray(config.data.datasets)) {
      config.data.datasets.forEach((ds) => {
        if (ds.borderRadius === undefined) ds.borderRadius = 6;
        if (ds.borderSkipped === undefined) ds.borderSkipped = false;
        if (ds.maxBarThickness === undefined) ds.maxBarThickness = 36;
      });
    }
    if (config.options) applyTokensToOptions(config.options, tokens);
  }

  function applyTokensToOptions(options, tokens) {
    if (!options) return;
    options.plugins = options.plugins || {};
    options.plugins.legend = options.plugins.legend || {};
    if (!options.plugins.legend.position) options.plugins.legend.position = 'top';
    if (!options.plugins.legend.align) options.plugins.legend.align = 'end';
    options.plugins.legend.labels = options.plugins.legend.labels || {};
    options.plugins.legend.labels.color = tokens.textSecondary;
    options.plugins.legend.labels.usePointStyle = true;
    options.plugins.legend.labels.pointStyle = 'circle';
    options.plugins.legend.labels.boxWidth = 8;
    options.plugins.legend.labels.boxHeight = 8;

    options.plugins.tooltip = options.plugins.tooltip || {};
    Object.assign(options.plugins.tooltip, {
      backgroundColor: '#0f172a',
      titleColor: '#f8fafc',
      bodyColor: '#e2e8f0',
      borderColor: 'rgba(255, 255, 255, 0.12)',
      borderWidth: 1,
      padding: 10,
      cornerRadius: 8,
      displayColors: true,
      boxPadding: 4
    });

    if (options.scales) {
      Object.keys(options.scales).forEach(function (axisKey) {
        const axis = options.scales[axisKey];
        if (!axis) return;
        if (axisKey === 'x') {
          axis.grid = Object.assign(axis.grid || {}, { display: false });
          axis.border = Object.assign(axis.border || {}, { display: false });
        } else {
          axis.grid = Object.assign(axis.grid || {}, {
            color: 'rgba(148, 163, 184, 0.15)',
            tickBorderDash: [4, 4]
          });
          axis.border = Object.assign(axis.border || {}, { display: false, dash: [4, 4] });
        }
        if (axis.ticks) axis.ticks.color = tokens.textMuted;
        if (axis.pointLabels) axis.pointLabels.color = tokens.textSecondary;
        if (axis.angleLines) axis.angleLines.color = 'rgba(148, 163, 184, 0.15)';
      });
    }
  }

  function resolveCanvas(target) {
    if (!target) return null;
    if (typeof target === 'string') return document.getElementById(target);
    return target;
  }

  function createThemedChart(target, configOrFactory) {
    if (typeof Chart === 'undefined') return null;
    const canvas = resolveCanvas(target);
    if (!canvas) return null;

    const existing = managedCharts.get(canvas);
    if (existing && existing.chart) {
      existing.chart.destroy();
      managedCharts.delete(canvas);
    }

    applyGlobalChartDefaults();
    const tokens = getThemeTokens();
    const isFactory = typeof configOrFactory === 'function';
    const config = isFactory ? configOrFactory(tokens) : configOrFactory;
    config.options = config.options || {};
    applyTokensToConfig(config, tokens);

    const chart = new Chart(canvas.getContext('2d'), config);
    managedCharts.set(canvas, { chart: chart, factory: isFactory ? configOrFactory : null });
    return chart;
  }

  function refreshAllCharts() {
    if (typeof Chart === 'undefined') return;
    applyGlobalChartDefaults();
    const tokens = getThemeTokens();

    managedCharts.forEach(function (entry, canvas) {
      if (!document.body.contains(canvas)) {
        entry.chart.destroy();
        managedCharts.delete(canvas);
        return;
      }
      if (entry.factory) {
        const updatedConfig = entry.factory(tokens);
        if (updatedConfig.data && updatedConfig.data.datasets) {
          updatedConfig.data.datasets.forEach(function (ds, idx) {
            if (entry.chart.data.datasets[idx]) Object.assign(entry.chart.data.datasets[idx], ds);
          });
        }
        if (updatedConfig.options) {
          applyTokensToConfig(updatedConfig, tokens);
          entry.chart.options = updatedConfig.options;
        }
      } else {
        applyTokensToOptions(entry.chart.options, tokens);
      }
      entry.chart.update('none');
    });

    if (Chart.instances) {
      Object.values(Chart.instances).forEach(function (inst) {
        if (inst && inst.canvas && !managedCharts.has(inst.canvas) && document.body.contains(inst.canvas)) {
          applyTokensToOptions(inst.options, tokens);
          inst.update('none');
        }
      });
    }
  }

  function initShellPreviewChart() {
    const canvas = document.getElementById('shell-preview-chart');
    if (!canvas) return;
    createThemedChart(canvas, function (tokens) {
      return {
        type: 'line',
        data: {
          labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6'],
          datasets: [
            {
              label: 'Avg Attendance %',
              data: [88, 90, 87, 91, 93, 92],
              borderColor: tokens.accentPrimary,
              backgroundColor: tokens.accentSoft,
              borderWidth: 2,
              tension: 0.35,
              fill: true,
              pointRadius: 3,
              pointBackgroundColor: tokens.accentPrimary
            },
            {
              label: 'Predicted Readiness %',
              data: [82, 84, 85, 88, 90, 91],
              borderColor: tokens.statusSuccess,
              backgroundColor: 'transparent',
              borderWidth: 2,
              borderDash: [5, 4],
              tension: 0.35,
              pointRadius: 3,
              pointBackgroundColor: tokens.statusSuccess
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          scales: {
            x: { ticks: { color: tokens.textMuted } },
            y: { min: 70, max: 100, ticks: { color: tokens.textMuted } }
          }
        }
      };
    });
  }

  window.getChartThemeTokens = getThemeTokens;
  window.createThemedChart = createThemedChart;
  window.EduPredictCharts = {
    getThemeTokens: getThemeTokens,
    applyGlobalChartDefaults: applyGlobalChartDefaults,
    createChart: createThemedChart,
    refreshAllCharts: refreshAllCharts
  };

  window.addEventListener('themeChanged', refreshAllCharts);
  document.addEventListener('DOMContentLoaded', function () {
    applyGlobalChartDefaults();
    initShellPreviewChart();
  });
})();
