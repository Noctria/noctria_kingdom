# src/veritas/strategy_generator.py
# [NOCTRIA_CORE_REQUIRED]
#!/usr/bin/env python3
# coding: utf-8

"""
🛡️ Veritas Machina — ML 戦略コード生成（KEEP-safeラッパ）

- 既存API互換: build_prompt(prompt), generate_strategy_code(prompt) -> str,
              save_to_db(prompt, response) -> None, save_to_file(code, tag) -> str
- 中身は veritas_machina.generate_strategy(...) に委譲。
- 失敗時はフォールバックコードを返し、保存は原子的 (tmp -> os.replace)。
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# ------- 遅延import/パス/ロガー/obs --------------------------------------------


def _lazy_import(name: str):
    try:
        __import__(name)
        return sys.modules[name]
    except Exception:
        return None


def _paths() -> Dict[str, Path]:
    mod = _lazy_import("src.core.path_config") or _lazy_import("core.path_config")
    root = Path(__file__).resolve().parents[2]
    if mod:
        return {
            "ROOT": getattr(mod, "ROOT", root),
            "LOGS_DIR": getattr(mod, "LOGS_DIR", root / "logs"),
            "STRATEGIES_DIR": getattr(mod, "STRATEGIES_DIR", root / "src" / "strategies"),
            "VERITAS_MODELS_DIR": getattr(mod, "VERITAS_MODELS_DIR", root / "models" / "veritas"),
        }
    return {
        "ROOT": root,
        "LOGS_DIR": root / "logs",
        "STRATEGIES_DIR": root / "src" / "strategies",
        "VERITAS_MODELS_DIR": root / "models" / "veritas",
    }


def _logger():
    mod = _lazy_import("src.core.logger") or _lazy_import("core.logger")
    p = _paths()
    log_path = Path(p["LOGS_DIR"]) / "veritas" / "generator.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if mod and hasattr(mod, "setup_logger"):
        return mod.setup_logger("VeritasGenerator", log_path)  # type: ignore[attr-defined]
    import logging

    lg = logging.getLogger("VeritasGenerator")
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
        print("[OBS]", json.dumps(msg, ensure_ascii=False))

    if mod:
        return getattr(mod, "mk_trace_id", mk_trace_id), getattr(mod, "obs_event", obs_event)
    return mk_trace_id, obs_event


PATHS = _paths()
logger = _logger()
mk_trace_id, obs_event = _obs()

# ------- 環境変数 --------------------------------------------------------------

DB_NAME = os.getenv("POSTGRES_DB", "airflow")
DB_USER = os.getenv("POSTGRES_USER", "airflow")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "airflow")
DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
VERITAS_MODEL_DIR = Path(
    os.getenv("VERITAS_MODEL_DIR", str(PATHS["VERITAS_MODELS_DIR"] / "ml_model"))
)

# ------- 原子的保存 ------------------------------------------------------------


def _atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", delete=False, dir=str(path.parent), encoding=encoding
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


# ------- 既存I/F: プロンプト生成 ----------------------------------------------


def build_prompt(symbol: str, tag: str, target_metric: str) -> str:
    prompt = f"通貨ペア'{symbol}', 特性'{tag}', 目標指標'{target_metric}'に基づく取引戦略生成用パラメータ"
    logger.info(f"📝 生成されたパラメータ説明: {prompt}")
    return prompt


# ------- プロンプト解析（既存build_promptに整合） ------------------------------

_PROMPT_RE = re.compile(
    r"通貨ペア'(?P<symbol>[^']+)'.*?特性'(?P<tag>[^']+)'.*?目標指標'(?P<metric>[^']+)'", re.DOTALL
)


def _parse_prompt(prompt: str) -> Dict[str, str]:
    m = _PROMPT_RE.search(prompt)
    if not m:
        return {"symbol": "USDJPY", "tag": "default", "metric": "sharpe_ratio"}
    return {"symbol": m.group("symbol"), "tag": m.group("tag"), "metric": m.group("metric")}


# ------- 既存I/F: 戦略生成（machina に委譲） -----------------------------------

FALLBACK_CODE = """# Veritas fallback strategy code
def simulate(prices, params=None):
    if not prices:
        return {"action": "HOLD", "reason": "no-data", "meta": {}}
    ma = sum(prices[-5:]) / max(1, min(5, len(prices)))
    action = "BUY" if prices[-1] > ma else "SELL"
    return {"action": action, "reason": "fallback-ma", "meta": {"ma": ma, "last": prices[-1]}}
"""


def generate_strategy_code(prompt: str) -> str:
    trace_id = mk_trace_id()
    obs_event("veritas.wrapper.start", trace_id=trace_id, meta={"prompt_head": prompt[:80]})
    try:
        vm = _lazy_import("src.veritas.veritas_machina") or _lazy_import("veritas.veritas_machina")
        if not vm or not hasattr(vm, "generate_strategy"):
            raise RuntimeError("veritas_machina.generate_strategy not available")

        parsed = _parse_prompt(prompt)
        inputs = {
            "pair": parsed["symbol"],
            "tag": parsed["tag"],
            "profile": None,
            "model_dir": str(VERITAS_MODEL_DIR),
            "safe_mode": False,
            "seed": None,
        }
        res: Dict[str, Any] = vm.generate_strategy(inputs)  # type: ignore
        code = str(res.get("code") or "")
        if not code.strip():
            raise RuntimeError("empty code from machina")
        obs_event("veritas.wrapper.done", trace_id=trace_id, meta={"via": "machina"})
        logger.info("🤖 VeritasMachina 経由の戦略コード生成完了")
        return code
    except Exception as e:
        logger.error(f"[{trace_id}] Veritas wrapper 失敗、フォールバック適用: {e}", exc_info=True)
        obs_event(
            "veritas.wrapper.fallback", trace_id=trace_id, severity="MEDIUM", meta={"exc": repr(e)}
        )
        return FALLBACK_CODE


# ------- 既存I/F: DB 保存（ベストエフォート） ----------------------------------


def save_to_db(prompt: str, response: str) -> None:
    pg = _lazy_import("psycopg2")
    if not pg:
        logger.warning("psycopg2 が無いため DB保存をスキップ")
        return
    conn = None
    try:
        conn = pg.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
        )
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO veritas_outputs (prompt, response, created_at) VALUES (%s, %s, %s)",
                (prompt, response, datetime.now(timezone.utc)),
            )
            conn.commit()
        logger.info("✅ 生成結果をDBに保存しました。")
    except Exception as e:
        logger.error(f"🚨 DB保存に失敗（継続）: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()


# ------- 既存I/F: ファイル保存（原子的） ---------------------------------------


def save_to_file(code: str, tag: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"veritas_{tag}_{now}.py"
    save_dir = PATHS["STRATEGIES_DIR"] / "veritas_generated"
    dest = save_dir / filename
    try:
        _atomic_write_text(dest, code)
        logger.info(f"💾 戦略をファイルに保存しました: {dest}")
        return str(dest)
    except Exception as e:
        logger.error(f"戦略ファイル保存失敗: {e}", exc_info=True)
        return ""
