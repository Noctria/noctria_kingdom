#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.prompt_loader import load_governance

MEM_PATH_DEFAULT = Path("data/agent_memory.jsonl")


def _append_memory(path: Path, record: dict) -> None:
    """JSONL メモリに1行追記。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    import datetime as dt

    rec = dict(record)
    rec["ts"] = dt.datetime.now().isoformat()
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(old + json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")


def _shell(
    cmd: str,
    *,
    cwd: str = ".",
    env: Optional[Dict[str, str]] = None,
    timeout: Optional[int] = None,
) -> subprocess.CompletedProcess:
    """安全寄り設定でシェル実行（出力は capture）。"""
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(
        cmd,
        cwd=cwd,
        shell=True,
        text=True,
        capture_output=True,
        env=merged_env,
        timeout=timeout,
    )


def _git_diff_changed_under(prefix: str) -> bool:
    """origin/main..HEAD の範囲で prefix 配下に変更があるかを判定。"""
    try:
        r = subprocess.run(
            ["git", "diff", "--name-only", "origin/main..HEAD", "--", prefix],
            text=True,
            capture_output=True,
        )
        if r.returncode != 0:
            return False
        return any(line.strip() for line in r.stdout.splitlines())
    except Exception:
        return False


def _find_tool(gov: dict, tool_id: str) -> Optional[dict]:
    for t in (gov.get("tools", {}) or {}).get("allowlist", []) or []:
        if t.get("id") == tool_id:
            return t
    return None


def _run_tool(gov: dict, step: dict) -> Dict[str, Any]:
    """
    step: { run: "<tool-id>", with: {...} }
    """
    tool_id = step.get("run")
    t = _find_tool(gov, tool_id)
    if not t:
        return {"status": "error", "error": f"unknown tool {tool_id}"}

    kind = t.get("kind")
    if kind == "shell":
        entry = t.get("entry", "")
        params = step.get("with", {}) or {}
        # {param} テンプレ置換
        for k, v in params.items():
            entry = entry.replace("{" + k + "}", str(v))

        safety = t.get("safety", {}) or {}
        cwd = safety.get("cwd", ".")
        allow_net = bool(safety.get("network", False))

        # ネットワーク遮断まではできないが、プロキシを消して事故を減らす
        env = dict(os.environ)
        if not allow_net:
            for k in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"]:
                env.pop(k, None)

        cp = _shell(entry, cwd=cwd, env=env)
        return {
            "status": "ok" if cp.returncode == 0 else "error",
            "returncode": cp.returncode,
            "stdout": cp.stdout,
            "stderr": cp.stderr,
            "entry": entry,
            "cwd": cwd,
        }

    elif kind == "workflow":
        # いまはスタブ（必要なら GitHub API 連携を拡張）
        return {
            "status": "noop",
            "note": "workflow dispatch stub",
            "workflow": t.get("workflow"),
            "dispatch": t.get("dispatch"),
        }

    return {"status": "error", "error": f"unsupported kind {kind}"}


def _remember(step: dict) -> Dict[str, Any]:
    """step: { remember: {...} } をメモリに追加。"""
    mem_path = Path(os.getenv("NOCTRIA_AGENT_MEM", MEM_PATH_DEFAULT))
    payload = step.get("remember") or {}
    _append_memory(mem_path, {"remember": payload})
    return {"status": "remembered", "data": payload}


def _suggest(step: dict) -> Dict[str, Any]:
    """step: { suggest: {NEXT_ACTIONS:[...]} } を返却に乗せる。"""
    return {"suggest": step.get("suggest")}


def _eval_when(event: Optional[str], when: str) -> bool:
    """
    簡易評価器:
      - "git.diff:docs" → docs/ に差分があれば True
      - event 文字列の完全一致（手動トリガー用）
    """
    if event and event == when:
        return True
    if when == "git.diff:docs":
        return _git_diff_changed_under("docs/")
    return False


def run_automations(event: Optional[str] = None) -> Dict[str, Any]:
    """
    automations.triggers を走査し、条件成立したものの steps を順に実行。
    """
    gov = load_governance()
    triggers = (gov.get("automations", {}) or {}).get("triggers", []) or []

    fired: List[str] = []
    results: List[Dict[str, Any]] = []

    for trg in triggers:
        when = trg.get("when", "")
        if not when:
            continue
        if _eval_when(event, when):
            fired.append(trg.get("id") or when)
            for st in trg.get("steps") or []:
                if "run" in st:
                    results.append(_run_tool(gov, st))
                elif "remember" in st:
                    results.append(_remember(st))
                elif "suggest" in st:
                    results.append(_suggest(st))

    return {"fired": fired, "results": results}


def main() -> None:
    ap = argparse.ArgumentParser(description="Noctria Agent Automations Runner")
    ap.add_argument(
        "--event",
        help="force trigger match like 'git.diff:docs' or 'precommit.blocked:pytest-heavy'",
    )
    args = ap.parse_args()
    out = run_automations(event=args.event)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
