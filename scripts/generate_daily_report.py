#!/usr/bin/env python3
# coding: utf-8
"""
Noctria 王国・日次業務レポート自動生成（ノーコード強化版・ハイブリッド書式）
- Postgres の obs_codex_kpi / obs_codex_kpi_latest から KPI を取得
- 最新 run の reliability.png を埋め込み（存在チェック付き）
- YAML フロントマター + Markdown 本文（ハイブリッド書式）で docs/reports/daily/YYYY-MM-DD.md を生成
- 直近N runのサマリ、トレンド矢印、翌日の引継ぎYAML、実行コマンド例 などを自動出力

要件:
  - 環境変数 NOCTRIA_OBS_PG_DSN に Postgres DSN を設定
  - 事前に plot_reliability.py を実行して最新 run の reliability.png を生成しておくと画像が埋まる

使い方（例）:
  PYTHONPATH=. ./scripts/generate_daily_report.py --runs 5
  PYTHONPATH=. ./scripts/generate_daily_report.py --dry-run
  PYTHONPATH=. ./scripts/generate_daily_report.py --date 2025-09-27
  PYTHONPATH=. ./scripts/generate_daily_report.py --runs 5 --target-brier-max 0.18 --target-ece-max 0.35 --target-adv-min 0.40
"""

from __future__ import annotations
import os
import sys
import argparse
import datetime as dt
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import psycopg2

DSN = os.getenv("NOCTRIA_OBS_PG_DSN", "postgresql://noctria:noctria@127.0.0.1:5432/noctria_db")

DAILY_DIR = Path("docs/reports/daily")
REPORTS_BASE = Path("reports") / "veritas"


# ---------- SQL ----------
SQL_PIVOT = """
SELECT
  run_id,
  round(MAX(CASE WHEN metric='brier_score' THEN value END)::numeric,4)  AS brier,
  round(MAX(CASE WHEN metric='ece_calibration' THEN value END)::numeric,4) AS ece,
  round(MAX(CASE WHEN metric='adversarial_pass_rate' THEN value END)::numeric,3) AS adv_pass,
  MAX(meta->'calibration'->>'objective')     AS obj,
  MAX(meta->'calibration'->>'temperature')   AS T,
  MAX(meta->'calibration'->>'bins')          AS bins,
  MAX(created_at)                             AS updated_at
FROM obs_codex_kpi_latest
GROUP BY run_id
ORDER BY updated_at DESC
LIMIT %s;
"""

# フォールバック（ビュー未作成でも動くように）
SQL_FALLBACK = """
WITH ranked AS (
  SELECT
    agent, metric, value, created_at, meta,
    (meta->>'run_id') AS run_id,
    ROW_NUMBER() OVER (PARTITION BY agent, (meta->>'run_id'), metric ORDER BY created_at DESC) AS rn
  FROM obs_codex_kpi
  WHERE agent = 'Prometheus' AND meta ? 'run_id'
),
latest AS (
  SELECT agent, run_id, metric, value, created_at, meta
  FROM ranked
  WHERE rn = 1
)
SELECT
  run_id,
  round(MAX(CASE WHEN metric='brier_score' THEN value END)::numeric,4)  AS brier,
  round(MAX(CASE WHEN metric='ece_calibration' THEN value END)::numeric,4) AS ece,
  round(MAX(CASE WHEN metric='adversarial_pass_rate' THEN value END)::numeric,3) AS adv_pass,
  MAX(meta->'calibration'->>'objective')     AS obj,
  MAX(meta->'calibration'->>'temperature')   AS T,
  MAX(meta->'calibration'->>'bins')          AS bins,
  MAX(created_at)                             AS updated_at
FROM latest
GROUP BY run_id
ORDER BY updated_at DESC
LIMIT %s;
"""


# ---------- helpers ----------
def fmt_dt(x: Any) -> str:
    try:
        return dt.datetime.fromisoformat(str(x)).isoformat()
    except Exception:
        return str(x)


def arrow_and_delta(
    curr: Optional[float], prev: Optional[float], lower_is_better: bool
) -> Tuple[str, str]:
    """
    直近との差分を矢印と差分文字列で返す。
    lower_is_better: True のとき値が下がれば「↑（良化）」ではなく「↓（良化）」にしたい…が
    ユーザの自然感覚に合わせて↓/↑は “数値の増減” を素直に表し、(±delta) のみを表示。
    ここでは矢印は 増=↑, 減=↓, 変化なし=→ とする。
    """
    if curr is None or prev is None:
        return "→", ""
    delta = round(curr - prev, 4)
    if delta > 0:
        return "↑", f"(+{delta:.4f})"
    elif delta < 0:
        return "↓", f"({delta:.4f})"
    else:
        return "→", "(+0.0000)"


def reliability_path(run_id: str) -> Path:
    return REPORTS_BASE / run_id / "reliability.png"


def file_exists(p: Path) -> bool:
    try:
        return p.exists()
    except Exception:
        return False


def to_md_table_row_latest(latest: Dict[str, Any], prev: Optional[Dict[str, Any]]) -> str:
    brier = latest.get("brier")
    ece = latest.get("ece")
    adv = latest.get("adv_pass")
    T = latest.get("T") or "—"
    bins = latest.get("bins") or "—"

    # 前 run と比較して矢印・差分
    br_arrow, br_delta = arrow_and_delta(
        brier, prev.get("brier") if prev else None, lower_is_better=True
    )
    ece_arrow, ece_delta = arrow_and_delta(
        ece, prev.get("ece") if prev else None, lower_is_better=True
    )
    adv_arrow, adv_delta = arrow_and_delta(
        adv, prev.get("adv_pass") if prev else None, lower_is_better=False
    )

    return (
        f"| `{latest['run_id']}` | "
        f"{brier if brier is not None else '—':>6} | {br_arrow} {br_delta} | "
        f"{ece   if ece   is not None else '—':>6} | {ece_arrow} {ece_delta} | "
        f"{adv   if adv   is not None else '—':>6} | {adv_arrow} {adv_delta} | "
        f"{latest.get('obj') or '—'} | {T} | {bins} | {fmt_dt(latest.get('updated_at'))} |"
    )


def kpi_judgement_line(
    brier: Optional[float],
    ece: Optional[float],
    adv: Optional[float],
    tgt_brier_max: float,
    tgt_ece_max: float,
    tgt_adv_min: float,
) -> str:
    def mark(val: Optional[float], ok: bool, label: str) -> str:
        if val is None:
            return f"{label}=— → ❔"
        return (
            f"{label}={val:.4f}"
            if label != "Adv.Pass"
            else f"{label}={val:.3f}" + (" → ✅" if ok else " → ❌")
        )

    ok_brier = (brier is not None) and (brier <= tgt_brier_max)
    ok_ece = (ece is not None) and (ece <= tgt_ece_max)
    ok_adv = (adv is not None) and (adv >= tgt_adv_min)

    parts = [
        mark(brier, ok_brier, "Brier"),
        mark(ece, ok_ece, "ECE"),
        mark(adv, ok_adv, "Adv.Pass"),
    ]
    return "本日の判定: " + " / ".join(parts)


def fetch_runs(limit: int) -> List[Dict[str, Any]]:
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        try:
            cur.execute(SQL_PIVOT, (limit,))
        except Exception:
            # ビューがまだ無い場合のフォールバック
            cur.execute(SQL_FALLBACK, (limit,))
        rows = cur.fetchall()
        cols = [d.name for d in cur.description]
    runs: List[Dict[str, Any]] = [dict(zip(cols, r)) for r in rows]
    return runs


def build_yaml_frontmatter(
    date_str: str, latest: Optional[Dict[str, Any]], targets: Dict[str, float]
) -> str:
    run_id = latest["run_id"] if latest else ""
    rel = reliability_path(run_id) if run_id else None
    rel_str = str(rel).replace("\\", "/") if (rel and file_exists(rel)) else ""

    fm = []
    fm.append("---")
    fm.append("report_type: daily")
    fm.append(f'date_utc: "{date_str}"')
    fm.append(f'latest_run: "{run_id}"')
    fm.append("kpi_targets:")
    fm.append(f"  brier_max: {targets['brier_max']}")
    fm.append(f"  ece_max: {targets['ece_max']}")
    fm.append(f"  adv_pass_min: {targets['adv_min']}")
    fm.append("data_sources:")
    fm.append("  - postgres: obs_codex_kpi_latest")
    if rel_str:
        fm.append("artifacts:")
        fm.append(f'  reliability_plot: "{rel_str}"')
    fm.append("---")
    return "\n".join(fm)


def build_markdown(date_str: str, runs: List[Dict[str, Any]], targets: Dict[str, float]) -> str:
    latest = runs[0] if runs else None
    prev = runs[1] if len(runs) >= 2 else None

    # 1) YAML front matter
    parts = [build_yaml_frontmatter(date_str, latest, targets), ""]

    # 2) 見出し
    parts.append(f"# Noctria 王国・日次業務レポート — {date_str}\n")
    parts.append("**王の訓示**: 本日のKPIを確認し、明日の改善点を明確化せよ。\n")

    # 3) 本日のKPIレビュー
    parts.append("## 1) 本日のKPIレビュー（最新 run）\n")
    parts.append(
        "| run_id | Brier | trend | ECE | trend | Adv.Pass | trend | objective | T | bins | updated_at |"
    )
    parts.append("|---|---:|:---:|---:|:---:|---:|:---:|:--|--:|--:|:--|")
    if latest:
        parts.append(to_md_table_row_latest(latest, prev))
        # 判定ライン
        parts.append("")
        parts.append(
            kpi_judgement_line(
                latest.get("brier"),
                latest.get("ece"),
                latest.get("adv_pass"),
                targets["brier_max"],
                targets["ece_max"],
                targets["adv_min"],
            )
        )
        parts.append("")
        # reliability plot があれば表示
        img_path = reliability_path(latest["run_id"])
        if file_exists(img_path):
            parts.append(f"![Reliability Curve](/{img_path.as_posix()})\n")
        else:
            parts.append(
                "> 注記: reliability.png が見つかりません。`plot_reliability.py` の実行を確認してください。\n"
            )
    else:
        parts.append("| — | — | → | — | → | — | → | — | — | — | — |")
        parts.append("")
        parts.append(
            "> 注記: KPI データが取得できませんでした。データ連携/DSN/テーブルを確認してください。\n"
        )

    # 4) 直近ラン一覧
    parts.append("## 2) 直近ラン一覧\n")
    parts.append("| updated_at | run_id | Brier | ECE | Adv.Pass | obj | T | bins |")
    parts.append("|--|--|--:|--:|--:|:--|--:|--:|")
    for r in runs:
        parts.append(
            f"| {fmt_dt(r['updated_at'])} | `{r['run_id']}` | "
            f"{r['brier'] if r['brier'] is not None else '—'} | "
            f"{r['ece'] if r['ece'] is not None else '—'} | "
            f"{r['adv_pass'] if r['adv_pass'] is not None else '—'} | "
            f"{r.get('obj') or '—'} | {r.get('T') or '—'} | {r.get('bins') or '—'} |"
        )
    parts.append("")

    # 5) 週次の伏線（直近3点の暫定トレンド）
    parts.append("## 3) 今週の暫定トレンド（直近3点）\n")
    last3 = runs[:3]
    if last3:
        brier_seq = " → ".join(
            f"{x['brier']:.4f}" if x["brier"] is not None else "—" for x in last3[::-1]
        )
        ece_seq = " → ".join(
            f"{x['ece']:.4f}" if x["ece"] is not None else "—" for x in last3[::-1]
        )
        parts.append(f"- Brier: {brier_seq}")
        parts.append(f"- ECE:   {ece_seq}\n")
    else:
        parts.append("- （データ不足）\n")

    # 6) 翌日の引継ぎ（王の作戦） — YAMLブロック
    parts.append("## 4) 翌日の引継ぎ指示（王の作戦）\n")
    latest_run_id = latest["run_id"] if latest else ""
    parts.append("```yaml")
    parts.append("handover:")
    parts.append(f"  date: {date_str}")
    parts.append(f"  latest_run: {latest_run_id}")
    parts.append("  priorities:")
    parts.append("    - id: CAL-01")
    parts.append('      name: "信頼度曲線（ECE）を目標内に再収束"')
    parts.append('      why: "過学習抑制とポジションサイズ最適化の精度向上"')
    parts.append("      actions:")
    parts.append('        - "温度スケーリングのTレンジをサンプル数に応じて自動調整"')
    parts.append('        - "bin=12,15 の比較検証（安定性 vs 粒度）"')
    parts.append("      success_criteria:")
    parts.append(f"        - \"ECE <= {targets['ece_max']:.2f}\"")
    parts.append("    - id: ROBUST-01")
    parts.append('      name: "逆境耐性維持・改善"')
    parts.append("      actions:")
    parts.append('        - "ノイズ注入/時系列シフト/レジームドリフトに対する頑強性テストの強化"')
    parts.append("      success_criteria:")
    parts.append(f"        - \"adversarial_pass_rate >= {targets['adv_min']:.2f}\"")
    parts.append("  checkpoints:")
    parts.append('    - "obs_codex_kpi_latest ビューで run ごとのKPIを再確認"')
    parts.append('    - "Prometheus エージェントの設定（T, bins, objective）を記録"')
    parts.append("  blockers:")
    parts.append('    - "サンプル不足による温度推定の不安定化"')
    parts.append("  tomorrow_tasks:")
    parts.append('    - "09:30 UTC: evaluate_veritas.py を --calibrate-temperature で実行"')
    parts.append('    - "09:35 UTC: log_kpi_from_reports.py でKPI記録（--limit 1）"')
    parts.append('    - "09:40 UTC: plot_reliability.py で reliability.png を更新"')
    parts.append("```")
    parts.append("")

    # 7) 明日の実行コマンド例
    parts.append("## 5) 明日の実行コマンド例\n")
    parts.append("```bash")
    parts.append(
        "PYTHONPATH=. python src/veritas/evaluate_veritas.py --calibrate-temperature --calib-objective both --calib-bins 12"
    )
    parts.append("PYTHONPATH=. ./scripts/log_kpi_from_reports.py --limit 1")
    parts.append(
        "PYTHONPATH=. python scripts/plot_reliability.py --reports reports/veritas --limit 1"
    )
    parts.append("```")
    parts.append("")

    # 8) ガード/注意
    parts.append("## 6) 注意・ガード\n")
    if latest:
        img_path = reliability_path(latest["run_id"])
        if not file_exists(img_path):
            parts.append(
                "- アーティファクト未生成: reliability.png が存在しません（プロットスクリプトの実行を確認）"
            )
    else:
        parts.append("- KPI 取得に失敗: DSN/テーブル/ビューの整合を確認")
    parts.append("")

    # 9) 訓示
    parts.append("> 訓示: 『数の知恵を集めよ、勝利の礎となすべし』\n")

    return "\n".join(parts)


def resolve_report_path(date_arg: Optional[str]) -> Tuple[str, Path]:
    if date_arg:
        date_str = dt.date.fromisoformat(date_arg).isoformat()
    else:
        date_str = dt.datetime.utcnow().date().isoformat()
    out_path = DAILY_DIR / f"{date_str}.md"
    return date_str, out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5, help="直近何 run を列挙するか（デフォルト: 5）")
    ap.add_argument(
        "--date", type=str, default=None, help="レポートの日付（YYYY-MM-DD, 省略時はUTC今日）"
    )
    ap.add_argument("--dry-run", action="store_true", help="ファイルに保存せず標準出力に表示")
    ap.add_argument("--target-brier-max", type=float, default=0.18)
    ap.add_argument("--target-ece-max", type=float, default=0.35)
    ap.add_argument("--target-adv-min", type=float, default=0.40)
    args = ap.parse_args()

    # 取得
    try:
        runs = fetch_runs(max(1, int(args.runs)))
    except Exception as e:
        print(f"[report] ERROR: failed to fetch KPI from DB: {e}", file=sys.stderr)
        runs = []

    targets = {
        "brier_max": float(args.target_brier_max),
        "ece_max": float(args.target_ece_max),
        "adv_min": float(args.target_adv_min),
    }

    date_str, out_path = resolve_report_path(args.date)
    md = build_markdown(date_str, runs, targets)

    if args.dry_run:
        print(md)
        return 0

    # 保存
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md, encoding="utf-8")
        print(f"[report] saved {out_path.as_posix()}")
    except Exception as e:
        print(f"[report] ERROR: failed to save report: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
