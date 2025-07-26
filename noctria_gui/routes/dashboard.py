{% extends "base_hud.html" %}

{% block title %}👑 Noctria Kingdom - Central Governance HUD{% endblock %}

{% block header_icon %}<i class="fas fa-chess-king"></i>{% endblock %}
{% block header_title %}CENTRAL GOVERNANCE HUD{% endblock %}
{% block header_nav_href %}#{% endblock %}
{% block header_nav_text %}—{% endblock %}

{% block content %}
<!-- 🔢 Key Metrics -->
<section class="hud-panel metrics">
    <h2 class="panel-title">KEY METRICS</h2>
    <div style="display: flex; gap: 2rem; flex-wrap: wrap;">
        <div class="metric-item">
            <h3><i class="fas fa-chart-line"></i> 平均勝率</h3>
            <p class="metric-value text-green">
                {{ overall_metrics['win_rate']['avg'] if overall_metrics['win_rate'] else '-' }}%
            </p>
        </div>
        <div class="metric-item">
            <h3><i class="fas fa-arrow-up"></i> 採用戦略数</h3>
            <p class="metric-value">{{ stats.promoted_count }}</p>
        </div>
        <div class="metric-item">
            <h3><i class="fas fa-upload"></i> GitHubへPush済</h3>
            <p class="metric-value text-blue">{{ stats.pushed_count }}</p>
        </div>
        <div class="metric-item">
            <h3><i class="fas fa-history"></i> PDCA再評価数</h3>
            <p class="metric-value text-yellow">{{ stats.pdca_count }}</p>
        </div>
    </div>
</section>

<!-- 📈 Oracle予測グラフ（従来通り） -->
<section class="hud-panel">
    <h2 class="panel-title"><i class="fas fa-chart-area"></i> ORACLE予測チャート</h2>
    <div id="forecast-data-holder" data-forecast='{{ forecast | tojson | safe }}'></div>
    <canvas id="forecastChart" width="900" height="300" style="max-width:100%; background:#181c2b; margin:16px 0;"></canvas>
</section>

<!-- 🟦 指標×AI切替型ダッシュボード -->
<section class="hud-panel">
    <h2 class="panel-title"><i class="fas fa-chart-bar"></i> 全AI・全指標トレンド可視化</h2>
    <div class="metric-switcher" style="display:flex; gap:1.1rem; margin-bottom:.9rem;">
        {% for m in dashboard_metrics %}
            <button class="metric-tab{% if loop.first %} active{% endif %}" onclick="switchMetric('{{ m.key }}')">
                {{ m.label }}
            </button>
        {% endfor %}
        <button class="metric-tab metric-tab-overall" onclick="switchAI('overall')" id="tab-overall" style="margin-left:2em;">
            <i class="fas fa-globe"></i> 全体平均
        </button>
    </div>
    <div class="ai-switcher" id="ai-switcher" style="margin-bottom: 1rem;">
      {% for ai in ai_names %}
        <button class="ai-tab{% if loop.first %} active{% endif %}" onclick="switchAI('{{ ai }}')">
            {{ ai }}
        </button>
      {% endfor %}
    </div>
    <canvas id="metricChart" width="900" height="230" style="max-width:100%; background:#181c2b; margin:16px 0;"></canvas>
    <div class="metric-summary" style="margin-top:1.5rem; color:#aee3fc; font-size:1.1em;">
      <span id="metric-summary-label">平均</span>: <span id="metric-avg">-</span><span id="metric-unit"></span>
      ／ 最大: <span id="metric-max">-</span><span id="metric-unit-max"></span>
      ／ 最小: <span id="metric-min">-</span><span id="metric-unit-min"></span>
      ／ 前回差分: <span id="metric-diff">-</span><span id="metric-unit-diff"></span>
    </div>
</section>

<!-- 🟧 AIごとの進捗率 -->
<section class="hud-panel">
    <h2 class="panel-title"><i class="fas fa-bolt"></i> AIごとの進捗率</h2>
    <div class="panel-graph-row" style="display:flex;gap:2rem;flex-wrap:wrap;">
      {% for ai in ai_progress %}
      <div class="mini-panel" style="flex:1 1 220px;min-width:180px;max-width:240px; background:rgba(34,38,58,0.86); border-radius:1.2rem; padding:1rem 1.2rem; box-shadow:0 0 14px 0 #199bda38;">
        <h3 style="font-size:1.1rem;color:#7eeafc;font-weight:600;">{{ ai.name }}</h3>
        <canvas id="progress-{{ ai.id }}" width="120" height="120"></canvas>
        <div class="progress-label" style="margin-top:.7em; color:#e6f1ff;font-weight:bold;">
          {{ ai.progress }}%
          <span style="margin-left:1em; color:#aac7ff;font-weight:normal;">{{ ai.phase }}</span>
        </div>
      </div>
      {% endfor %}
    </div>
</section>
{% endblock %}

{% block extra_scripts %}
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    // --- Oracle予測グラフ（従来通り） ---
    {
        const dataHolder = document.getElementById('forecast-data-holder');
        const canvas = document.getElementById('forecastChart');
        if (dataHolder && canvas) {
            let forecastData = [];
            try { forecastData = JSON.parse(dataHolder.dataset.forecast || "[]"); } catch (e) {}
            if (Array.isArray(forecastData) && forecastData.length > 0) {
                const labels = forecastData.map(d => d.date);
                const forecasts = forecastData.map(d => d.forecast);
                const lowers = forecastData.map(d => d.lower);
                const uppers = forecastData.map(d => d.upper);
                new Chart(canvas.getContext('2d'), {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [
                            { label: '予測値', data: forecasts, borderColor: '#00e5ff', backgroundColor: 'rgba(0,229,255,0.12)', pointRadius: 3, tension: 0.25, fill: false },
                            { label: '下限', data: lowers, borderColor: 'rgba(255, 99, 132, 0.5)', borderDash: [5, 5], fill: false, pointRadius: 0, tension: 0.2 },
                            { label: '上限', data: uppers, borderColor: 'rgba(99, 255, 132, 0.5)', borderDash: [5, 5], fill: false, pointRadius: 0, tension: 0.2 }
                        ]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: { display: true, labels: { color: '#e6f1ff' } },
                            title: { display: true, text: 'Oracle予測時系列', color: '#e6f1ff' }
                        },
                        scales: {
                            x: { ticks: { color: '#a8b2d1' }, title: { display: true, text: '日付', color: '#a8b2d1' } },
                            y: { ticks: { color: '#a8b2d1' }, title: { display: true, text: '価格', color: '#a8b2d1' } }
                        }
                    }
                });
            }
        }
    }

    // --- 指標×AI切替グラフ ---
    const metricsDict = {{ metrics_dict | tojson | safe }};
    const overallMetrics = {{ overall_metrics | tojson | safe }};
    const dashboardMetrics = {{ dashboard_metrics | tojson | safe }};
    const aiNames = {{ ai_names | tojson | safe }};
    let selectedMetric = dashboardMetrics[0].key;
    let selectedAI = aiNames[0];
    function getMetricConfig(key) {
        return dashboardMetrics.find(m => m.key === key) || {label: key, unit: "", dec: 2};
    }
    function drawMetricChart(metric, ai) {
        const ctx = document.getElementById('metricChart').getContext('2d');
        if (window.metricChartObj) window.metricChartObj.destroy();
        let data, label, unit, dec;
        let showAI = true;
        if (ai === 'overall') {
            data = overallMetrics[metric];
            label = "全体平均";
            showAI = false;
        } else {
            data = (metricsDict[metric] && metricsDict[metric][ai]) ? metricsDict[metric][ai] : null;
            label = ai;
        }
        let conf = getMetricConfig(metric);
        unit = conf.unit;
        dec = conf.dec;
        window.metricChartObj = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: conf.label + (showAI ? `（${label}）` : "（全体平均）"),
                    data: data.values,
                    borderColor: '#18e1ef',
                    backgroundColor: 'rgba(24,225,239,0.10)',
                    pointRadius: 3,
                    tension: 0.20,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { labels: { color: "#e6f1ff" } },
                    title: { display: true, text: `${conf.label}トレンド（${label}）`, color: "#e6f1ff" }
                },
                scales: {
                    x: { ticks: { color: "#a8b2d1" } },
                    y: { ticks: { color: "#a8b2d1" } }
                }
            }
        });
        // サマリー
        document.getElementById('metric-summary-label').textContent = conf.label;
        document.getElementById('metric-avg').textContent = (data.avg != null) ? data.avg : "-";
        document.getElementById('metric-max').textContent = (data.max != null) ? data.max : "-";
        document.getElementById('metric-min').textContent = (data.min != null) ? data.min : "-";
        document.getElementById('metric-diff').textContent = (data.diff != null ? (data.diff >= 0 ? "+" : "") + data.diff : "-");
        document.getElementById('metric-unit').textContent = unit;
        document.getElementById('metric-unit-max').textContent = unit;
        document.getElementById('metric-unit-min').textContent = unit;
        document.getElementById('metric-unit-diff').textContent = unit;
        // AI切替ボタンの表示/非表示
        document.getElementById('ai-switcher').style.display = showAI ? 'flex' : 'none';
        // 全体平均タブactive切替
        document.getElementById('tab-overall').classList.toggle('active', !showAI);
        // AIタブactive切替
        if (showAI) {
            document.querySelectorAll('.ai-tab').forEach(btn => btn.classList.remove('active'));
            document.querySelector(`.ai-tab[onclick*="${ai}"]`).classList.add('active');
        }
        // 指標タブactive切替
        document.querySelectorAll('.metric-tab').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`.metric-tab[onclick*="${metric}"]`).classList.add('active');
    }
    window.switchMetric = function(metric) {
        selectedMetric = metric;
        drawMetricChart(selectedMetric, selectedAI);
    }
    window.switchAI = function(ai) {
        selectedAI = ai;
        drawMetricChart(selectedMetric, selectedAI);
    }
    // 初期表示
    drawMetricChart(selectedMetric, selectedAI);

    // --- AI進捗ゲージ（ドーナツ型） ---
    {% for ai in ai_progress %}
    (function() {
        const ctx = document.getElementById('progress-{{ ai.id }}');
        if (!ctx) return;
        new Chart(ctx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['進捗', '残り'],
                datasets: [{
                    data: [{{ ai.progress }}, {{ 100 - ai.progress }}],
                    backgroundColor: ['#31edc2', '#1b2233'],
                    borderWidth: 0
                }]
            },
            options: {
                cutout: "70%",
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            }
        });
    })();
    {% endfor %}
});
</script>
<style>
.metric-switcher {
    display: flex;
    gap: 1.2rem;
    margin-bottom: 0.8rem;
}
.metric-tab {
    border: none;
    background: var(--hud-btn-bg, #232844);
    color: #fff;
    font-family: inherit;
    font-size: 1.05rem;
    border-radius: 0.9rem;
    box-shadow: 0 0 10px var(--glow-primary, #09f9);
    padding: 0.42rem 1.1rem;
    cursor: pointer;
    transition: background 0.15s;
    opacity: 0.84;
}
.metric-tab.active, .metric-tab:hover {
    background: var(--glow-primary, #0976ff66);
    opacity: 1;
}
.metric-tab-overall {
    background: #12223c;
    color: #aee3fc;
    font-weight: bold;
}
.ai-switcher {
    display: flex;
    gap: 1rem;
    margin-bottom: 0.5rem;
}
.ai-tab {
    border: none;
    background: var(--hud-btn-bg, #222);
    color: #fff;
    font-family: inherit;
    font-size: 1.05rem;
    border-radius: 0.9rem;
    box-shadow: 0 0 8px var(--glow-primary, #09f9);
    padding: 0.40rem 1.0rem;
    cursor: pointer;
    transition: background 0.15s;
    opacity: 0.83;
}
.ai-tab.active, .ai-tab:hover {
    background: var(--glow-primary, #0976ff66);
    opacity: 1;
}
.metric-summary span {
    min-width: 2.5em;
    display: inline-block;
    text-align: right;
    font-variant-numeric: tabular-nums;
}
</style>
{% endblock %}
