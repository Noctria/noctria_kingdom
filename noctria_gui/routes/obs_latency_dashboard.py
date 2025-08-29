# noctria_gui/routes/obs_latency_dashboard.py
from __future__ import annotations

import os
import contextlib
from typing import Any, Dict, List, Tuple

from flask import Blueprint, current_app, jsonify, make_response, render_template_string

try:
    import psycopg2  # type: ignore
    import psycopg2.extras  # type: ignore
except Exception as e:  # pragma: no cover
    psycopg2 = None  # type: ignore

bp_obs_latency = Blueprint("obs_latency", __name__)

# ------------------------------
# DB helpers
# ------------------------------
def _dsn() -> str:
    # 既定は Airflow 用と同じ
    return os.getenv(
        "NOCTRIA_OBS_PG_DSN",
        os.getenv("PSQL_DSN", "postgresql://airflow:airflow@localhost:5432/airflow"),
    )

@contextlib.contextmanager
def _pg():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 が見つかりません。`pip install psycopg2-binary` を実行してください。")
    conn = psycopg2.connect(_dsn())
    try:
        yield conn
    finally:
        with contextlib.suppress(Exception):
            conn.close()

def _q(sql: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    with _pg() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]

# ------------------------------
# Queries
# ------------------------------
SQL_DAILY = """
SELECT
  day::date,
  events,
  ROUND(p50_ms)::int AS p50_ms,
  ROUND(p90_ms)::int AS p90_ms,
  ROUND(p99_ms)::int AS p99_ms
FROM obs_latency_daily
ORDER BY day DESC
LIMIT 30;
"""

SQL_SUMMARY = """
SELECT
  trace_id,
  started_at,
  finished_at,
  ROUND(total_latency_ms)::int AS total_ms,
  COALESCE(infer_ms, 0) AS infer_ms,
  COALESCE(strategy_name,'') AS strategy_name,
  COALESCE(action,'') AS action,
  params,
  COALESCE(infer_to_decision_ms, NULL) AS infer_to_decision_ms,
  events
FROM obs_trace_summary
ORDER BY finished_at DESC
LIMIT 50;
"""

# ------------------------------
# Routes
# ------------------------------
@bp_obs_latency.route("/observability/latency.json", methods=["GET"])
def api_latency_json():
    try:
        daily = _q(SQL_DAILY)
        summary = _q(SQL_SUMMARY)
        return jsonify({"daily": daily, "summary": summary})
    except Exception as e:
        current_app.logger.exception("latency.json error")
        return make_response({"error": str(e)}, 500)

@bp_obs_latency.route("/observability/latency", methods=["GET"])
def page_latency():
    """
    単一ファイルで完結する埋め込みテンプレート。
    Chart.js(CDN) で p50/p90/p99 を折れ線表示、下に直近 trace サマリ表。
    """
    try:
        daily = _q(SQL_DAILY)
        summary = _q(SQL_SUMMARY)
    except Exception as e:
        current_app.logger.exception("latency page error")
        return make_response(f"<pre>DB error: {e}</pre>", 500)

    # 軽い整形
    labels = [str(r["day"]) for r in reversed(daily)]
    p50 = [r["p50_ms"] for r in reversed(daily)]
    p90 = [r["p90_ms"] for r in reversed(daily)]
    p99 = [r["p99_ms"] for r in reversed(daily)]

    html = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Noctria – Observability / Latency</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 16px; background:#0f1115; color:#eaeef7; }
    h1 { font-size: 20px; margin-bottom: 8px; }
    .card { background:#171923; border:1px solid #2a2f45; border-radius:12px; padding:16px; margin-bottom:16px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 8px; border-bottom: 1px solid #2a2f45; text-align: left; }
    th { color:#aab3d0; font-weight: 600; }
    .muted { color:#9aa3b2; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
    .grid { display:grid; grid-template-columns: 1fr; gap:16px; }
    @media (min-width: 1100px) { .grid { grid-template-columns: 1.2fr 1fr; } }
    .pill { display:inline-block; padding:2px 8px; border-radius:999px; background:#1f2437; color:#cfd7f7; font-size:12px; }
    .tag-ok { background:#16351e; color:#a8f0b3; }
    .tag-warn { background:#3b2d12; color:#ffd79a; }
    .tag-err { background:#3b1f1f; color:#ffb1b1; }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <h1>Observability / Latency</h1>
  <div class="grid">
    <div class="card">
      <div class="muted" style="margin-bottom:8px;">Daily next-event latency (p50 / p90 / p99)</div>
      <canvas id="latencyChart" height="140"></canvas>
    </div>
    <div class="card">
      <div class="muted" style="margin-bottom:8px;">Last 30 days (events / pXX ms)</div>
      <table>
        <thead>
          <tr><th>Day</th><th class="mono">events</th><th class="mono">p50</th><th class="mono">p90</th><th class="mono">p99</th></tr>
        </thead>
        <tbody>
          {% for r in daily %}
            <tr>
              <td>{{ r.day.strftime('%Y-%m-%d') if r.day.__class__.__name__ in ('datetime','date') else r.day }}</td>
              <td class="mono">{{ r.events }}</td>
              <td class="mono">{{ r.p50_ms }}</td>
              <td class="mono">{{ r.p90_ms }}</td>
              <td class="mono">{{ r.p99_ms }}</td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>

  <div class="card">
    <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
      <div class="muted">Recent trace summary</div>
      <span class="pill">latest {{ summary|length }}</span>
    </div>
    <table>
      <thead>
        <tr>
          <th>Finished</th>
          <th>Trace</th>
          <th>Strategy</th>
          <th>Action</th>
          <th class="mono">Total(ms)</th>
          <th class="mono">Infer(ms)</th>
          <th class="mono">Infer→Decision(ms)</th>
          <th class="mono">Events</th>
          <th>Params</th>
        </tr>
      </thead>
      <tbody>
        {% for s in summary %}
          <tr>
            <td class="mono">{{ s.finished_at }}</td>
            <td class="mono">{{ s.trace_id }}</td>
            <td>{{ s.strategy_name or '-' }}</td>
            <td>
              {% set tag = 'tag-ok' if s.action in ('scalp','range_trade','enter_trend') else 'tag-warn' %}
              <span class="pill {{ tag }}">{{ s.action or '-' }}</span>
            </td>
            <td class="mono">{{ s.total_ms }}</td>
            <td class="mono">{{ s.infer_ms }}</td>
            <td class="mono">{{ s.infer_to_decision_ms if s.infer_to_decision_ms is not none else '-' }}</td>
            <td class="mono">{{ s.events }}</td>
            <td class="mono">{{ s.params }}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

<script>
const labels = {{ labels|tojson }};
const p50 = {{ p50|tojson }};
const p90 = {{ p90|tojson }};
const p99 = {{ p99|tojson }};

const ctx = document.getElementById('latencyChart').getContext('2d');
new Chart(ctx, {
  type: 'line',
  data: {
    labels,
    datasets: [
      { label: 'p50 ms', data: p50, borderWidth: 2, tension: 0.3 },
      { label: 'p90 ms', data: p90, borderWidth: 2, tension: 0.3 },
      { label: 'p99 ms', data: p99, borderWidth: 2, tension: 0.3 },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: '#d7def7' } },
    },
    scales: {
      x: { ticks: { color: '#9aa3b2' }, grid: { color: '#1f2437' } },
      y: { ticks: { color: '#9aa3b2' }, grid: { color: '#1f2437' } },
    }
  }
});
</script>

</body>
</html>
    """

    return render_template_string(
        html,
        daily=daily,
        summary=summary,
        labels=labels,
        p50=p50,
        p90=p90,
        p99=p99,
    )
