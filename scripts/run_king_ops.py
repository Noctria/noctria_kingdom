#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [NOCTRIA_CORE_REQUIRED]
"""
run_king_ops.py — KingOps(王)を1回起動して「開発プロマネ計画」を生成・保存・台帳反映するCLI。

やること:
  1) 入力コンテキストの取得（--context / stdin / 既定テンプレ）
  2) king_ops_agent.run_once() を呼び、計画(JSON+Markdown)を runs/king_ops/ に保存
  3) Decision Registry に upsert（trace_idキー）
  4) 三行要約の保存 (scripts/summarize_to_pdca.py) と台帳ひも付け (scripts/link_summary_to_decision.py)

環境変数（例）:
  OPENAI_API_KEY          : APIキー
  OPENAI_API_BASE         : OpenAI互換のBase URL（または OPENAI_BASE_URL）
  NOCTRIA_GPT_MODEL       : 既定モデル名（例: gpt-4o-mini / llama3.1:8b-instruct-q4_K_M など）
  DECISION_REGISTRY_CSV   : CSV台帳のパス（モジュールAPIが無いときのフォールバック）

使い方:
  # 標準: 既定コンテキストで1回実行
  scripts/run_king_ops.py

  # テキストファイルをコンテキストに
  scripts/run_king_ops.py --context docs/handoff/handoff_latest.md

  # 標準入力で渡す
  cat docs/handoff/handoff_latest.md | scripts/run_king_ops.py -

出力:
  runs/king_ops/king_ops_<timestamp>.json
  runs/king_ops/king_ops_<timestamp>.md
  （三行要約は pdca_log.db に保存、Decision Registry に summary_* がupsert）
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# プロジェクトルート
ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "runs" / "king_ops"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

# モジュール本体
sys.path.insert(0, str(ROOT / "src"))
from king.king_ops_agent import run_once  # type: ignore


def _read_context(path_or_dash: Optional[str]) -> str:
    if not path_or_dash or path_or_dash == "-":
        data = sys.stdin.read()
        if data.strip():
            return data
        # 既定テンプレ（ハンドオフが無いとき用）
        return (
            "【入力が空のため既定テンプレ】\n"
            "・直近の課題: テスト安定化 / 決定台帳の一元化 / DAG整備\n"
            "・制約: GPUコスト抑制、CIは10分以内、平日日中のみデプロイ\n"
            "・希望: 王が日々の情報を三行で掴み、優先タスクが自動提示されること\n"
        )
    p = Path(path_or_dash).expanduser().resolve()
    return p.read_text(encoding="utf-8", errors="replace")


def _save_outputs(trace_id: str, plan: dict, md_text: str) -> Path:
    ts = dt.datetime.now(dt.UTC).strftime("%Y%m%d_%H%M%S")
    stem = f"king_ops_{ts}"
    jpath = RUNS_DIR / f"{stem}.json"
    mpath = RUNS_DIR / f"{stem}.md"
    jpath.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    mpath.write_text(md_text, encoding="utf-8")
    print(f"[OK] saved plan:\n  JSON: {jpath}\n  MD  : {mpath}")
    return mpath


def _which(path: Path) -> bool:
    return path.exists() and os.access(path, os.X_OK)


def _upsert_registry(trace_id: str, summary_lines: list[str], model_tag: str) -> None:
    """
    Decision Registry upsert:
      1) src.core.decision_registry に upsert_fields があればそれを使用
      2) なければ CSV 直接更新（scripts/link_summary_to_decision.py を利用）
    """
    try:
        from src.core import decision_registry as dr  # type: ignore
        if hasattr(dr, "upsert_fields") and callable(dr.upsert_fields):
            dr.upsert_fields(trace_id, {
                "summary_line1": summary_lines[0],
                "summary_line2": summary_lines[1],
                "summary_line3": summary_lines[2],
                "summary_model": model_tag,
            })
            print("[OK] Decision Registry upsert via module API")
            return
    except Exception as e:
        print(f"[WARN] module API not available or failed: {e}")

    # CSV版（フォールバック）
    csv_path = os.getenv("DECISION_REGISTRY_CSV", "docs/operations/PDCA/decision_registry.csv")
    linker = ROOT / "scripts" / "link_summary_to_decision.py"
    if _which(linker):
        cmd = [
            sys.executable, str(linker),
            "--trace-id", trace_id,
            "--registry-csv", str(Path(csv_path))
        ]
        print("[RUN]", " ".join(cmd))
        subprocess.run(cmd, check=False)
    else:
        print(f"[WARN] {linker} が見つからず、CSVへの反映をスキップしました。")


def _summarize_and_store(trace_id: str, md_path: Path, model_tag: str) -> list[str]:
    """
    scripts/summarize_to_pdca.py を呼び、三行要約を pdca_log.db に保存。
    戻り値: ["…","…","…"]
    """
    summ = ROOT / "scripts" / "summarize_to_pdca.py"
    if not _which(summ):
        print(f"[WARN] summarizer not found: {summ} — 三行要約をスキップ")
        return []

    env = os.environ.copy()
    if model_tag:
        env["NOCTRIA_SUMMARY_MODEL"] = model_tag

    cmd = [sys.executable, str(summ), "--trace-id", trace_id, str(md_path)]
    print("[RUN]", " ".join(cmd))
    proc = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        print("[WARN] summarize_to_pdca failed:", proc.stderr[:2000])
        return []
    try:
        arr = json.loads(proc.stdout.strip())
        if isinstance(arr, list) and len(arr) == 3 and all(isinstance(x, str) for x in arr):
            print("[OK] 三行要約を保存しました。")
            return arr
    except Exception as e:
        print("[WARN] JSON parse error:", e)
    return []


def main():
    ap = argparse.ArgumentParser(description="Run KingOps once to generate PM plan and persist artifacts.")
    ap.add_argument("context", nargs="?", default="-", help="Context path or '-' for stdin")
    ap.add_argument("--trace-id", default=None, help="指定が無ければ自動生成")
    ap.add_argument("--model", default=os.getenv("NOCTRIA_GPT_MODEL", ""), help="LLM model tag (optional)")
    args = ap.parse_args()

    # 1) 入力コンテキスト
    context = _read_context(args.context)

    # 2) 実行
    result = run_once(context=context, model_hint=args.model, trace_id=args.trace_id)
    trace_id = result["trace_id"]
    plan_json = result["plan"]
    md_text = result["markdown"]

    # 3) 保存
    md_path = _save_outputs(trace_id, plan_json, md_text)

    # 4) 三行要約 → SQLite保存
    summary3 = _summarize_and_store(trace_id, md_path, model_tag=args.model or plan_json.get("model", ""))

    # 5) 台帳 upsert（summary_* も反映）
    if summary3:
        _upsert_registry(trace_id, summary3, model_tag=args.model or plan_json.get("model", ""))

    print(f"[DONE] trace_id={trace_id}")


if __name__ == "__main__":
    main()
