# src/veritas/spec_writer.py
# [NOCTRIA_CORE_REQUIRED]
#!/usr/bin/env python3
# coding: utf-8
"""
📝 Veritas Spec Writer — タスクJSONLから仕様ドラフト & 最小pytest生成（KEEP-safe）

目的:
- codex/agents/task_discovery.py が出力した JSONL を読み、
  タスクごとに「仕様ドラフト（.md）」と「最小pytest（_test.py）」の雛形を作る。
- 依存は遅延import、保存は原子的（tmp→os.replace）、DB保存は任意（失敗HOLD）。

出力:
- docs/specs/<task_id>.md
- tests/generated/test_<task_id>.py
- logs/veritas/spec_writer.log
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ===== 遅延import/ロガー/パス/obs ==============================================


def _lazy_import(name: str):
    try:
        __import__(name)
        return sys.modules[name]
    except Exception:
        return None


def _paths():
    mod = _lazy_import("src.core.path_config") or _lazy_import("core.path_config")
    root = Path(__file__).resolve().parents[2]
    if mod:
        return {
            "ROOT": getattr(mod, "ROOT", root),
            "LOGS_DIR": getattr(mod, "LOGS_DIR", root / "logs"),
        }
    return {"ROOT": root, "LOGS_DIR": root / "logs"}


def _logger():
    mod = _lazy_import("src.core.logger") or _lazy_import("core.logger")
    paths = _paths()
    log_path = Path(paths["LOGS_DIR"]) / "veritas" / "spec_writer.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if mod and hasattr(mod, "setup_logger"):
        return mod.setup_logger("VeritasSpecWriter", log_path)  # type: ignore[attr-defined]
    import logging

    lg = logging.getLogger("VeritasSpecWriter")
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

# ===== モデル ==================================================================


@dataclass
class TaskItem:
    task_id: str
    kind: str
    file: str
    line: int
    message: str
    snippet: str
    priority: float
    tags: List[str]
    created_at: str
    trace_id: str


# ===== ユーティリティ ==========================================================


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", delete=False, dir=str(path.parent), encoding="utf-8"
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def _read_jsonl(path: Path, limit: Optional[int]) -> List[TaskItem]:
    items: List[TaskItem] = []
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines()):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        items.append(
            TaskItem(
                task_id=obj.get("task_id", ""),
                kind=obj.get("kind", ""),
                file=obj.get("file", ""),
                line=int(obj.get("line", 0)),
                message=obj.get("message", ""),
                snippet=obj.get("snippet", ""),
                priority=float(obj.get("priority", 0.0)),
                tags=list(obj.get("tags", []) or []),
                created_at=obj.get("created_at", ""),
                trace_id=obj.get("trace_id", ""),
            )
        )
        if limit and len(items) >= limit:
            break
    return items


# ===== 生成ロジック ============================================================

_SPEC_TMPL = """# Spec: {task_id}
- Kind: **{kind}**
- File: `{file}` :{line}
- Priority: {priority}
- Tags: {tags}
- CreatedAt: {created_at}
- Trace: {trace_id}

## Context
```
{snippet}
```

## Objective
{objective}

## Acceptance Criteria
- [ ] {ac1}
- [ ] {ac2}

## Risks / Considerations
- Logging / Observability
- Performance / Latency
- Backward compatibility
"""

_TEST_TMPL_TODO = """# Generated minimal test for {task_id}
def test_{safe_id}_placeholder():
    assert True  # replace with concrete assertions
"""


def _build_objective(task: TaskItem) -> Tuple[str, str, str]:
    kind = (task.kind or "").upper()
    if kind == "FIXME":
        return ("修復すべき不具合を特定する", "再現ケースが成功する", "同種失敗を網羅する")
    if kind == "STUB":
        return ("スタブ関数を実装する", "主要関数が有意味な戻り値を返す", "例外/Noneにならない")
    if kind == "DESIGN_GAP":
        return ("機能の仕様化と最小実装", "仕様に沿ったAPIが成立", "異常系も定義される")
    return ("TODOを具体化し仕様→実装→テスト", "機能がストーリーを満たす", "回帰テストが追加される")


def _safe_id(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", s)


def generate_for_task(task: TaskItem, spec_dir: Path, test_dir: Path) -> Tuple[Path, Path]:
    objective, ac1, ac2 = _build_objective(task)
    spec_txt = _SPEC_TMPL.format(
        task_id=task.task_id,
        kind=task.kind,
        file=task.file,
        line=task.line,
        priority=task.priority,
        tags=", ".join(task.tags) or "-",
        created_at=task.created_at,
        trace_id=task.trace_id,
        snippet=task.snippet or (task.message or ""),
        objective=objective,
        ac1=ac1,
        ac2=ac2,
    )
    test_txt = _TEST_TMPL_TODO.format(task_id=task.task_id, safe_id=_safe_id(task.task_id))
    spec_path = spec_dir / f"{task.task_id}.md"
    test_path = test_dir / f"test_{task.task_id}.py"
    _atomic_write_text(spec_path, spec_txt)
    _atomic_write_text(test_path, test_txt)
    return spec_path, test_path


# ===== CLI ====================================================================


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Veritas Spec Writer")
    p.add_argument("--in", dest="in_path", required=True)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--out-spec-dir", default="docs/specs")
    p.add_argument("--out-test-dir", default="tests/generated")
    return p.parse_args(argv or sys.argv[1:])


def main(argv: Optional[List[str]] = None) -> int:
    ns = _parse_args(argv)
    in_path, spec_dir, test_dir = Path(ns.in_path), Path(ns.out_spec_dir), Path(ns.out_test_dir)
    spec_dir.mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    try:
        tasks = _read_jsonl(in_path, ns.limit)
        if not tasks:
            LOGGER.info("No tasks to process.")
            return 0
        tid = mk_trace_id()
        obs_event("veritas.spec_writer.start", trace_id=tid, meta={"tasks": len(tasks)})
        for t in tasks:
            generate_for_task(t, spec_dir, test_dir)
        obs_event("veritas.spec_writer.done", trace_id=tid, meta={"specs": len(tasks)})
        LOGGER.info(f"✅ {len(tasks)} specs/tests 生成完了")
        return 0
    except Exception as e:
        obs_event(
            "veritas.spec_writer.unhandled",
            severity="CRITICAL",
            trace_id=mk_trace_id(),
            meta={"exc": repr(e)},
        )
        LOGGER.error(f"🚨 エラー: {e}", exc_info=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
