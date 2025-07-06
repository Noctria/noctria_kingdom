{% extends "base.html" %}
{% block title %}📄 詳細: {{ key }} - Noctria Kingdom{% endblock %}

{% block content %}
<h2>📄 詳細表示（{{ "戦略" if mode == "strategy" else "タグ" }}）: {{ key }}</h2>

<!-- 🔽 ソート選択 -->
<form method="get" action="/statistics/detail" style="margin-bottom: 1rem;">
  <input type="hidden" name="mode" value="{{ mode }}">
  <input type="hidden" name="key" value="{{ key }}">

  <label>🔃 並び順:</label>
  <select name="sort_by">
    <option value="date" {% if sort_by == 'date' %}selected{% endif %}>📅 日付</option>
    <option value="win_rate" {% if sort_by == 'win_rate' %}selected{% endif %}>📈 勝率</option>
    <option value="max_drawdown" {% if sort_by == 'max_drawdown' %}selected{% endif %}>📉 最大DD</option>
  </select>

  <select name="order">
    <option value="asc" {% if order == 'asc' %}selected{% endif %}>昇順</option>
    <option value="desc" {% if order == 'desc' %}selected{% endif %}>降順</option>
  </select>

  <button type="submit" class="button">🔄 並び替え</button>
</form>

{% if results %}
  <p>📌 データ件数: <strong>{{ results | length }}</strong></p>
  <p>
    📈 平均勝率（%）:
    <strong>
      {{ results | map(attribute='win_rate') | select('!=', none) | list | sum / results|length | round(1) }}
    </strong><br>
    📉 平均DD（%）:
    <strong>
      {{ results | map(attribute='max_drawdown') | select('!=', none) | list | sum / results|length | round(1) }}
    </strong>
  </p>

  <canvas id="detailChart" height="120"></canvas>

  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script>
    const labels = {{ results | map(attribute='date') | list | tojson }};
    const winRates = {{ results | map(attribute='win_rate') | list | tojson }};
    const ddRates = {{ results | map(attribute='max_drawdown') | list | tojson }};

    new Chart(document.getElementById('detailChart'), {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: '勝率（%）',
            data: winRates,
            borderColor: 'rgba(54, 162, 235, 1)',
            backgroundColor: 'rgba(54, 162, 235, 0.2)',
            tension: 0.3,
            yAxisID: 'y',
          },
          {
            label: '最大DD（%）',
            data: ddRates,
            borderColor: 'rgba(255, 99, 132, 1)',
            backgroundColor: 'rgba(255, 99, 132, 0.2)',
            tension: 0.3,
            yAxisID: 'y1',
          }
        ]
      },
      options: {
        responsive: true,
        scales: {
          y: {
            type: 'linear',
            position: 'left',
            beginAtZero: true,
            title: { display: true, text: '勝率' }
          },
          y1: {
            type: 'linear',
            position: 'right',
            beginAtZero: true,
            grid: { drawOnChartArea: false },
            title: { display: true, text: '最大DD' }
          }
        }
      }
    });
  </script>
{% else %}
  <p>⚠ データが存在しません。</p>
{% endif %}

<a href="/statistics/compare" class="button" style="margin-top: 1rem;">← 比較ページへ戻る</a>
{% endblock %}
