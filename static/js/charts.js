/* ==========================================================================
   RMMV Dashboard — Chart.js Utilities
   ========================================================================== */

/* --------------------------------------------------------------------------
   Global Chart.js Defaults
   -------------------------------------------------------------------------- */
(function () {
  'use strict';

  if (typeof Chart === 'undefined') return;

  // Font defaults
  Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
  Chart.defaults.font.size = 12;
  Chart.defaults.color = '#6c757d';

  // Responsive defaults
  Chart.defaults.responsive = true;
  Chart.defaults.maintainAspectRatio = false;

  // Tooltip defaults
  Chart.defaults.plugins.tooltip.backgroundColor = '#0a192f';
  Chart.defaults.plugins.tooltip.titleFont = { weight: '600', size: 13 };
  Chart.defaults.plugins.tooltip.bodyFont = { size: 12 };
  Chart.defaults.plugins.tooltip.padding = 12;
  Chart.defaults.plugins.tooltip.cornerRadius = 6;
  Chart.defaults.plugins.tooltip.displayColors = true;
  Chart.defaults.plugins.tooltip.boxPadding = 4;

  // Legend defaults
  Chart.defaults.plugins.legend.position = 'bottom';
  Chart.defaults.plugins.legend.labels.padding = 20;
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.legend.labels.pointStyle = 'circle';
})();


/**
 * Grouped bar chart comparing physical vs financial progress per ULB/project.
 *
 * @param {string} canvasId      – id of the <canvas> element
 * @param {Array}  labels        – Array of ULB or project names
 * @param {Array}  physicalData  – Array of physical progress percentages
 * @param {Array}  financialData – Array of financial progress percentages
 * @returns {Chart} Chart.js instance
 */
function initProgressChart(canvasId, labels, physicalData, financialData) {
  'use strict';

  var ctx = document.getElementById(canvasId);
  if (!ctx) return null;

  return new Chart(ctx.getContext('2d'), {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Physical Progress (%)',
          data: physicalData,
          backgroundColor: 'rgba(10, 25, 47, 0.8)',
          borderColor: '#0a192f',
          borderWidth: 1,
          borderRadius: 4,
          barPercentage: 0.7,
          categoryPercentage: 0.6
        },
        {
          label: 'Financial Progress (%)',
          data: financialData,
          backgroundColor: 'rgba(217, 4, 41, 0.8)',
          borderColor: '#d90429',
          borderWidth: 1,
          borderRadius: 4,
          barPercentage: 0.7,
          categoryPercentage: 0.6
        }
      ]
    },
    options: {
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          grid: {
            color: 'rgba(0,0,0,0.05)',
            drawBorder: false
          },
          ticks: {
            callback: function (val) { return val + '%'; },
            stepSize: 20
          }
        },
        x: {
          grid: { display: false }
        }
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: function (ctx) {
              return ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(1) + '%';
            }
          }
        }
      }
    }
  });
}


/**
 * Doughnut chart showing project status distribution.
 *
 * @param {string} canvasId     – id of the <canvas> element
 * @param {Object} statusCounts – { active: N, delayed: N, critical: N, completed: N }
 * @returns {Chart} Chart.js instance
 */
function initStatusDonut(canvasId, statusCounts) {
  'use strict';

  var ctx = document.getElementById(canvasId);
  if (!ctx) return null;

  var labels = [];
  var data   = [];
  var colors = [];

  var colorMap = {
    active:    '#00b894',
    delayed:   '#fdcb6e',
    critical:  '#d63031',
    completed: '#0984e3'
  };

  var order = ['active', 'delayed', 'critical', 'completed'];

  order.forEach(function (key) {
    if (statusCounts.hasOwnProperty(key)) {
      labels.push(key.charAt(0).toUpperCase() + key.slice(1));
      data.push(statusCounts[key]);
      colors.push(colorMap[key] || '#6c757d');
    }
  });

  return new Chart(ctx.getContext('2d'), {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: colors,
        borderColor: '#ffffff',
        borderWidth: 3,
        hoverOffset: 8
      }]
    },
    options: {
      cutout: '62%',
      plugins: {
        tooltip: {
          callbacks: {
            label: function (ctx) {
              var total = ctx.dataset.data.reduce(function (a, b) { return a + b; }, 0);
              var pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
              return ctx.label + ': ' + ctx.parsed + ' (' + pct + '%)';
            }
          }
        }
      }
    }
  });
}


/**
 * Horizontal bar chart ranking ULBs by average progress score.
 *
 * @param {string} canvasId – id of the <canvas> element
 * @param {Array}  ulbNames – Array of ULB names
 * @param {Array}  scores   – Array of average progress scores (0-100)
 * @returns {Chart} Chart.js instance
 */
function initULBRankingChart(canvasId, ulbNames, scores) {
  'use strict';

  var ctx = document.getElementById(canvasId);
  if (!ctx) return null;

  // Generate gradient-style colours based on score
  var barColors = scores.map(function (s) {
    if (s >= 75) return '#00b894';
    if (s >= 50) return '#0984e3';
    if (s >= 25) return '#fdcb6e';
    return '#d63031';
  });

  return new Chart(ctx.getContext('2d'), {
    type: 'bar',
    data: {
      labels: ulbNames,
      datasets: [{
        label: 'Avg Progress (%)',
        data: scores,
        backgroundColor: barColors,
        borderColor: barColors,
        borderWidth: 1,
        borderRadius: 4,
        barPercentage: 0.65
      }]
    },
    options: {
      indexAxis: 'y',
      scales: {
        x: {
          beginAtZero: true,
          max: 100,
          grid: {
            color: 'rgba(0,0,0,0.05)',
            drawBorder: false
          },
          ticks: {
            callback: function (val) { return val + '%'; }
          }
        },
        y: {
          grid: { display: false }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function (ctx) {
              return 'Average: ' + ctx.parsed.x.toFixed(1) + '%';
            }
          }
        }
      }
    }
  });
}


/**
 * Simple bar chart for activity-wise progress in project detail view.
 *
 * @param {string} canvasId  – id of the <canvas> element
 * @param {Array}  labels    – Activity names
 * @param {Array}  targetQty – Target quantities
 * @param {Array}  achieved  – Achieved quantities
 * @returns {Chart} Chart.js instance
 */
function initActivityChart(canvasId, labels, targetQty, achieved) {
  'use strict';

  var ctx = document.getElementById(canvasId);
  if (!ctx) return null;

  return new Chart(ctx.getContext('2d'), {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Target',
          data: targetQty,
          backgroundColor: 'rgba(10, 25, 47, 0.2)',
          borderColor: '#0a192f',
          borderWidth: 1,
          borderRadius: 4,
          barPercentage: 0.7,
          categoryPercentage: 0.6
        },
        {
          label: 'Achieved',
          data: achieved,
          backgroundColor: 'rgba(0, 184, 148, 0.7)',
          borderColor: '#00b894',
          borderWidth: 1,
          borderRadius: 4,
          barPercentage: 0.7,
          categoryPercentage: 0.6
        }
      ]
    },
    options: {
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: 'rgba(0,0,0,0.05)', drawBorder: false }
        },
        x: {
          grid: { display: false }
        }
      }
    }
  });
}
