{% extends "base.html" %}
{% block title %}📊 比較分析 - Noctria Kingdom{% endblock %}

{% block content %}
<h2>📊 戦略・タグ比較分析</h2>

<!-- 🔍 フィルター（GET） -->
<form method="get" action="/statistics/compare" style="margin-bottom: 1.5rem;">
  <label>📌 モード選択：</label>
  <select name="mode">
    <option value="strategy" {% if mode == "strategy" %}selected{% endif %}>🧠 戦略別</option>
    <option value="tag" {% if mode == "tag" %}selected{% endif %}>🔖 タグ別</option>
  </select>

  <label style="margin-left: 1rem;">📅 期間：</label>
  <input type="date" name="from" value="{{ filter.from }}">
  〜
  <input type="date" name="to" value="{{ filter.to }}">

  <label style="margin-left: 1rem;">🔽 ソート：</label>
  <select name="sort">
    <option value="score" {% if sort == "score" %}selected{% endif %}>📈 勝率・DD順</option>
    <option value="check" {% if sort == "check" %}selected{% endif %}>🗂 チェック順</option>
  </select>

  <!-- ✅ 比較対象選択 -->
  <div style="margin: 1rem 0;">
    <label>{{ "🔖 タグ一覧：" if mode == "tag" else "🧠 戦略一覧：" }}</label>
    <div style="max-height: 200px; overflow-y: auto; border: 1px solid #ccc; padding: 0.5rem;">
      <button type="button" class="button" onclick="selectAll(true)">✅ 全選択</button>
      <button type="button" class="button" onclick="selectAll(false)">❌ 全解除</button>
      <span style="margin-left: 1rem;">✅ 選択数: <span id="selectedCount">0</span></span><br><br>
      {% for k in all_keys %}
        <label style="display: inline-block; margin-right: 1rem;">
          <input type="checkbox" name="{{ mode }}s" value="{{ k }}" {% if k in keys %}checked{% endif %} onchange="updateCount()">
          {{ k }}
        </label>
      {% endfor %}
    </div>
  </div>

  <button type="submit" class="button">📥 表示</button>
  {% if keys %}
    <a href="/statistics/compare/export?mode={{ mode }}&from={{ filter.from }}&to={{ filter.to }}&sort={{ sort }}&{{ mode }}s={{ keys | join(',') }}" class="button">📄 CSV出力</a>
  {% endif %}
</form>

<!-- 🔗 URL共有 -->
{% if keys %}
  <div style="margin-top: 1rem;">
    <label>🔗 現在のURL（共有可）:</label><br>
    <input id="shareUrl" type="text" readonly style="width: 90%;" value="{{ request.url }}" />
    <button class="button" onclick="copyUrl()">📋 コピー</button>
  </div>
  <script>
    function copyUrl() {
      const input = document.getElementById("shareUrl");
      input.select();
      input.setSelectionRange(0, 99999);
      document.execCommand("copy");
      alert("URLをコピーしました！");
    }
  </script>
{% endif %}

<!-- 📊 結果表示 -->
{% if results %}
  <label>📈 表示形式:</label>
  <select id="chartTypeSelect">
    <option value="bar">棒グラフ</option>
    <option value="line">折れ線グラフ</option>
    <option value="radar">レーダーチャート</option>
  </select>

  <table>
    <thead>
      <tr>
        <th>比較対象</th>
        <th>平均勝率（%）</th>
        <th>平均DD（%）</th>
        <th>件数</th>
      </tr>
    </thead>
    <tbody>
      {% for row in results %}
        <tr>
          <td>
            <a href="/statistics/detail?mode={{ mode }}&key={{ row.key | urlencode }}&sort_by=date&order=desc">
              {{ row.key }}
            </a>
          </td>
          <td>{{ row.avg_win }}</td>
          <td>{{ row.avg_dd }}</td>
          <td>{{ row.count }}</td>
        </tr>
      {% endfor %}
    </tbody>
  </table>

  <!-- 📈 グラフ表示 -->
  <canvas id="winChart" height="100"></canvas>
  <canvas id="ddChart" height="100"></canvas>

  <script>
    const labels = {{ results | map(attribute='key') | list | tojson }};
    const winRates = {{ results | map(attribute='avg_win') | list | tojson }};
    const ddRates = {{ results | map(attribute='avg_dd') | list | tojson }};
    let winChartInstance, ddChartInstance;

    function renderCharts(type) {
      if (winChartInstance) winChartInstance.destroy();
      if (ddChartInstance) ddChartInstance.destroy();

      winChartInstance = new Chart(document.getElementById('winChart'), {
        type,
        data: {
          labels,
          datasets: [{ label: '平均勝率（%）', data: winRates, backgroundColor: 'rgba(54, 162, 235, 0.7)', borderColor: 'rgba(54, 162, 235, 1)', fill: type !== 'line', tension: 0.2 }]
        },
        options: { responsive: true, scales: type !== 'radar' ? { y: { beginAtZero: true } } : {} }
      });

      ddChartInstance = new Chart(document.getElementById('ddChart'), {
        type,
        data: {
          labels,
          datasets: [{ label: '平均DD（%）', data: ddRates, backgroundColor: 'rgba(255, 99, 132, 0.7)', borderColor: 'rgba(255, 99, 132, 1)', fill: type !== 'line', tension: 0.2 }]
        },
        options: { responsive: true, scales: type !== 'radar' ? { y: { beginAtZero: true } } : {} }
      });
    }

    renderCharts("bar");
    document.getElementById("chartTypeSelect").addEventListener("change", e => renderCharts(e.target.value));

    function selectAll(flag) {
      document.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = flag);
      updateCount();
    }
    function updateCount() {
      const count = [...document.querySelectorAll('input[type="checkbox"]')].filter(cb => cb.checked).length;
      document.getElementById("selectedCount").textContent = count;
    }
    window.onload = updateCount;
  </script>
{% else %}
  <p>⚠ 比較対象を選択してください。</p>
{% endif %}
{% endblock %}
