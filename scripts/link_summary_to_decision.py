#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [NOCTRIA_CORE_REQUIRED]
"""
scripts/link_summary_to_decision.py

PDCAの三行要約(pdca_log.db/pdca_summaries)を Decision Registry（CSV台帳）に
trace_id でひも付けるツール。

優先順位:
  1) src.core.decision_registry モジュールに upsert/更新系API があれば使用
  2) なければ --registry-csv で指定された CSV を安全に直接更新（原子的書き換え）

追記/更新する列（存在しなければ自動追加）:
  - summary_line1, summary_line2, summary_line3  … 三行要約
  - summary_model                              … モデル名タグ（任意）
  - summary_at                                 … 要約保存時刻(UTC, ISO8601)

使い方:
  # もっとも簡単な例（CSVパスを指定）
  scripts/link_summary_to_decision.py --trace-id <TRACE_ID> \
      --registry-csv docs/operations/PDCA/decision_registry.csv

  # SQLiteパスやモデル名を明示
  scripts/link_summary_to_decision.py \
      --trace-id 2025-10-01T17:23:04Z-e5669a99-0c2f-46b6-a0c6-38dc3ea43059 \
      --sqlite pdca_log.db \
      --registry-csv docs/operations/PDCA/decision_registry.csv

  # 既存の src.core.decision_registry が提供する upsert API を使いたい場合は
  # --use-module を付ける（関数が無ければ自動でCSV直接更新にフォールバック）
  scripts/link_summary_to_decision.py --trace-id <TRACE_ID> --use-module
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import importlib
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE = ROOT / "pdca_log.db"

# CSVに書き込む列
SUMMARY_COLUMNS = [
    "summary_line1",
    "summary_line2",
    "summary_line3",
    "summary_model",
    "summary_at",
]


def _fetch_summary_from_sqlite(sqlite_path: Path, trace_id: str) -> Tuple[List[str], str]:
    """
    pdca_summaries から trace_id に一致する最新1件を取り出す。
    returns: (summary_arr[3], model_used:str)
    """
    q = """
        SELECT summary_json, COALESCE(model_used, ''), created_at
          FROM pdca_summaries
         WHERE trace_id = ?
         ORDER BY id DESC
         LIMIT 1
    """
    con = sqlite3.connect(str(sqlite_path))
    try:
        cur = con.cursor()
        row = cur.execute(q, (trace_id,)).fetchone()
        if not row:
            raise RuntimeError(f"no summary found for trace_id={trace_id!r} in {sqlite_path}")
        summary_json, model_used, created_at = row
    finally:
        con.close()

    # JSONは ["…","…","…"] フォーマットのはず
    import json
    arr = json.loads(summary_json)
    if not (isinstance(arr, list) and len(arr) == 3 and all(isinstance(x, str) for x in arr)):
        raise ValueError(f"invalid summary_json for trace_id={trace_id}: expect list[str]*3")

    # created_at は SQLite のローカル時刻 (UTCでない可能性がある) なので、ここでは UTC 現在時刻を記録
    # 必要なら pdca_summaries の created_at をそのまま使うように調整してもよい
    summary_at = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00","Z")

    return arr + [model_used, summary_at], model_used  # 返り値は整形済み配列＋モデル名


def _try_use_module_api(trace_id: str, fields: Dict[str, str]) -> bool:
    """
    src.core.decision_registry に upsert 系APIがあれば使う。
    想定API（存在すればどれか一つを利用）:
      - upsert_fields(trace_id: str, fields: Dict[str,str]) -> None
      - upsert_decision_fields(trace_id: str, fields: Dict[str,str]) -> None
    """
    try:
        mod = importlib.import_module("src.core.decision_registry")
    except Exception:
        return False

    for fname in ("upsert_fields", "upsert_decision_fields"):
        fn = getattr(mod, fname, None)
        if callable(fn):
            try:
                fn(trace_id, fields)  # type: ignore[arg-type]
                return True
            except Exception as e:
                print(f"[warn] decision_registry.{fname} failed: {e}", file=sys.stderr)
                return False
    return False


def _csv_atomic_write(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    tmp_fd, tmp_path = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
    os.close(tmp_fd)
    tmp = Path(tmp_path)
    try:
        with tmp.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow({k: (r.get(k, "") or "") for k in fieldnames})
        tmp.replace(path)
    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise


def _csv_update_registry(registry_csv: Path, trace_id: str, fields: Dict[str, str]) -> None:
    """
    CSVを安全に更新。trace_id の行があれば上書き、無ければ新規行を追加。
    必要ならヘッダに SUMMARY_COLUMNS を追加。
    """
    exists = registry_csv.exists()
    rows: List[Dict[str, str]] = []
    fieldnames: List[str] = []

    if exists:
        with registry_csv.open("r", encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            fieldnames = list(r.fieldnames or [])
            for row in r:
                rows.append(dict(row))
    else:
        # 新規作成: trace_id を含む最小ヘッダ
        fieldnames = ["trace_id"]

    # summary系列をヘッダに足す（無ければ）
    for col in SUMMARY_COLUMNS:
        if col not in fieldnames:
            fieldnames.append(col)

    # 既存に trace_id があるか
    hit = False
    for row in rows:
        if row.get("trace_id", "") == trace_id:
            row.update(fields)
            hit = True
            break

    if not hit:
        new_row = {"trace_id": trace_id}
        new_row.update(fields)
        rows.append(new_row)

    _csv_atomic_write(registry_csv, rows, fieldnames)


def main():
    ap = argparse.ArgumentParser(description="Link PDCA three-line summary to Decision Registry by trace_id.")
    ap.add_argument("--trace-id", required=True, help="Trace ID to link (must exist in pdca_summaries)")
    ap.add_argument("--sqlite", default=str(DEFAULT_SQLITE), help="Path to pdca_log.db (default: ./pdca_log.db)")
    ap.add_argument("--registry-csv", default="", help="Path to Decision Registry CSV (if not using module API)")
    ap.add_argument("--use-module", action="store_true", help="Use src.core.decision_registry if upsert API exists")
    args = ap.parse_args()

    sqlite_path = Path(args.sqlite).resolve()
    if not sqlite_path.exists():
        print(f"[error] SQLite not found: {sqlite_path}", file=sys.stderr)
        sys.exit(2)

    # 1) SQLite から要約を取得
    packed, model_used = _fetch_summary_from_sqlite(sqlite_path, args.trace_id)
    line1, line2, line3, model_tag, summary_at = packed

    fields = {
        "summary_line1": line1,
        "summary_line2": line2,
        "summary_line3": line3,
        "summary_model": model_tag or model_used or "",
        "summary_at": summary_at,
    }

    # 2) モジュールAPI優先
    used_module = False
    if args.use_module:
        used_module = _try_use_module_api(args.trace_id, fields)

    # 3) CSV直接更新
    if not used_module:
        csv_path = Path(args.registry_csv).resolve() if args.registry_csv else None
        if not csv_path:
            print("[error] --registry-csv is required when not using module API.", file=sys.stderr)
            sys.exit(3)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        _csv_update_registry(csv_path, args.trace_id, fields)

    # 出力（確認用）
    print(f"linked trace_id={args.trace_id}")
    for k, v in fields.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
