# codex/tools/json_parse.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List

def load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def extract_failures(py_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    pytest-json（pytest-json-report）の構造から失敗テストを抽出し、
    Inventorに渡しやすい簡易フォーマットへ変換する。
    返す要素: {nodeid, message, traceback}
    """
    out: List[Dict[str, Any]] = []
    tests = py_json.get("tests", []) or []
    for t in tests:
        if t.get("outcome") == "failed":
            nodeid = t.get("nodeid", "")
            # pluginにより詳細の場所が異なるため安全側で取り出し
            msg = None
            tb = None
            # longrepr 互換（あれば）
            longrepr = t.get("longrepr")
            if isinstance(longrepr, str):
                tb = longrepr
            # call フェーズの失敗メッセージがあれば拾う
            call = t.get("call") or {}
            if isinstance(call, dict):
                msg = call.get("crash", call.get("message")) or call.get("outcome")
            out.append({
                "nodeid": nodeid,
                "message": msg or "test failed",
                "traceback": tb or "",
            })
    return out

def build_pytest_result_for_inventor(py_json: Dict[str, Any]) -> Dict[str, Any]:
    return {"failures": extract_failures(py_json)}
