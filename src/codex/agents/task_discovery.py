# [NOCTRIA_CORE_REQUIRED]
#!/usr/bin/env python3
# coding: utf-8
"""
🧭 Codex Questor — 問題発見エージェント（KEEP-safe版）

目的:
- リポジトリを走査し、「創造のタネ」= 実装候補タスクを自動抽出する。
- TODO/FIXME/NOTE/＠タグ、未実装スタブ（pass/raise NotImplementedError）、ダミー関数等を検出。
- 検出結果を JSONL（原子的書き込み）へ保存。DB（PostgreSQL）が使えれば併記保存（失敗してもHOLD）。
- 生成タスクは後段の「設計→実装→評価」エージェントのインボックスになる。

特徴:
- 遅延import（psycopg2 等の重依存が無くても動作）。
- 例外時は HOLD（副作用なし）。trace_id と obs_event ログを埋める。
- CLIあり: --root / --out / --max-files / --include / --exclude / --dry-run / --save-db / --priority-bias

出力（1行=1タスク JSON）例:
{
  "trace_id": "...",
  "task_id": "codex_task_20250926T123456_000001",
  "kind": "TODO",                       # TODO | FIXME | STUB | DESIGN_GAP | DOC_TODO
  "file": "src/strategies/levia_tempest.py",
  "line": 123,
  "col": 5,
  "message": "TODO: implement position sizing under volatile regime",
  "snippet": "    # TODO: implement position sizing under volatile regime",
  "priority": 0.78,                     # 0.0 - 1.0
  "tags": ["levia", "risk", "size"],
  "created_at": "2025-09-26T12:34:56Z",
  "meta": {"detector": "todo_comment", "score_breakdown": {...}}
}

次の段階:
- veritas_spec_writer（設計層）にこのJSONLをインボックスとして渡す。
- hermes/hypothesis_writer で仕様・仮説プロンプト生成 → codex/patcher で実装 → prometheus/evaluator でスコア。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ========= 遅延import & SAFEユーティリティ =====================================


def _lazy_import(name: str):
    try:
        __import__(name)
        return sys.modules[name]
    except Exception:
        return None


def _paths():
    mod = _lazy_import("src.core.path_config") or _lazy_import("core.path_config")
    root = (
        Path(__file__).resolve().parents[3]
        if "src" in str(Path(__file__).resolve())
        else Path(__file__).resolve().parents[1]
    )
    if mod:
        return {
            "ROOT": getattr(mod, "ROOT", root),
            "LOGS_DIR": getattr(mod, "LOGS_DIR", root / "logs"),
        }
    return {"ROOT": root, "LOGS_DIR": root / "logs"}


def _logger():
    mod = _lazy_import("src.core.logger") or _lazy_import("core.logger")
    paths = _paths()
    log_path = Path(paths["LOGS_DIR"]) / "codex" / "task_discovery.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if mod and hasattr(mod, "setup_logger"):
        return mod.setup_logger("CodexTaskDiscovery", log_path)  # type: ignore[attr-defined]
    import logging

    lg = logging.getLogger("CodexTaskDiscovery")
    if not lg.handlers:
        lg.setLevel(logging.INFO)
        fh = logging.FileHandler(str(log_path), encoding="utf-8")
        sh = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s")
        fh.setFormatter(fmt)
        sh.setFormatter(fmt)
        lg.addHandler(fh)
        lg.addHandler(sh)
    return lg


def _obs():
    mod = _lazy_import("src.plan_data.observability") or _lazy_import("plan_data.observability")

    def mk_trace_id():
        return dt.datetime.utcnow().strftime("trace_%Y%m%dT%H%M%S_%f")

    def obs_event(
        event: str,
        *,
        severity: str = "LOW",
        trace_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ):
        msg = {
            "event": event,
            "severity": severity,
            "trace_id": trace_id,
            "meta": meta or {},
            "ts": dt.datetime.utcnow().isoformat(),
        }
        print("[OBS]", json.dumps(msg, ensure_ascii=False))

    if mod:
        mk_trace_id = getattr(mod, "mk_trace_id", mk_trace_id)  # type: ignore
        obs_event = getattr(mod, "obs_event", obs_event)  # type: ignore
    return mk_trace_id, obs_event


LOGGER = _logger()
PATHS = _paths()
mk_trace_id, obs_event = _obs()

# ========= DB設定（任意・HOLD） =================================================

DB_NAME = os.getenv("POSTGRES_DB", "airflow")
DB_USER = os.getenv("POSTGRES_USER", "airflow")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "airflow")
DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

# ========= 設定・検出パターン ===================================================

DEFAULT_INCLUDE = [
    r"^src/.*\.(py|md|txt|yaml|yml|toml|ini)$",
    r"^airflow_docker/dags/.*\.py$",
    r"^noctria_gui/.*\.(py|html|js|css)$",
    r"^tools/.*\.py$",
]
DEFAULT_EXCLUDE = [
    r"/venv_",
    r"/_graveyard/",
    r"/node_modules/",
    r"/\.git/",
    r"/__pycache__/",
    r"^logs/",
    r"^viz/",
]

RE_TODO = re.compile(r"#\s*(?:TODO|TBD|NOTE|HACK)\b[:\-\s]*(.*)", re.IGNORECASE)
RE_FIXME = re.compile(r"#\s*(?:FIXME|BUG)\b[:\-\s]*(.*)", re.IGNORECASE)
RE_STUB1 = re.compile(
    r"^\s*def\s+[A-Za-z_]\w*\(.*\):\s*(?:pass|\"\"\".*?\"\"\"|\'\'\'.*?\'\'\')\s*$",
    re.DOTALL | re.MULTILINE,
)
RE_STUB2 = re.compile(r"raise\s+NotImplementedError\b")
RE_DOC_TODO = re.compile(r"(?:^|\s)(?:TODO|TBD):\s*(.+)")

TAG_HINTS = {
    "risk": re.compile(r"\b(risk|drawdown|stop[-_\s]?loss|lot|exposure)\b", re.I),
    "latency": re.compile(r"\b(latency|perf|optimize|speed)\b", re.I),
    "strategy": re.compile(r"\b(strategy|entry|exit|signal|alpha)\b", re.I),
    "data": re.compile(r"\b(dataset|feature|preprocess|loader|fetch)\b", re.I),
    "obs": re.compile(r"\b(observab|trace|metrics|log)\b", re.I),
}

# ========= データ構造 ==========================================================


@dataclass
class DiscoveredTask:
    trace_id: str
    task_id: str
    kind: str
    file: str
    line: int
    col: int
    message: str
    snippet: str
    priority: float
    tags: List[str]
    created_at: str
    meta: Dict[str, Any]


# ========= ユーティリティ =======================================================


def _atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", delete=False, dir=str(path.parent), encoding=encoding
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def _norm_path(p: Path, root: Path) -> str:
    try:
        return str(p.relative_to(root)).replace("\\", "/")
    except Exception:
        return str(p).replace("\\", "/")


def _match_any(path_str: str, patterns: List[str]) -> bool:
    return any(re.search(p, path_str) for p in patterns)


def _score_priority(kind: str, line: int, tags: List[str], bias: float) -> float:
    base = {"FIXME": 0.9, "TODO": 0.7, "STUB": 0.65, "DESIGN_GAP": 0.6, "DOC_TODO": 0.5}.get(
        kind, 0.5
    )
    # 低い行番号＝重要（多くは上位設計部）
    line_boost = max(0.0, (1000 - min(line, 1000)) / 1000.0) * 0.2
    tag_boost = 0.1 if any(t in {"risk", "strategy"} for t in tags) else 0.0
    return max(0.0, min(1.0, base + line_boost + tag_boost + bias))


def _extract_tags(text: str) -> List[str]:
    hits = []
    for k, rx in TAG_HINTS.items():
        if rx.search(text or ""):
            hits.append(k)
    return hits[:4]


# ========= 検出器 =============================================================


def _detect_in_text(rel_path: str, text: str) -> Iterable[Tuple[str, int, int, str, str]]:
    # コメント TODO/FIXME
    out: List[Tuple[str, int, int, str, str]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        m1 = RE_TODO.search(line)
        if m1:
            out.append(("TODO", i, (m1.start(0) + 1), m1.group(0).strip(), line.rstrip()))
        m2 = RE_FIXME.search(line)
        if m2:
            out.append(("FIXME", i, (m2.start(0) + 1), m2.group(0).strip(), line.rstrip()))
        # ドキュメント TODO
        m3 = RE_DOC_TODO.search(line)
        if m3 and rel_path.endswith((".md", ".txt")):
            out.append(
                ("DOC_TODO", i, (m3.start(0) + 1), f"TODO: {m3.group(1).strip()}", line.rstrip())
            )
    # スタブ検出（def ...: pass / raise NotImplementedError）
    if rel_path.endswith(".py"):
        for m in RE_STUB1.finditer(text):
            line = text[: m.start()].count("\n") + 1
            snippet = text[m.start() : m.start() + 160].splitlines()[0]
            out.append(("STUB", line, 1, "Function stub (pass or empty body) detected", snippet))
        for m in RE_STUB2.finditer(text):
            line = text[: m.start()].count("\n") + 1
            snippet = text[m.start() : m.start() + 160].splitlines()[0]
            out.append(("STUB", line, 1, "NotImplementedError placeholder detected", snippet))
    # 簡易 DESIGN_GAP: simulate シグネチャだけあって本文が薄い（ヒューリスティック）
    if rel_path.endswith(".py"):
        if re.search(r"def\s+simulate\s*\([^)]*\)\s*:\s*\n\s*(?:pass|return\s+{}\s*)", text):
            i = text[: re.search(r"def\s+simulate", text).start()].count("\n") + 1
            out.append(
                ("DESIGN_GAP", i, 1, "simulate() appears empty/minimal", "simulate skeleton")
            )
    return out


# ========= 走査本体 ============================================================


def discover_tasks(
    *,
    root: Path,
    include: List[str],
    exclude: List[str],
    max_files: int | None,
    priority_bias: float,
) -> List[DiscoveredTask]:
    tid = mk_trace_id()
    obs_event("codex.questor.start", trace_id=tid, meta={"root": str(root), "max_files": max_files})
    tasks: List[DiscoveredTask] = []
    count = 0

    all_files: List[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = _norm_path(p, root)
        if not _match_any(rel, include):
            continue
        if _match_any(rel, exclude):
            continue
        all_files.append(p)

    # ファイル数制限（重いリポでもサクッと動く）
    if max_files and len(all_files) > max_files:
        LOGGER.info(f"[info] limiting files: {max_files}/{len(all_files)}")
        all_files = all_files[:max_files]

    for fp in all_files:
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = _norm_path(fp, root)
        for kind, line, col, msg, snippet in _detect_in_text(rel, text):
            tags = list(set(_extract_tags(msg + " " + snippet)))
            prio = _score_priority(kind, line, tags, priority_bias)
            task_id = f"codex_task_{dt.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{count:06d}"
            tasks.append(
                DiscoveredTask(
                    trace_id=tid,
                    task_id=task_id,
                    kind=kind,
                    file=rel,
                    line=line,
                    col=col,
                    message=msg,
                    snippet=snippet[:400],
                    priority=round(prio, 4),
                    tags=tags,
                    created_at=dt.datetime.utcnow().isoformat() + "Z",
                    meta={"detector": "questor", "repo_root": str(root)},
                )
            )
            count += 1

    obs_event("codex.questor.done", trace_id=tid, meta={"tasks": len(tasks)})
    return tasks


# ========= 永続化（JSONL / DB はHOLD可能） ====================================


def write_jsonl(path: Path, tasks: List[DiscoveredTask]) -> Path:
    lines = "\n".join(json.dumps(asdict(t), ensure_ascii=False) for t in tasks) + (
        "\n" if tasks else ""
    )
    _atomic_write_text(path, lines)
    return path


def save_to_db(tasks: List[DiscoveredTask]) -> bool:
    try:
        psycopg2 = _lazy_import("psycopg2")
        if psycopg2 is None:
            raise RuntimeError("psycopg2 not available")
        conn = psycopg2.connect(  # type: ignore[attr-defined]
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                CREATE TABLE IF NOT EXISTS codex_tasks (
                    id SERIAL PRIMARY KEY,
                    task_id TEXT UNIQUE,
                    trace_id TEXT,
                    kind TEXT,
                    file TEXT,
                    line INTEGER,
                    col INTEGER,
                    message TEXT,
                    snippet TEXT,
                    priority DOUBLE PRECISION,
                    tags JSONB,
                    created_at TIMESTAMP,
                    meta JSONB
                )
                """)
                for t in tasks:
                    cur.execute(
                        """
                    INSERT INTO codex_tasks (task_id, trace_id, kind, file, line, col, message, snippet, priority, tags, created_at, meta)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (task_id) DO NOTHING
                    """,
                        (
                            t.task_id,
                            t.trace_id,
                            t.kind,
                            t.file,
                            t.line,
                            t.col,
                            t.message,
                            t.snippet,
                            float(t.priority),
                            json.dumps(t.tags, ensure_ascii=False),
                            dt.datetime.fromisoformat(t.created_at.replace("Z", "")),
                            json.dumps(t.meta, ensure_ascii=False),
                        ),
                    )
        LOGGER.info("✅ codex_tasks: DB保存完了")
        return True
    except Exception as e:
        LOGGER.error(f"🚨 DB保存失敗（継続）: {e}", exc_info=True)
        return False


# ========= CLI ================================================================


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Codex Questor — Problem Discovery Agent")
    p.add_argument("--root", default=".", help="リポジトリのルート")
    p.add_argument(
        "--out", default=None, help="JSONL保存先（未指定なら logs/codex/inbox/tasks_*.jsonl）"
    )
    p.add_argument("--include", default=",".join(DEFAULT_INCLUDE), help="正規表現カンマ区切り")
    p.add_argument("--exclude", default=",".join(DEFAULT_EXCLUDE), help="正規表現カンマ区切り")
    p.add_argument("--max-files", type=int, default=8000, help="走査ファイル上限（安全用）")
    p.add_argument("--dry-run", action="store_true", help="結果を保存しない（標準出力のみ）")
    p.add_argument("--save-db", action="store_true", help="DBにも保存（失敗はHOLD）")
    p.add_argument(
        "--priority-bias", type=float, default=0.0, help="優先度に一律バイアス（-0.2〜+0.2推奨）"
    )
    return p.parse_args(argv or sys.argv[1:])


def main(argv: Optional[List[str]] = None) -> int:
    ns = _parse_args(argv)
    root = Path(ns.root).resolve()
    include = [s.strip() for s in ns.include.split(",") if s.strip()]
    exclude = [s.strip() for s in ns.exclude.split(",") if s.strip()]

    try:
        tasks = discover_tasks(
            root=root,
            include=include,
            exclude=exclude,
            max_files=ns.max_files,
            priority_bias=ns.priority_bias,
        )

        if ns.dry_run:
            # 標準出力にサマリ
            print(json.dumps([asdict(t) for t in tasks[:50]], ensure_ascii=False, indent=2))
            if len(tasks) > 50:
                print(f"... ({len(tasks) - 50} more)")
            return 0

        # 保存先決定
        out_path = (
            Path(ns.out)
            if ns.out
            else (
                Path(PATHS["LOGS_DIR"])
                / "codex"
                / "inbox"
                / f"tasks_{dt.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.jsonl"
            )
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        write_jsonl(out_path, tasks)
        LOGGER.info(f"🗃️ JSONL saved: {out_path} (tasks={len(tasks)})")

        # 任意でDB保存
        if ns.save_db and tasks:
            _ = save_to_db(tasks)

        return 0
    except Exception as e:
        tid = mk_trace_id()
        obs_event(
            "codex.questor.unhandled", severity="CRITICAL", trace_id=tid, meta={"exc": repr(e)}
        )
        LOGGER.error(f"🚨 予期せぬエラー: {e}", exc_info=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
