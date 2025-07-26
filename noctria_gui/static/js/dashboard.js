/**
 * Noctria Kingdom - Central Governance HUD
 * ダッシュボードのインタラクティブなチャートを管理します。
 */
document.addEventListener('DOMContentLoaded', () => {

  // --- ライブラリの存在チェックと登録 ---
  if (typeof Chart === 'undefined') {
    console.error('Chart.js本体が読み込まれていません。dashboard.htmlの<script>タグを確認してください。');
    return;
  }
  
  try {
    if (typeof window.ChartjsChartHistogram === 'undefined') {
      throw new Error('Histogramプラグインが読み込まれていません。CDN URLを確認してください。');
    }

    // histogramプラグインの必要なコンポーネントがあればここで登録（なければ不要）
    // Chart.register(...)  // histogramプラグインが自動登録されていれば省略可能

  } catch (e) {
    console.error('Chart.jsのプラグイン登録に失敗しました。', e);
    return;
  }

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
  const aiMetricDist = JSON.parse(dataHolder.dataset.aiMetricDist || '{}');

  if (dashboardMetrics.length === 0 || aiNames.length === 0) {
    console.warn("ダッシュボードの表示に必要なデータが不足しています。");
  }

  // --- 状態管理 ---
  let selectedMetric = dashboardMetrics.length > 0 ? dashboardMetrics[0].key : null;
  let selectedAI = aiNames.length > 0 ? aiNames[0] : null;
  let selectedMode = 'trend';

  // --- チャートインスタンス管理 ---
  let metricChartObj, histChart, boxChart;

  // トレンドチャート描画
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

  // 分布チャート描画
  function drawDistCharts(metric, ai) {
    const histCtx = document.getElementById('distHistogram')?.getContext('2d');
    const boxCtx = document.getElementById('distBoxplot')?.getContext('2d');
    if (!histCtx || !boxCtx) return;

    if (histChart) histChart.destroy();
    if (boxChart) boxChart.destroy();

    const conf = dashboardMetrics.find(m => m.key === metric);
    if (!conf) return;

    const data = (ai === 'overall')
      ? (aiMetricDist[metric]?.flatMap(d => d.values) || [])
      : (aiMetricDist[metric]?.find(d => d.ai === ai)?.values || []);
    
    const label = ai === 'overall' ? '全体' : ai;

    histChart = new Chart(histCtx, { 
      type: 'histogram', data: { datasets: [{ label: conf.label, data: data, backgroundColor: 'rgba(24,225,239,0.5)', borderColor: '#18e1ef', }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, title: { display: true, text: `${conf.label} 分布（${label}）`, color: "#e6f1ff" } }, scales: { x: { ticks: { color: "#a8b2d1" } }, y: { ticks: { color: "#a8b2d1" } } } }
    });
    boxChart = new Chart(boxCtx, { 
      type: 'boxplot', data: { labels: [conf.label], datasets: [{ label: conf.label, data: [data], backgroundColor: 'rgba(34,38,58,0.86)', borderColor: '#7eeafc', outlierColor: '#FF6384', }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { ticks: { color: "#a8b2d1" } } } }
    });
  }

  // サマリーUI更新
  function updateSummaryUI(conf, data) {
    const format = (val) => val != null ? val : "-";
    document.getElementById('metric-summary-label').textContent = conf.label;
    document.getElementById('metric-avg').textContent = format(data.avg);
    document.getElementById('metric-max').textContent = format(data.max);
    document.getElementById('metric-min').textContent = format(data.min);
    document.getElementById('metric-diff').textContent = data.diff != null ? (data.diff >= 0 ? `+${data.diff}` : data.diff) : "-";
    document.querySelectorAll('#metric-unit, #metric-unit-max, #metric-unit-min, #metric-unit-diff').forEach(el => el.textContent = conf.unit || '');
  }

  // チャート再描画
  function redrawCharts() {
    if (!selectedMetric || !selectedAI) return;
    if (selectedMode === 'trend') {
      drawMetricChart(selectedMetric, selectedAI);
    } else {
      drawDistCharts(selectedMetric, selectedAI);
    }
  }

  // グローバル関数登録
  window.switchChartMode = (mode) => {
    selectedMode = mode;
    document.getElementById('tab-trend').classList.toggle('active', mode === 'trend');
    document.getElementById('tab-dist').classList.toggle('active', mode === 'dist');
    document.getElementById('trend-canvas-box').style.display = (mode === 'trend') ? 'block' : 'none';
    document.getElementById('dist-canvas-box').style.display = (mode === 'dist') ? 'block' : 'none';
    redrawCharts();
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

  // 初期化
  if(selectedMetric && selectedAI) {
    redrawCharts();
    window.switchAI(selectedAI);
  }
});
