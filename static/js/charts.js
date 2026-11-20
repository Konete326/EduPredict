(function () {
  const managedCharts = new Map();

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
      borderSubtle: readCssVar('--border-subtle', isDark ? '#1e293b' : '#e2e8f0'),
      accentPrimary: readCssVar('--accent-primary', isDark ? '#3b82f6' : '#2563eb'),
      accentHover: readCssVar('--accent-hover', isDark ? '#60a5fa' : '#1d4ed8'),
      accentSoft: readCssVar('--accent-soft', isDark ? 'rgba(59, 130, 246, 0.16)' : '#eff6ff'),
      statusSuccess: readCssVar('--status-success', isDark ? '#22c55e' : '#16a34a'),
      statusWarning: readCssVar('--status-warning', isDark ? '#f59e0b' : '#d97706'),
      statusDanger: readCssVar('--status-danger', isDark ? '#ef4444' : '#dc2626')
    };
  }

  function applyGlobalChartDefaults() {
    if (typeof Chart === 'undefined') {
      return;
    }
    const tokens = getThemeTokens();
    Chart.defaults.color = tokens.textSecondary;
    Chart.defaults.borderColor = tokens.borderSubtle;
    Chart.defaults.font.family = "'Inter', ui-sans-serif, system-ui, sans-serif";
    if (Chart.defaults.plugins && Chart.defaults.plugins.legend && Chart.defaults.plugins.legend.labels) {
      Chart.defaults.plugins.legend.labels.color = tokens.textSecondary;
    }
    if (Chart.defaults.plugins && Chart.defaults.plugins.tooltip) {
      Chart.defaults.plugins.tooltip.backgroundColor = tokens.bgSurface;
      Chart.defaults.plugins.tooltip.titleColor = tokens.textPrimary;
      Chart.defaults.plugins.tooltip.bodyColor = tokens.textSecondary;
      Chart.defaults.plugins.tooltip.borderColor = tokens.borderSubtle;
      Chart.defaults.plugins.tooltip.borderWidth = 1;
    }
  }

  function applyTokensToOptions(options, tokens) {
    if (!options) {
      return;
    }
    if (!options.plugins) {
      options.plugins = {};
    }
    if (!options.plugins.legend) {
      options.plugins.legend = {};
    }
    if (!options.plugins.legend.labels) {
      options.plugins.legend.labels = {};
    }
    options.plugins.legend.labels.color = tokens.textSecondary;

    if (!options.plugins.tooltip) {
      options.plugins.tooltip = {};
    }
    options.plugins.tooltip.backgroundColor = tokens.bgSurface;
    options.plugins.tooltip.titleColor = tokens.textPrimary;
    options.plugins.tooltip.bodyColor = tokens.textSecondary;
    options.plugins.tooltip.borderColor = tokens.borderSubtle;
    options.plugins.tooltip.borderWidth = 1;

    if (options.scales) {
      Object.keys(options.scales).forEach(function (axisKey) {
        const axis = options.scales[axisKey];
        if (!axis) {
          return;
        }
        if (axis.grid) {
          axis.grid.color = tokens.borderSubtle;
        }
        if (axis.ticks) {
          axis.ticks.color = tokens.textMuted;
        }
        if (axis.pointLabels) {
          axis.pointLabels.color = tokens.textSecondary;
        }
        if (axis.angleLines) {
          axis.angleLines.color = tokens.borderSubtle;
        }
      });
    }
  }

  function resolveCanvas(target) {
    if (!target) {
      return null;
    }
    if (typeof target === 'string') {
      return document.getElementById(target);
    }
    return target;
  }

  function createThemedChart(target, configOrFactory) {
    if (typeof Chart === 'undefined') {
      return null;
    }
    const canvas = resolveCanvas(target);
    if (!canvas) {
      return null;
    }

    const existing = managedCharts.get(canvas);
    if (existing && existing.chart) {
      existing.chart.destroy();
      managedCharts.delete(canvas);
    }

    applyGlobalChartDefaults();
    const tokens = getThemeTokens();
    const isFactory = typeof configOrFactory === 'function';
    const config = isFactory ? configOrFactory(tokens) : configOrFactory;
    if (!config.options) {
      config.options = {};
    }
    applyTokensToOptions(config.options, tokens);

    const chart = new Chart(canvas.getContext('2d'), config);
    managedCharts.set(canvas, {
      chart: chart,
      factory: isFactory ? configOrFactory : null
    });
    return chart;
  }

  function refreshAllCharts() {
    if (typeof Chart === 'undefined') {
      return;
    }
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
            if (entry.chart.data.datasets[idx]) {
              Object.assign(entry.chart.data.datasets[idx], ds);
            }
          });
        }
        if (updatedConfig.options) {
          applyTokensToOptions(updatedConfig.options, tokens);
          entry.chart.options = updatedConfig.options;
        }
      } else {
        applyTokensToOptions(entry.chart.options, tokens);
      }
      entry.chart.update('none');
    });
  }

  function initShellPreviewChart() {
    const canvas = document.getElementById('shell-preview-chart');
    if (!canvas) {
      return;
    }
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
          interaction: {
            mode: 'index',
            intersect: false
          },
          plugins: {
            legend: {
              position: 'top',
              align: 'end',
              labels: {
                usePointStyle: true,
                boxWidth: 8,
                color: tokens.textSecondary
              }
            }
          },
          scales: {
            x: {
              grid: {
                color: tokens.borderSubtle,
                drawBorder: false
              },
              ticks: {
                color: tokens.textMuted
              }
            },
            y: {
              min: 70,
              max: 100,
              grid: {
                color: tokens.borderSubtle,
                drawBorder: false
              },
              ticks: {
                color: tokens.textMuted
              }
            }
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
