# noctria_gui/routes/hermes.py
# [NOCTRIA_CORE_REQUIRED]
#!/usr/bin/env python3
# coding: utf-8

import asyncio
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger("noctria.hermes")

# ========= 軽量ユーティリティ（DAG/GUIパース時は安全） ===========================


def _lazy_import(name: str):
    try:
        __import__(name)
        return sys.modules[name]
    except Exception:
        return None


def _paths() -> Dict[str, Path]:
    mod = _lazy_import("src.core.path_config") or _lazy_import("core.path_config")
    root = Path(__file__).resolve().parents[2]  # repo root を推定
    if mod:
        return {
            "ROOT": getattr(mod, "ROOT", root),
            "LOGS_DIR": getattr(mod, "LOGS_DIR", root / "logs"),
            "STRATEGIES_DIR": getattr(mod, "STRATEGIES_DIR", root / "src" / "strategies"),
        }
    return {
        "ROOT": root,
        "LOGS_DIR": root / "logs",
        "STRATEGIES_DIR": root / "src" / "strategies",
    }


def _obs():
    mod = _lazy_import("src.plan_data.observability") or _lazy_import("plan_data.observability")
    import datetime as dt

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
        # GUI実行でも標準出力に落としておく（収集しやすい）
        print("[OBS]", json.dumps(msg, ensure_ascii=False))

    if mod:
        mk_trace_id = getattr(mod, "mk_trace_id", mk_trace_id)  # type: ignore
        obs_event = getattr(mod, "obs_event", obs_event)  # type: ignore
    return mk_trace_id, obs_event


def _atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", delete=False, dir=str(path.parent), encoding=encoding
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


PATHS = _paths()
mk_trace_id, obs_event = _obs()

# ========= Pydantic I/O =======================================================


class HermesStrategyRequest(BaseModel):
    symbol: str
    tag: str
    target_metric: str


class HermesStrategyResponse(BaseModel):
    status: str
    strategy_code: str
    explanation: Optional[str] = None
    prompt: str
    saved_path: Optional[str] = None


# ========= フォールバック用テンプレ ============================================

FALLBACK_CODE = """# Hermes fallback strategy (KEEP-safe)
def simulate(prices, params=None):
    if not prices:
        return {"action": "HOLD", "reason": "no-data", "meta": {}}
    n = min(5, len(prices))
    ma = sum(prices[-n:]) / max(1, n)
    action = "BUY" if prices[-1] > ma else "SELL"
    return {"action": action, "reason": "fallback-ma", "meta": {"ma": ma, "last": prices[-1]}}
"""


def _fallback_build_prompt(symbol: str, tag: str, target_metric: str) -> str:
    return (
        f"あなたはプロの金融エンジニアです。通貨ペア'{symbol}'を対象に、"
        f"特性'{tag}'、評価指標'{target_metric}'を重視した戦略を設計してください。"
        "Pythonで simulate(prices, params=None) を含む関数を提示してください。"
    )


async def _safe_save_file(code: str, tag: str) -> str:
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = PATHS["STRATEGIES_DIR"] / "hermes_generated" / f"hermes_{tag}_{ts}.py"
    _atomic_write_text(dest, code)
    return str(dest)


# ========= コア処理（遅延 import + HOLD フォールバック） ========================


async def _run_hermes_generation(symbol: str, tag: str, target_metric: str) -> Dict[str, Any]:
    """
    Hermesの既存API（build_prompt/generate/save_...）が使えれば使う。
    使えない・失敗時はフォールバック（テンプレ）で **HOLD** 維持。
    """
    trace_id = mk_trace_id()
    obs_event(
        "gui.hermes.start",
        trace_id=trace_id,
        meta={"symbol": symbol, "tag": tag, "target_metric": target_metric},
    )

    # 遅延 import（重依存回避）
    hermes = _lazy_import("src.hermes.strategy_generator") or _lazy_import(
        "hermes.strategy_generator"
    )

    prompt = None
    code = None
    saved_path = None
    via = "fallback"

    try:
        if hermes and all(
            hasattr(hermes, k)
            for k in ("build_prompt", "generate_strategy_code", "save_to_file", "save_to_db")
        ):
            # 既存の I/F をそのまま使用（互換）
            prompt = await asyncio.to_thread(hermes.build_prompt, symbol, tag, target_metric)
            code = await asyncio.to_thread(hermes.generate_strategy_code, prompt)
            saved_path = await asyncio.to_thread(hermes.save_to_file, code, tag)
            # DBは失敗してもユーザー応答は返す（HOLD）
            try:
                await asyncio.to_thread(hermes.save_to_db, prompt, code)
            except Exception as e_db:
                logger.warning(f"[{trace_id}] Hermes DB保存に失敗（継続）: {e_db}")
            via = "hermes"
        else:
            # 互換APIが見つからない → フォールバック
            prompt = _fallback_build_prompt(symbol, tag, target_metric)
            code = FALLBACK_CODE
            saved_path = await _safe_save_file(code, tag)

        obs_event("gui.hermes.done", trace_id=trace_id, meta={"via": via, "path": saved_path})
        return {
            "prompt": prompt,
            "code": code,
            "path": saved_path,
            "via": via,
            "trace_id": trace_id,
        }

    except Exception as e:
        logger.error(f"[{trace_id}] Hermes生成処理で例外: {e}", exc_info=True)
        obs_event("gui.hermes.error", severity="HIGH", trace_id=trace_id, meta={"exc": repr(e)})
        # 最終フォールバック（必ず応答を返す）
        try:
            prompt = prompt or _fallback_build_prompt(symbol, tag, target_metric)
            code = code or FALLBACK_CODE
            saved_path = saved_path or await _safe_save_file(code, tag)
            return {
                "prompt": prompt,
                "code": code,
                "path": saved_path,
                "via": "fallback-error",
                "trace_id": trace_id,
            }
        except Exception as e2:
            logger.critical(f"[{trace_id}] フォールバック保存まで失敗: {e2}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Hermes生成に失敗しました（trace_id={trace_id}）"
            )


# ========= FastAPI ルート ======================================================


@router.post("/hermes/generate_strategy", response_model=HermesStrategyResponse)
async def generate_strategy(req: HermesStrategyRequest):
    """
    KEEP-safe:
      - hermes.strategy_generator を **遅延import**（GUI起動時の ImportError を回避）
      - 例外時は **HOLD**（フォールバックコードを原子的保存）
      - trace_id/obs_event で観測可能
    """
    result = await _run_hermes_generation(req.symbol, req.tag, req.target_metric)
    if not result or not result.get("code"):
        raise HTTPException(status_code=500, detail="Hermes生成失敗（空の結果）")

    explanation = (
        f"Hermes生成戦略：{req.symbol} / {req.tag} / {req.target_metric}（via={result.get('via')}）"
    )
    return HermesStrategyResponse(
        status="SUCCESS",
        strategy_code=result["code"],
        explanation=explanation,
        prompt=result["prompt"],
        saved_path=result.get("path"),
    )
