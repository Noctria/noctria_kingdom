#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/generate_handoff.py

直近のコミットや進捗をまとめて handoff/ ディレクトリに Markdown(+JSON) を生成するスクリプト。
- --lookback-hours N : 直近N時間の更新を抽出（デフォルト24）
- --next-from FILE   : 次アクションを外部ファイル（.md/.txt）から読み込む（各行を1項目）
- --auto-complete-next: 次アクションの達成状況をリポジトリ状態から自動判定して [x] にする（ベースは --next-from / デフォルトリスト）
- --include-airflow  : Airflow scheduler コンテナ内の /opt/airflow/backtests を走査し、直近Runsの成果物状況を追記
- --airflow-container: （--include-airflow有効時）対象コンテナ名（デフォルト: noctria_airflow_scheduler）
- --max-runs         : （--include-airflow有効時）一覧に載せる最大件数（デフォルト: 5）
"""

from __future__ import annotations
from pathlib import Path
import argparse
import subprocess
import datetime as dt
import json
import os
import shlex
from typing import List, Dict, Tuple, Optional

ROOT = Path(__file__).resolve().parents[1]
HANDOFF_DIR = ROOT / "handoff"
HANDOFF_DIR.mkdir(exist_ok=True)


# ------------------------
# Shell helpers
# ------------------------
def run(cmd: str, *, cwd: Path | None = None, check: bool = True) -> str:
    if cwd is None:
        cwd = ROOT
    try:
        return subprocess.check_output(shlex.split(cmd), text=True, cwd=str(cwd)).strip()
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return e.output.strip() if e.output else ""


def command_exists(cmd: str) -> bool:
    """Return True if command exists on PATH."""
    try:
        subprocess.check_output(["bash", "-lc", f"command -v {shlex.quote(cmd)}"], text=True)
        return True
    except Exception:
        return False


# ------------------------
# Git
# ------------------------
def recent_commits(hours: int) -> List[Dict]:
    since = (dt.datetime.now() - dt.timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        # ハッシュ、サブジェクト、相対時刻、日時
        fmt = r"%h|%s|%cr|%cd"
        out = run(f'git log --since="{since}" --pretty=format:{fmt} --date=iso', check=False)
        lines = [ln for ln in out.splitlines() if ln.strip()]
    except Exception:
        lines = []
    commits = []
    for ln in lines:
        parts = ln.split("|", 3)
        if len(parts) == 4:
            h, subj, rel, ts = parts
            commits.append({"hash": h, "title": subj, "when": rel, "timestamp": ts})
    return commits


# ------------------------
# Next actions
# ------------------------
DEFAULT_NEXT_ACTIONS = [
    "DAG 本処理の組み込み",
    "戦略指定パラメータの対応",
    "結果の artifact / PR コメント出力",
]


def read_next_actions(path: str | None) -> List[str]:
    if not path:
        return list(DEFAULT_NEXT_ACTIONS)
    p = Path(path)
    if not p.exists():
        return [f"(next-from が見つかりません: {path})"]
    items: List[str] = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip("-• ").strip()
        if ln:
            items.append(ln)
    return items or ["(次アクションが空)"]


def file_contains(path: Path, needle: str) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        txt = path.read_text(encoding="utf-8", errors="ignore")
        return needle in txt
    except Exception:
        return False


def auto_complete_next(actions: List[str]) -> List[Tuple[str, bool]]:
    """
    簡易ヒューリスティックで完了判定。
    戻り値: [(action_text, done_bool), ...]
    """
    dag_path = ROOT / "airflow_docker" / "dags" / "noctria_backtest_dag.py"
    scripts_dir = ROOT / "scripts"
    repo_veritas = ROOT / "airflow_docker" / "scripts" / "veritas_local_test.py"
    repo_veritas_alt = ROOT / "scripts" / "veritas_local_test.py"  # 片方にあるケースも

    # 1) DAG 本処理の組み込み（render_report タスクが存在＆report.html を書いている）
    dag_has_render_task = file_contains(dag_path, "render_report") and file_contains(
        dag_path, "report.html"
    )

    # 2) 戦略指定パラメータの対応（DAG で NOCTRIA_STRATEGY_GLOB / NOCTRIA_EXTRA_ARGS を設定し実行へ渡す）
    dag_sets_env = file_contains(dag_path, "NOCTRIA_STRATEGY_GLOB") and file_contains(
        dag_path, "NOCTRIA_EXTRA_ARGS"
    )
    # 実スクリプト側が環境変数 or 引数を読む実装かは厳密にはソース依存。ここでは存在の痕跡だけ軽く見る
    script_consumes_env = any(
        [
            file_contains(repo_veritas, "NOCTRIA_STRATEGY_GLOB")
            or file_contains(repo_veritas, "NOCTRIA_EXTRA_ARGS"),
            file_contains(repo_veritas_alt, "NOCTRIA_STRATEGY_GLOB")
            or file_contains(repo_veritas_alt, "NOCTRIA_EXTRA_ARGS"),
            # もしくは scripts/backtest_runner.py が受け取っている
            file_contains(scripts_dir / "backtest_runner.py", "NOCTRIA_STRATEGY_GLOB")
            or file_contains(scripts_dir / "backtest_runner.py", "NOCTRIA_EXTRA_ARGS"),
        ]
    )
    strategy_params_ready = dag_sets_env and script_consumes_env

    # 3) 結果の artifact / PR コメント出力（GitHub Actions で artifact or コメント投稿）
    gh_wf_dir = ROOT / ".github" / "workflows"
    any_wf = list(gh_wf_dir.glob("*.yml")) + list(gh_wf_dir.glob("*.yaml"))
    artifact_or_comment = False
    for wf in any_wf:
        if (
            file_contains(wf, "upload-artifact")
            or file_contains(wf, "github-script")
            or file_contains(wf, "Create or update comment")
            or file_contains(wf, "issue_comment")
        ):
            artifact_or_comment = True
            break

    results: List[Tuple[str, bool]] = []
    for a in actions:
        done = False
        if "DAG 本処理" in a:
            done = dag_has_render_task
        elif "戦略指定" in a:
            done = strategy_params_ready
        elif "artifact" in a.lower() or "PR コメント" in a:
            done = artifact_or_comment
        results.append((a, done))
    return results


# ------------------------
# Airflow backtests (optional)
# ------------------------
def list_backtests_in_container(container: str, max_runs: int = 5) -> List[Dict]:
    """
    docker exec で /opt/airflow/backtests を覗く。
    返却: [{"run_id": ..., "has_conf": bool, "has_result": bool, "has_html": bool, "has_stdout": bool}, ...]
    新しい順のつもりで ls -1t を使用。
    """
    if not command_exists("docker"):
        return []
    try:
        base = "/opt/airflow/backtests"
        # 直近ディレクトリを新しい順に
        dirs = run(
            f'docker exec {shlex.quote(container)} bash -lc "ls -1t {base} 2>/dev/null | head -n {int(max_runs)}"',
            check=False,
        )
        run_ids = [d.strip() for d in dirs.splitlines() if d.strip()]
        results: List[Dict] = []
        for rid in run_ids:

            def exists(p: str) -> bool:
                code = subprocess.call(
                    ["docker", "exec", container, "bash", "-lc", f"test -f {shlex.quote(p)}"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return code == 0

            outdir = f"{base}/{rid}"
            results.append(
                {
                    "run_id": rid,
                    "has_conf": exists(f"{outdir}/conf.json"),
                    "has_result": exists(f"{outdir}/result.json"),
                    "has_html": exists(f"{outdir}/report.html"),
                    "has_stdout": exists(f"{outdir}/stdout.txt"),
                }
            )
        return results
    except Exception:
        return []


# ------------------------
# Main
# ------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lookback-hours", type=int, default=24)
    ap.add_argument("--next-from", type=str, default=None)
    ap.add_argument(
        "--auto-complete-next", action="store_true", help="次アクションを自動判定して [x] を付ける"
    )
    ap.add_argument(
        "--include-airflow", action="store_true", help="Airflow の backtests 一覧を付記する"
    )
    ap.add_argument("--airflow-container", type=str, default="noctria_airflow_scheduler")
    ap.add_argument("--max-runs", type=int, default=5)
    args = ap.parse_args()

    now = dt.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    date_tag = now.date().isoformat()

    md_path = HANDOFF_DIR / f"handoff_{date_tag}.md"
    json_path = HANDOFF_DIR / f"handoff_{date_tag}.json"

    commits = recent_commits(args.lookback_hours)
    base_actions = read_next_actions(args.next_from)

    # 自動判定でチェック状態を付ける
    if args.auto_complete_next:
        actions_with_state = auto_complete_next(base_actions)
    else:
        actions_with_state = [(a, False) for a in base_actions]

    # Airflow の backtests 一覧（任意）
    airflow_runs: List[Dict] = []
    if args.include_airflow:
        airflow_runs = list_backtests_in_container(args.airflow_container, args.max_runs)

    data = {
        "generated_at": now_str,
        "lookback_hours": args.lookback_hours,
        "commits": commits,
        "next_actions": [{"text": a, "done": d} for a, d in actions_with_state],
        "airflow_runs": airflow_runs,
    }

    # Markdown生成
    md: List[str] = []
    md.append(f"# 📝 引き継ぎレポート ({now_str})")
    md.append(f"_直近 **{args.lookback_hours}h** の更新を集計_\n")

    # Recent commits
    md.append("## ✅ 最近のコミット")
    if not commits:
        md.append("- （該当なし）")
    else:
        for c in commits:
            md.append(f"- {c['hash']} {c['title']} ({c['when']})")

    # Next actions
    md.append("\n## 🚩 次アクション")
    for a, done in actions_with_state:
        mark = "x" if done else " "
        md.append(f"- [{mark}] {a}")

    # Airflow runs (optional)
    if args.include_airflow:
        md.append("\n## 🧪 Airflow Backtests（直近）")
        if not airflow_runs:
            md.append("- （該当なし / もしくは docker 未検出）")
        else:
            for r in airflow_runs:
                flags = []
                flags.append("conf✅" if r.get("has_conf") else "conf—")
                flags.append("result✅" if r.get("has_result") else "result—")
                flags.append("html✅" if r.get("has_html") else "html—")
                flags.append("stdout✅" if r.get("has_stdout") else "stdout—")
                md.append(f"- `{r['run_id']}` : " + ", ".join(flags))

    # 機械可読（コメント貼付時も抽出できる）
    md.append("\n<!--HANDOFF_JSON")
    md.append(json.dumps(data, ensure_ascii=False))
    md.append("HANDOFF_JSON-->")

    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"✅ Handoff written:\n- {md_path}\n- {json_path}")


if __name__ == "__main__":
    main()
