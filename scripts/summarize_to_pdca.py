#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [NOCTRIA_CORE_REQUIRED]
"""
scripts/summarize_to_pdca.py

三行要約 (summarize3.sh) を呼び出して JSON 取得し、
PDCAログ(SQLite) と runs/metrics.csv に保存する統合スクリプト。

使い方:
  # 単一ファイルを要約して PDCA ログへ保存
  scripts/summarize_to_pdca.py /path/to/body.txt

  # trace_id付与＋モデル名タグ付け＋DBパス指定
  scripts/summarize_to_pdca.py \
      --trace-id 2025-10-02T23:59:59Z-abc123 \
      --model gpt-4o-mini \
      --sqlite pdca_log.db \
      /path/to/body.txt

  # 入力がSTDINのとき（- または引数省略）
  cat /path/to/body.txt | scripts/summarize_to_pdca.py -

出力:
  - 標準出力: 生成された要約(JSON配列: ["…","…","…"])
  - SQLite: pdca_summaries テーブルへ1レコード挿入
  - CSV: runs/metrics.csv に1行追記
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import re
from pathlib import Path
from typing import List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE = ROOT / "pdca_log.db"
RUNS_DIR = ROOT / "runs"
METRICS_CSV = RUNS_DIR / "metrics.csv"
SUMMARIZER = ROOT / "scripts" / "summarize3.sh"

# 言語検出: ハングル混入をNGとみなす（必要なら英字も制限可能）
_RE_HANGUL = re.compile(r"[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7AF]")
# _RE_LATIN  = re.compile(r"[A-Za-z]")  # 英字も禁止する場合は有効化


def _lang_is_japanese(arr: List[str]) -> bool:
    if any(_RE_HANGUL.search(s) for s in arr):
        return False
    # 英字もNGにする場合はコメントアウトを外す
    # if any(_RE_LATIN.search(s) for s in arr):
    #     return False
    return True


def _read_all_bytes(fp: Optional[Path]) -> bytes:
    if fp is None:
        data = sys.stdin.buffer.read()
        return data
    return fp.read_bytes()


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _ensure_runs():
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_sqlite_schema(sqlite_path: Path):
    conn = sqlite3.connect(sqlite_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pdca_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                trace_id TEXT,
                source_path TEXT,
                source_sha256 TEXT,
                line_count INTEGER,
                bytes INTEGER,
                model_used TEXT,
                summary_json TEXT NOT NULL,
                summary_text TEXT NOT NULL,
                metrics_json TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _run_summarizer_json(
    *,
    summarizer: Path,
    body_path: Optional[Path],
    raw_bytes: Optional[bytes],
    env_extra: Optional[dict] = None,
) -> List[str]:
    """
    summarize3.sh --format=json を実行し、三行の配列を返す。
    body_path が None の場合は raw_bytes が必須。
    """
    if not summarizer.exists():
        raise FileNotFoundError(f"summarizer not found: {summarizer}")

    run_env = os.environ.copy()
    if env_extra:
        run_env.update(env_extra)

    cmd = [str(summarizer), "--format=json"]
    if body_path is None:
        if raw_bytes is None:
            raise ValueError("raw_bytes is required when body_path is None")
        proc = subprocess.run(
            cmd,
            input=raw_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=run_env,
        )
    else:
        cmd.append(str(body_path))
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=run_env,
        )

    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="ignore")
        raise RuntimeError(f"summarizer failed (exit={proc.returncode}): {err}")

    out = proc.stdout.decode("utf-8", errors="replace").strip()
    try:
        arr = json.loads(out)
        if not (isinstance(arr, list) and len(arr) == 3 and all(isinstance(x, str) for x in arr)):
            raise ValueError("summarizer output must be a JSON array of 3 strings")
        return arr
    except Exception as e:
        raise RuntimeError(f"Invalid JSON from summarizer: {e}\nRaw: {out[:500]}")


def _call_summarizer(body_path: Optional[Path], summarizer: Path) -> Tuple[List[str], str]:
    """
    互換用（ファイルありの単純呼び出し）。現状は未使用パスだが保持。
    """
    arr = _run_summarizer_json(summarizer=summarizer, body_path=body_path, raw_bytes=None)
    raw_text = "\n".join(arr) + "\n"
    return arr, raw_text


def _append_metrics_row(
    metrics_csv: Path,
    *,
    ts: str,
    source_path: str,
    model_used: str,
    ok_three_lines: int,
    max_line_len: int,
    ended_with_maru: int,
    ascii_autoconverted: int,
    chars_total: int,
):
    header = [
        "timestamp",
        "source_path",
        "model_used",
        "ok_three_lines",
        "max_line_len",
        "ended_with_maru",
        "ascii_autoconverted",
        "chars_total",
    ]
    line = [
        ts,
        source_path,
        model_used,
        str(ok_three_lines),
        str(max_line_len),
        str(ended_with_maru),
        str(ascii_autoconverted),
        str(chars_total),
    ]
    write_header = not metrics_csv.exists()
    with metrics_csv.open("a", encoding="utf-8") as f:
        if write_header:
            f.write(",".join(header) + "\n")
        f.write(",".join(line) + "\n")


def _detect_model_tag() -> str:
    # summarizer 側で実際に使ったモデルは metrics に書かれているはずだが、
    # ここでは環境変数やヒントから推定（明示指定が最優先）。
    return os.getenv("NOCTRIA_SUMMARY_MODEL") or ""


def _validate_three_lines(arr: List[str]) -> Tuple[int, int, int, int, int]:
    """
    summarize3.sh 側でも検証済みだが、念のため簡易検証値をメトリクス化。
    returns: (ok_three, max_len, ended_with_maru, ascii_auto, chars_total)
    ※ ascii_auto はここでは未知（summarizer 内処理のため）。-1をセット。
    """
    ok_three = 1 if len(arr) == 3 else 0
    max_len = max(len(s) for s in arr) if arr else 0
    ended_maru = 1 if all(s.endswith("。") for s in arr) else 0
    ascii_auto = -1
    chars_total = sum(len(s) for s in arr)
    return ok_three, max_len, ended_maru, ascii_auto, chars_total


def _insert_sqlite(
    sqlite_path: Path,
    *,
    trace_id: Optional[str],
    source_path: Optional[str],
    source_sha: str,
    line_count: int,
    nbytes: int,
    model_used: str,
    summary_arr: List[str],
    summary_text: str,
    metrics: dict,
):
    conn = sqlite3.connect(sqlite_path)
    try:
        conn.execute(
            """
            INSERT INTO pdca_summaries (
                trace_id, source_path, source_sha256, line_count, bytes,
                model_used, summary_json, summary_text, metrics_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trace_id,
                source_path,
                source_sha,
                line_count,
                nbytes,
                model_used,
                json.dumps(summary_arr, ensure_ascii=False),
                summary_text,
                json.dumps(metrics, ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def main():
    p = argparse.ArgumentParser(description="Summarize text into PDCA SQLite and metrics CSV.")
    p.add_argument("input", nargs="?", default="-", help="Input file path or '-' for stdin")
    p.add_argument(
        "--sqlite", default=str(DEFAULT_SQLITE), help="Path to SQLite DB (default: pdca_log.db)"
    )
    p.add_argument("--trace-id", default=None, help="Optional trace_id to record")
    p.add_argument("--model", default=None, help="Model name tag to record (for metrics/log)")
    p.add_argument("--summarizer", default=str(SUMMARIZER), help="Path to scripts/summarize3.sh")
    args = p.parse_args()

    input_arg = args.input
    body_path: Optional[Path]
    if input_arg == "-" or (isinstance(input_arg, str) and input_arg.strip() == ""):
        body_path = None
    else:
        body_path = Path(input_arg).resolve()
        if not body_path.exists():
            print(f"Input file not found: {body_path}", file=sys.stderr)
            sys.exit(2)

    # 入力本文を読み、メタ情報を算出
    raw_bytes = _read_all_bytes(body_path)
    source_sha = _sha256(raw_bytes)
    line_count = raw_bytes.decode("utf-8", errors="replace").count("\n") + 1
    nbytes = len(raw_bytes)

    summarizer = Path(args.summarizer)

    # --- 要約実行（最大2回: 日本語チェックNGなら SUMMARY_LANG=ja を付けて再試行） ---
    try:
        arr = _run_summarizer_json(
            summarizer=summarizer,
            body_path=body_path,
            raw_bytes=None if body_path is not None else raw_bytes,
        )
    except Exception as e:
        print(f"summarizer failed: {e}", file=sys.stderr)
        sys.exit(3)

    # 言語チェック。NGなら1回だけ ja 指定で再試行
    if not _lang_is_japanese(arr):
        try:
            arr2 = _run_summarizer_json(
                summarizer=summarizer,
                body_path=body_path,
                raw_bytes=None if body_path is not None else raw_bytes,
                env_extra={"SUMMARY_LANG": "ja"},
            )
            if _lang_is_japanese(arr2):
                arr = arr2
        except Exception:
            # 再試行に失敗しても、初回結果で継続（記録上は lang_ok=0）
            pass

    summary_arr = arr
    summary_text = "\n".join(arr) + "\n"

    # モデル名タグ
    model_used = args.model or _detect_model_tag() or ""

    # メトリクス準備（CSVヘッダ互換を保つため lang_ok は SQLite 側 metrics_json へ）
    ok_three, max_len, ended_maru, ascii_auto, chars_total = _validate_three_lines(summary_arr)
    lang_ok = 1 if _lang_is_japanese(summary_arr) else 0
    ts = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    metrics = {
        "timestamp": ts,
        "ok_three_lines": ok_three,
        "max_line_len": max_len,
        "ended_with_maru": ended_maru,
        "ascii_autoconverted": ascii_auto,  # summarizer側で実施したかどうかは未知
        "chars_total": chars_total,
        "lang_ok": lang_ok,  # ← ここでのみ追加（CSV列は変えない）
    }

    # 保存処理
    _ensure_runs()
    sqlite_path = Path(args.sqlite).resolve()
    _ensure_sqlite_schema(sqlite_path)

    _insert_sqlite(
        sqlite_path,
        trace_id=args.trace_id,
        source_path=str(body_path) if body_path else "(stdin)",
        source_sha=source_sha,
        line_count=line_count,
        nbytes=nbytes,
        model_used=model_used,
        summary_arr=summary_arr,
        summary_text=summary_text,
        metrics=metrics,
    )

    _append_metrics_row(
        METRICS_CSV,
        ts=ts,
        source_path=str(body_path) if body_path else "(stdin)",
        model_used=model_used,
        ok_three_lines=ok_three,
        max_line_len=max_len,
        ended_with_maru=ended_maru,
        ascii_autoconverted=ascii_auto,
        chars_total=chars_total,
    )

    # STDOUT: JSON配列（GUI等がそのまま受け取れる形）
    print(json.dumps(summary_arr, ensure_ascii=False))


if __name__ == "__main__":
    main()
