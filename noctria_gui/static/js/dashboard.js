document.addEventListener('DOMContentLoaded', () => {
  if (typeof Chart === 'undefined') {
    console.error('Chart.js本体が読み込まれていません。dashboard.htmlの<script>タグを確認してください。');
    return;
  }

  // ※ Histogram, BoxPlotプラグイン関連のチェック・登録を一時削除

  // --- データ取得 ---
  const dataHolder = document.getElementById('data-holder');
  if (!dataHolder) {
    console.error('データ保持用のdiv要素(#data-holder)が見つかりません。');
    return;
  }
  const metricsDict = JSON.parse(dataHolder.dataset.metricsDict || '{}');
  const overallMetrics = JSON.parse(dataHolder.dataset.overallMetrics || '{}');
  const dashboardMetrics = JSON.parse(dataHolder.dataset.dashboardMetrics || '[]');
  const aiNames = JSON.parse(dataHolder.dataset.aiNames || '[]');
  // HistogramやBoxPlot用データは無視
  // const aiMetricDist = JSON.parse(dataHolder.dataset.aiMetricDist || '{}');

  if (dashboardMetrics.length === 0 || aiNames.length === 0) {
    console.warn("ダッシュボードの表示に必要なデータが不足しています。");
  }

  let selectedMetric = dashboardMetrics.length > 0 ? dashboardMetrics[0].key : null;
  let selectedAI = aiNames.length > 0 ? aiNames[0] : null;
  let selectedMode = 'trend';

  let metricChartObj;

  function drawMetricChart(metric, ai) {
    const ctx = document.getElementById('metricChart')?.getContext('2d');
    if (!ctx) return;
    if (metricChartObj) metricChartObj.destroy();

    const conf = dashboardMetrics.find(m => m.key === metric);
    if (!conf) return;

    const showAI = ai !== 'overall';
    const data = showAI ? (metricsDict[metric]?.[ai] || { labels: [], values: [] }) : (overallMetrics[metric] || { labels: [], values: [] });
    const label = showAI ? ai : '全体平均';

    metricChartObj = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.labels,
        datasets: [{
          label: `${conf.label}（${label}）`,
          data: data.values,
          borderColor: '#18e1ef',
          backgroundColor: 'rgba(24,225,239,0.10)',
          pointRadius: 3,
          tension: 0.2,
          fill: true
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#e6f1ff" } }, title: { display: false } },
        scales: { x: { ticks: { color: "#a8b2d1" } }, y: { ticks: { color: "#a8b2d1" } } }
      }
    });
    updateSummaryUI(conf, data);
  }

  // 分布チャート関連関数は一旦コメントアウト（未使用に）
  /*
  function drawDistCharts(metric, ai) {
    // 削除またはコメントアウト
  }
  */

  function updateSummaryUI(conf, data) {
    const format = (val) => val != null ? val : "-";
    document.getElementById('metric-summary-label').textContent = conf.label;
    document.getElementById('metric-avg').textContent = format(data.avg);
    document.getElementById('metric-max').textContent = format(data.max);
    document.getElementById('metric-min').textContent = format(data.min);
    document.getElementById('metric-diff').textContent = data.diff != null ? (data.diff >= 0 ? `+${data.diff}` : data.diff) : "-";
    document.querySelectorAll('#metric-unit, #metric-unit-max, #metric-unit-min, #metric-unit-diff').forEach(el => el.textContent = conf.unit || '');
  }

  function redrawCharts() {
    if (!selectedMetric || !selectedAI) return;
    // プラグイン使わないので常にトレンドチャートだけ描画
    drawMetricChart(selectedMetric, selectedAI);
  }

  window.switchChartMode = (mode) => {
    // 無効化またはデフォルトのままにする
    console.warn('チャートモード切替は無効化されています。');
  };

  window.switchMetric = (metric, event) => {
    selectedMetric = metric;
    document.querySelectorAll('.metric-tab').forEach(btn => btn.classList.remove('active'));
    if (event && event.currentTarget) {
      event.currentTarget.classList.add('active');
    }
    redrawCharts();
  };

  window.switchAI = (ai) => {
    selectedAI = ai;
    const isOverall = ai === 'overall';
    document.getElementById('ai-switcher').style.display = isOverall ? 'none' : 'flex';
    document.getElementById('tab-overall').classList.toggle('active', isOverall);
    document.querySelectorAll('.ai-tab').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.aiName === ai);
    });
    if (!isOverall) {
      window.history.pushState({}, '', `/dashboard#${encodeURIComponent(ai)}`);
    }
    redrawCharts();
  };

  if(selectedMetric && selectedAI) {
    redrawCharts();
    window.switchAI(selectedAI);
  }
});
