// DOMの読み込みが完了してからスクリプトを実行する
document.addEventListener('DOMContentLoaded', function() {
  // プラグイン登録
  try {
    Chart.register(
      window.ChartjsChartHistogram.HistogramController,
      window.ChartjsChartHistogram.HistogramElement,
      window.ChartjsChartBoxplot.BoxPlotController,
      window.ChartjsChartBoxplot.BoxAndWhiskers,
      window.ChartjsChartBoxplot.Violin
    );
  } catch (e) {
    console.error("Chart.jsのプラグイン登録に失敗しました。ライブラリが正しく読み込まれているか確認してください。", e);
    return; // エラーが発生したらここで処理を中断
  }

  // --- データ準備 ---
  const metricsDict = JSON.parse(document.getElementById('forecast-data-holder').dataset.metricsDict || '{}');
  const overallMetrics = JSON.parse(document.getElementById('forecast-data-holder').dataset.overallMetrics || '{}');
  const dashboardMetrics = JSON.parse(document.getElementById('forecast-data-holder').dataset.dashboardMetrics || '[]');
  const aiNames = JSON.parse(document.getElementById('forecast-data-holder').dataset.aiNames || '[]');
  const aiMetricDist = JSON.parse(document.getElementById('forecast-data-holder').dataset.aiMetricDist || '{}');

  if (dashboardMetrics.length === 0 || aiNames.length === 0) {
      console.error("ダッシュボードの初期データが不足しています。");
      return;
  }
  
  // --- 状態管理 ---
  let selectedMetric = dashboardMetrics[0].key;
  let selectedAI = aiNames[0];
  let selectedMode = "trend"; // "trend" または "dist"

  // --- チャート描画関数 ---
  // トレンドチャートの描画
  function drawMetricChart(metric, ai) {
    const ctx = document.getElementById('metricChart').getContext('2d');
    if (window.metricChartObj) window.metricChartObj.destroy();

    let data, label, unit, dec;
    let showAI = (ai !== 'overall');
    
    if (showAI) {
      data = (metricsDict[metric] && metricsDict[metric][ai]) ? metricsDict[metric][ai] : { labels: [], values: [] };
      label = ai;
    } else {
      data = overallMetrics[metric];
      label = "全体平均";
    }

    let conf = dashboardMetrics.find(m => m.key === metric);
    unit = conf.unit;
    dec = conf.dec;
    window.metricChartObj = new Chart(ctx, { /* (Chart.jsのオプションは省略) */ });
    
    // UI更新処理
    updateSummaryUI(conf, data, unit);
    updateButtonActiveStates(ai);
  }
  
  // 分布チャートの描画
  function drawDistCharts(metric, ai) { /* (この関数の内容は変更なし) */ }

  // UI更新のための補助関数
  function updateSummaryUI(conf, data, unit) { /* (サマリーUI更新ロジック) */ }
  function updateButtonActiveStates(ai) {
    document.getElementById('ai-switcher').style.display = (ai !== 'overall') ? 'flex' : 'none';
    document.getElementById('tab-overall').classList.toggle('active', ai === 'overall');
    document.querySelectorAll('.ai-tab').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.aiName === ai);
    });
  }

  // --- イベントハンドラ関数 ---
  // onclickから呼び出せるように、windowオブジェクトに登録する
  window.switchMetric = function(metric, event) {
    selectedMetric = metric;
    document.querySelectorAll('.metric-tab').forEach(btn => btn.classList.remove('active'));
    if (event && event.currentTarget) {
        event.currentTarget.classList.add('active');
    }
    redrawCharts();
  }

  window.switchAI = function(ai) {
    selectedAI = ai;
    if (ai !== 'overall') {
      // URLのハッシュを更新
      window.history.pushState({}, '', '/dashboard#' + encodeURIComponent(ai));
    }
    redrawCharts();
  }

  window.switchChartMode = function(mode) {
    selectedMode = mode;
    document.querySelectorAll('.mode-tab').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`tab-${mode}`).classList.add('active');
    document.getElementById('trend-canvas-box').style.display = (mode === "trend") ? 'block' : 'none';
    document.getElementById('dist-canvas-box').style.display = (mode === "dist") ? 'block' : 'none';
    redrawCharts();
  }

  // 再描画をまとめる関数
  function redrawCharts() {
    if (selectedMode === "trend") {
      drawMetricChart(selectedMetric, selectedAI);
    } else {
      drawDistCharts(selectedMetric, selectedAI);
    }
  }

  // --- 初期描画 ---
  drawMetricChart(selectedMetric, selectedAI);
});
