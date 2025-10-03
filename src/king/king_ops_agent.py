# [NOCTRIA_CORE_REQUIRED]
#!/usr/bin/env python3
# coding: utf-8
"""
king_ops_agent.py — 王(KingOps)の最小実装

目的:
  - 入力コンテキスト（ハンドオフ/課題など）から、開発プロマネ計画を生成
  - JSON(機械可読) と Markdown(可読) の両方を返す
  - trace_id を一貫利用
  - 依存は httpx のみ（OpenAI互換APIにPOST）

I/O:
  run_once(context:str, model_hint:str|None, trace_id:str|None) -> dict
    {
      "trace_id": "...",
      "plan": {...},        # JSON (priorities/next_actions/risks など)
      "markdown": "..."     # 人が読む用のMD
    }

設定:
  OPENAI_API_KEY, OPENAI_API_BASE(または OPENAI_BASE_URL), NOCTRIA_GPT_MODEL
  docs/governance/king_ops_prompt.yaml を優先ロード。無ければ内蔵プロンプトで代替。
"""

from __future__ import annotations

import dataclasses as dc
import datetime as dt
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

ROOT = Path(__file__).resolve().parents[1].parents[0]
PROMPT_PATH = ROOT / "docs" / "governance" / "king_ops_prompt.yaml"


def _load_yaml_prompt() -> str:
    try:
        import yaml  # type: ignore

        if PROMPT_PATH.exists():
            data = yaml.safe_load(PROMPT_PATH.read_text(encoding="utf-8"))
            # 代表的な置き場: data["charter"] or data["system_prompt"]
            if isinstance(data, dict):
                if "system_prompt" in data:
                    return str(data["system_prompt"])
                # 簡易合成
                charter = data.get("charter", {})
                principles = data.get("principles", [])
                return (
                    f"あなたはNoctria王のプロマネAI。\n"
                    f"役割: {charter.get('role', '')}\n"
                    f"使命: {charter.get('mission', '')}\n"
                    f"原則: " + " / ".join(map(str, principles))
                )
    except Exception:
        pass
    # フォールバックの最小プロンプト
    return (
        "あなたはNoctria王のプロマネAI。簡潔・実務優先で、実行可能な計画を出す。\n"
        "出力は JSON(厳密) と Markdown(簡潔) の二本立てで、JSONは以下のスキーマに沿うこと:\n"
        "{ priorities: [ {title, reason, eta_hours} ], next_actions: [ {title, owner, steps[]} ], risks: [ {name, mitigation} ], model }\n"
    )


@dc.dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    timeout: float = 60.0


def _llm_cfg(model_hint: Optional[str]) -> LLMConfig:
    api_key = os.getenv("OPENAI_API_KEY", "")
    base = (
        os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    )
    model = model_hint or os.getenv("NOCTRIA_GPT_MODEL") or "gpt-4o-mini"
    return LLMConfig(api_key=api_key, base_url=base.rstrip("/"), model=model)


def _make_trace_id(user_trace: Optional[str]) -> str:
    if user_trace:
        return user_trace
    return dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ") + "-" + str(uuid.uuid4()).lower()


def _chat_completion(cfg: LLMConfig, system_prompt: str, user_content: str) -> str:
    """OpenAI互換 /v1/chat/completions にPOSTし、textを返す。"""
    url = f"{cfg.base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"}
    payload = {
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.3,
        "max_tokens": 1200,
        "stream": False,
    }
    with httpx.Client(timeout=cfg.timeout) as cli:
        r = cli.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
    # provider差吸収
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    text = msg.get("content") or choice.get("text") or ""
    return text


_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_json(text: str) -> Dict[str, Any]:
    # ```json ... ``` 優先
    m = _JSON_BLOCK_RE.search(text)
    raw = m.group(1) if m else text
    # 末尾のノイズを可能な範囲で除去
    raw = raw.strip()
    # JSONでなければ失敗し、呼び出し側でフォールバック
    return json.loads(raw)


def _coerce_plan(obj: Dict[str, Any], model: str) -> Dict[str, Any]:
    def _ls(x, key):
        return x.get(key) if isinstance(x.get(key), list) else []

    plan = {
        "model": model,
        "priorities": [],
        "next_actions": [],
        "risks": [],
    }
    for it in _ls(obj, "priorities"):
        if isinstance(it, dict):
            plan["priorities"].append(
                {
                    "title": str(it.get("title", "")).strip(),
                    "reason": str(it.get("reason", "")).strip(),
                    "eta_hours": float(it.get("eta_hours", 0))
                    if str(it.get("eta_hours", "")).replace(".", "", 1).isdigit()
                    else 0.0,
                }
            )
    for it in _ls(obj, "next_actions"):
        if isinstance(it, dict):
            steps = it.get("steps", [])
            if not isinstance(steps, list):
                steps = []
            plan["next_actions"].append(
                {
                    "title": str(it.get("title", "")).strip(),
                    "owner": str(it.get("owner", "KingOps")).strip() or "KingOps",
                    "steps": [str(s).strip() for s in steps],
                }
            )
    for it in _ls(obj, "risks"):
        if isinstance(it, dict):
            plan["risks"].append(
                {
                    "name": str(it.get("name", "")).strip(),
                    "mitigation": str(it.get("mitigation", "")).strip(),
                }
            )
    return plan


def _render_md(trace_id: str, plan: Dict[str, Any]) -> str:
    lines = [
        f"# KingOps 計画 (trace_id: {trace_id})",
        "",
        "## 優先タスク",
    ]
    for i, p in enumerate(plan.get("priorities", []), 1):
        lines += [f"{i}. **{p['title']}** — 理由: {p['reason']} / 目安: ~{p['eta_hours']}h"]
    lines += ["", "## 次アクション"]
    for i, a in enumerate(plan.get("next_actions", []), 1):
        lines += [f"{i}. **{a['title']}** (owner: {a['owner']})"]
        for s in a.get("steps", []):
            lines += [f"   - {s}"]
    lines += ["", "## リスクと軽減策"]
    for i, r in enumerate(plan.get("risks", []), 1):
        lines += [f"{i}. **{r['name']}** — {r['mitigation']}"]
    lines += ["", f"モデル: `{plan.get('model', '')}`"]
    return "\n".join(lines).strip() + "\n"


def run_once(
    *, context: str, model_hint: Optional[str] = None, trace_id: Optional[str] = None
) -> Dict[str, Any]:
    cfg = _llm_cfg(model_hint)
    t_id = _make_trace_id(trace_id)
    system_prompt = _load_yaml_prompt()
    # ユーザー入力の包み紙（簡潔指示）
    user = (
        "以下の情報を基に、次の形式で実行可能なPM計画を作ってください。\n"
        "1) priorities: 3〜5件、各title/reason/eta_hours。\n"
        "2) next_actions: 3〜8件、各title/owner(既定KingOps)/steps(具体的タスク)。\n"
        "3) risks: 2〜5件、name/mitigation。\n"
        "出力はまずJSON、続けて簡潔なMarkdown。可能ならJSONを```jsonで囲ってください。\n\n"
        f"=== CONTEXT START ===\n{context}\n=== CONTEXT END ==="
    )
    text = _chat_completion(cfg, system_prompt, user)

    # JSON抽出
    try:
        raw = _extract_json(text)
    except Exception:
        # 最低限のフォールバック
        raw = {"priorities": [], "next_actions": [], "risks": [], "model": cfg.model}

    plan = _coerce_plan(raw, model=cfg.model)
    md = _render_md(t_id, plan)
    return {"trace_id": t_id, "plan": plan, "markdown": md}
