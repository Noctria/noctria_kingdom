#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2

"""
Royal Scribe（史官）
- 王国の建国記録/議事録/AI会話/PDCA進捗を DB へ保存（Postgres）
- DB が使えない場合でも JSONL へフォールバックして永続化を保証
- 既存の chronicle_thread / chronicle_entry を使用

提供関数:
- ensure_thread(topic, tags) -> int
- log_chronicle(title, category, content_md, trace_id=None, topic="PDCA nightly", tags=None, refs=None) -> None
- chronicle_save(entry: dict) -> None  # 汎用 one-shot 保存（推奨）
- log_pdca_stage(stage: str, payload: dict, trace_id: str | None = None, topic="PDCA agents", tags=None, refs=None) -> None
- log_ai_message(name: str, role: str, content: str, trace_id: str | None = None, topic="AI Council", tags=None, refs=None) -> None
- log_test_results(pytest_summary: dict, trace_id: str | None = None, topic="PDCA agents", tags=None) -> None
- log_lint_results(ruff_meta: dict, trace_id: str | None = None, topic="PDCA agents", tags=None) -> None
"""


# ----------------------------------------
# DSN 解決
# ----------------------------------------
DSN: Optional[str] = (
    os.getenv("NOCTRIA_DB_DSN") or os.getenv("NOCTRIA_OBS_PG_DSN") or os.getenv("DATABASE_URL")
)

# ルート推定（このファイルの2階層上＝リポジトリ直下）
ROOT = Path(__file__).resolve().parents[1]

# JSONL フォールバック先を決める（存在すれば src/codex_reports を優先）
FALLBACK_DIRS = [
    ROOT / "src" / "codex_reports",
    ROOT / "codex_reports",
]
for _d in FALLBACK_DIRS:
    try:
        _d.mkdir(parents=True, exist_ok=True)
        FALLBACK_JSONL = _d / "chronicle.jsonl"
        break
    except Exception:
        continue
else:
    # 最後の手段: カレント直下
    FALLBACK_JSONL = Path("chronicle.jsonl")


# ----------------------------------------
# 内部ユーティリティ
# ----------------------------------------
def _conn():
    if not DSN:
        return None
    return psycopg2.connect(DSN)


def _write_jsonl_fallback(entry: Dict[str, Any]) -> None:
    """DB が使えない/失敗した場合の永続化パス。絶対に失敗しないよう best-effort。"""
    try:
        with open(FALLBACK_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # 最後の最後の手段（権限などで失敗する場合）
        try:
            print("[scribe:fallback] ", json.dumps(entry, ensure_ascii=False))
        except Exception:
            pass


def _md_from_json(obj: Any) -> str:
    """JSON を Markdown のコードブロックにする簡易整形。"""
    try:
        pretty = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    except Exception:
        pretty = str(obj)
    return f"```json\n{pretty}\n```"


# ----------------------------------------
# 既存 API
# ----------------------------------------
def ensure_thread(topic: str, tags: List[str] | None = None) -> int:
    conn = _conn()
    if not conn:
        return 0
    with conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM chronicle_thread WHERE topic=%s AND is_open=TRUE ORDER BY id DESC LIMIT 1",
            (topic,),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            "INSERT INTO chronicle_thread(topic,tags) VALUES (%s,%s) RETURNING id",
            (topic, tags or []),
        )
        return cur.fetchone()[0]


def log_chronicle(
    title: str,
    category: str,
    content_md: str,
    trace_id: Optional[str] = None,
    topic: str = "PDCA nightly",
    tags: Optional[List[str]] = None,
    refs: Optional[Dict[str, Any]] = None,
) -> None:
    """
    既存の chronicle_entry へ書き込む。失敗時は JSONL にフォールバック。
    """
    entry = {
        "title": title,
        "category": category,
        "content_md": content_md,
        "trace_id": trace_id,
        "topic": topic,
        "tags": tags or [],
        "refs": refs or {},
    }

    conn = _conn()
    if not conn:
        _write_jsonl_fallback({"via": "log_chronicle", **entry})
        return

    try:
        th_id = ensure_thread(topic, tags or [])
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chronicle_entry(thread_id, trace_id, title, category, content_md, refs)
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                (th_id, trace_id, title, category, content_md, json.dumps(refs or {})),
            )
    except Exception:
        # DB 書き込みに失敗しても失わない
        _write_jsonl_fallback({"via": "log_chronicle(db_failed)", **entry})


# ----------------------------------------
# 追加 API（汎用 & ショートカット）
# ----------------------------------------
def chronicle_save(entry: Dict[str, Any]) -> None:
    """
    汎用の保存入口。可能なら DB（chronicle_entry 経由）、ダメなら JSONL。

    受け取る entry の例:
    {
      "stage": "pytest",
      "title": "pytest summary",
      "trace_id": "...",
      "topic": "PDCA agents",
      "tags": ["ci","test"],
      "refs": {"junit_xml": "src/codex_reports/pytest_last.xml"},
      "payload": {...}  # なんでもOK
    }
    """
    stage = entry.get("stage") or entry.get("category") or "misc"
    title = entry.get("title") or f"PDCA:{stage}"
    trace_id = entry.get("trace_id")
    topic = entry.get("topic") or "PDCA nightly"
    tags = entry.get("tags") or []
    refs = entry.get("refs") or {}

    # payload を Markdown(JSON) として残す
    content_md = _md_from_json(entry.get("payload", entry))

    # まず DB 経由（既存 log_chronicle）を試し、失敗時はフォールバック
    try:
        log_chronicle(
            title=title,
            category=str(stage),
            content_md=content_md,
            trace_id=trace_id,
            topic=topic,
            tags=tags,
            refs=refs,
        )
    except Exception:
        _write_jsonl_fallback({"via": "chronicle_save(exception)", **entry})


def log_pdca_stage(
    stage: str,
    payload: Dict[str, Any],
    trace_id: Optional[str] = None,
    topic: str = "PDCA agents",
    tags: Optional[List[str]] = None,
    refs: Optional[Dict[str, Any]] = None,
) -> None:
    """
    PDCA の各段で呼びやすいショートカット。
    """
    chronicle_save(
        {
            "stage": stage,
            "title": f"PDCA stage: {stage}",
            "trace_id": trace_id,
            "topic": topic,
            "tags": tags or [stage],
            "refs": refs or {},
            "payload": payload,
        }
    )


def log_ai_message(
    name: str,
    role: str,
    content: str,
    trace_id: Optional[str] = None,
    topic: str = "AI Council",
    tags: Optional[List[str]] = None,
    refs: Optional[Dict[str, Any]] = None,
) -> None:
    """
    AI 談話の記録（人/AI どちらでも）。GUI の議事録表示用。
    """
    payload = {"name": name, "role": role, "content": content}
    chronicle_save(
        {
            "stage": "ai_message",
            "title": f"[{role}] {name}",
            "trace_id": trace_id,
            "topic": topic,
            "tags": (tags or []) + ["ai", role],
            "refs": refs or {},
            "payload": payload,
        }
    )


def log_test_results(
    pytest_summary: Dict[str, Any],
    trace_id: Optional[str] = None,
    topic: str = "PDCA agents",
    tags: Optional[List[str]] = None,
) -> None:
    """
    pytest 実行結果（run_pdca_agents.py からの呼び出し想定）
    """
    refs = {"junit_xml": str(pytest_summary.get("xml_path") or "src/codex_reports/pytest_last.xml")}
    chronicle_save(
        {
            "stage": "pytest",
            "title": "pytest summary",
            "trace_id": trace_id,
            "topic": topic,
            "tags": (tags or []) + ["ci", "test"],
            "refs": refs,
            "payload": pytest_summary,
        }
    )


def log_lint_results(
    ruff_meta: Dict[str, Any],
    trace_id: Optional[str] = None,
    topic: str = "PDCA agents",
    tags: Optional[List[str]] = None,
) -> None:
    """
    ruff のハイライト等（run_pdca_agents.py からの呼び出し想定）
    """
    refs = {"ruff_json": str(ruff_meta.get("json_path") or "src/codex_reports/ruff/ruff.json")}
    chronicle_save(
        {
            "stage": "ruff",
            "title": "ruff summary",
            "trace_id": trace_id,
            "topic": topic,
            "tags": (tags or []) + ["ci", "lint"],
            "refs": refs,
            "payload": ruff_meta,
        }
    )
