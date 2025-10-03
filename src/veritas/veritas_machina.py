# src/veritas/veritas_machina.py
# [NOCTRIA_CORE_REQUIRED]
#!/usr/bin/env python3
# coding: utf-8

"""
🧪 Veritas Machina — 生成ロジック本体（KEEP-safe）

役割
- Veritas の戦略生成エンジン本体。caller（strategy_generator.py）から委譲される。
- 依存はすべて遅延import。失敗しても HOLD（テンプレ/ヒューリスティックにフォールバック）。
- 生成コードは `simulate(prices, params=None)` を含む。

I/F
- generate_strategy(inputs: dict) -> {"code": str, "meta": dict}
  inputs 期待キー:
    - pair: str                # "USD/JPY" 等
    - tag: str                 # "momentum_core" 等
    - profile: Optional[str]   # "default", "conservative" 等
    - model_dir: Optional[str] # LLM ディレクトリ（任意）
    - safe_mode: bool          # True なら即テンプレ
    - seed: Optional[int]      # 決定性制御（任意）
"""

from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# --- src を sys.path に追加 ----------------------------------------------------
_SRC = Path(__file__).resolve().parents[1]  # src/
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# ===== ユーティリティ（遅延import / ロガー / パス / 観測ログ） =================


def _lazy_import(name: str):
    try:
        __import__(name)
        return sys.modules[name]
    except Exception:
        return None


def _paths():
    mod = _lazy_import("core.path_config") or _lazy_import("src.core.path_config")
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
    mod = _lazy_import("core.logger") or _lazy_import("src.core.logger")
    paths = _paths()
    log_path = Path(paths["LOGS_DIR"]) / "veritas" / "machina.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if mod and hasattr(mod, "setup_logger"):
        return mod.setup_logger("VeritasMachina", log_path)  # type: ignore[attr-defined]
    import logging

    lg = logging.getLogger("VeritasMachina")
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
    mod = _lazy_import("plan_data.observability") or _lazy_import("src.plan_data.observability")
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
        mk_trace_id = getattr(mod, "mk_trace_id", mk_trace_id)  # type: ignore
        obs_event = getattr(mod, "obs_event", obs_event)  # type: ignore
    return mk_trace_id, obs_event


LOGGER = _logger()
PATHS = _paths()
mk_trace_id, obs_event = _obs()

# ===== シード制御 =============================================================


def _set_seed(seed: Optional[int]) -> None:
    try:
        import numpy as _np  # type: ignore

        _np.random.seed(seed if seed is not None else 42)
    except Exception:
        pass
    try:
        torch = _lazy_import("torch")
        if torch is not None:
            s = 42 if seed is None else seed
            torch.manual_seed(s)  # type: ignore[attr-defined]
            if getattr(torch, "cuda", None) and torch.cuda.is_available():  # type: ignore[attr-defined]
                torch.cuda.manual_seed_all(s)  # type: ignore[attr-defined]
    except Exception:
        pass
    random.seed(seed if seed is not None else 42)


# ===== テンプレ & 簡易ジェネレーター ===========================================


def _load_template_text() -> str:
    candidates = [
        PATHS["ROOT"] / "src" / "veritas" / "generate" / "templates" / "strategy_template.py",
        PATHS["ROOT"] / "src" / "strategies" / "official" / "sample_strategy.py",
    ]
    for p in candidates:
        try:
            if Path(p).is_file():
                return Path(p).read_text(encoding="utf-8")
        except Exception:
            continue
    # 最小テンプレ
    return """# Generated Fallback Strategy
def simulate(prices, params=None):
    if not prices:
        return {}
    ma = sum(prices[-5:]) / max(1, min(5, len(prices)))
    signal = "BUY" if prices[-1] > ma else "SELL"
    return {"action": signal, "reason": "fallback-ma", "meta": {"ma": ma, "last": prices[-1]}}
"""


def _render_header(pair: str, tag: str, profile: Optional[str]) -> str:
    return f"# VeritasMachina strategy — pair={pair}, tag={tag}, profile={profile or 'default'}\n"


def _heuristic_strategy(pair: str, tag: str, profile: Optional[str]) -> str:
    """
    依存ゼロの決定論的ジェネレーター（SMA/EMA/RSI 風のシンプル合成）
    """
    header = _render_header(pair, tag, profile)
    body = r"""
from statistics import mean

def _sma(xs, n):
    n = max(1, min(n, len(xs)))
    return mean(xs[-n:]) if xs else 0.0

def _ema(xs, n):
    n = max(1, min(n, len(xs)))
    if not xs:
        return 0.0
    alpha = 2/(n+1)
    ema = xs[0]
    for x in xs[1:]:
        ema = alpha*x + (1-alpha)*ema
    return ema

def _rsi(xs, n=14):
    n = max(1, min(n, len(xs)))
    if len(xs) < 2:
        return 50.0
    gains, losses = [], []
    for i in range(1, n):
        diff = xs[-i] - xs[-i-1]
        (gains if diff > 0 else losses).append(abs(diff))
    avg_gain = (sum(gains)/len(gains)) if gains else 0.0
    avg_loss = (sum(losses)/len(losses)) if losses else 0.0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain/avg_loss
    return 100 - (100/(1+rs))

def simulate(prices, params=None):
    params = params or {}
    fast = int(params.get("fast", 5))
    slow = int(params.get("slow", 20))
    rsi_n = int(params.get("rsi_n", 14))

    if not prices or len(prices) < max(2, slow):
        return {"action": "HOLD", "reason": "insufficient-data", "meta": {}}

    sma_fast = _sma(prices, fast)
    sma_slow = _sma(prices, slow)
    ema_slow = _ema(prices, slow)
    rsi = _rsi(prices, rsi_n)
    last = prices[-1]

    # 合成シグナル（単純な重み付け）
    score = 0.0
    score += 1.0 if sma_fast > sma_slow else -1.0
    score += 0.5 if last > ema_slow else -0.5
    score += (rsi - 50.0)/50.0 * 0.5  # [-0.5, +0.5] スケール

    action = "BUY" if score > 0.2 else ("SELL" if score < -0.2 else "HOLD")
    return {
        "action": action,
        "reason": "heuristic-composite",
        "meta": {
            "sma_fast": sma_fast, "sma_slow": sma_slow, "ema_slow": ema_slow,
            "rsi": rsi, "last": last, "score": score
        },
    }
"""
    return header + body.lstrip()


# ===== LLM 統合（任意） =======================================================


def _try_llm(prompt: str, *, model_dir: Optional[str]) -> Optional[str]:
    """
    transformers/torch があり、model_dir が存在すれば LLM 生成を試みる。
    """
    if not model_dir:
        return None
    try:
        trf = _lazy_import("transformers")
        torch = _lazy_import("torch")
        if trf is None or torch is None:
            return None
        from pathlib import Path as _P

        if not _P(model_dir).exists():
            return None
        AutoModelForCausalLM = getattr(trf, "AutoModelForCausalLM")
        AutoTokenizer = getattr(trf, "AutoTokenizer")
        model = AutoModelForCausalLM.from_pretrained(model_dir, local_files_only=True)
        tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
        inputs = tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():  # type: ignore[attr-defined]
            tokens = model.generate(
                inputs["input_ids"],
                max_new_tokens=1024,
                pad_token_id=getattr(tokenizer, "eos_token_id", None),
            )
        text = tokenizer.decode(tokens[0], skip_special_tokens=True)
        m = re.search(r"(def\s+simulate\(.*)", text, re.DOTALL)
        return m.group(1).strip() if m else text.strip()
    except Exception as e:
        LOGGER.error(f"LLM生成に失敗: {e}", exc_info=True)
        return None


# ===== Public API =============================================================


def generate_strategy(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Public: strategy_generator から呼ばれる唯一の関数。
    戻り値: {"code": str, "meta": {...}}
    """
    pair: str = str(inputs.get("pair") or inputs.get("symbol") or "USD/JPY")
    tag: str = str(inputs.get("tag") or "momentum_core")
    profile: Optional[str] = inputs.get("profile")
    model_dir: Optional[str] = inputs.get("model_dir")
    safe_mode: bool = bool(inputs.get("safe_mode") or False)
    seed: Optional[int] = inputs.get("seed")

    _set_seed(seed)

    trace_id = mk_trace_id()
    obs_event(
        "veritas.machina.start",
        severity="LOW",
        trace_id=trace_id,
        meta={"pair": pair, "tag": tag, "profile": profile, "safe_mode": safe_mode},
    )

    meta: Dict[str, Any] = {
        "pair": pair,
        "tag": tag,
        "profile": profile,
        "via": None,
        "trace_id": trace_id,
    }

    # 1) safe-mode → テンプレ
    if safe_mode:
        base = _load_template_text()
        code = _render_header(pair, tag, profile) + base
        meta["via"] = "template_safe_mode"
        obs_event("veritas.machina.done", severity="LOW", trace_id=trace_id, meta=meta)
        return {"code": code, "meta": meta}

    # 2) LLM（任意）
    prompt = f"Create a robust FX strategy for {pair} with tag '{tag}', profile '{profile or 'default'}'. Include simulate(prices, params=None). Prefer readable Python."
    llm_code = _try_llm(prompt, model_dir=model_dir)
    if llm_code:
        meta["via"] = "llm"
        obs_event("veritas.machina.done", severity="LOW", trace_id=trace_id, meta=meta)
        return {"code": llm_code, "meta": meta}

    # 3) 依存ゼロのヒューリスティック
    code = _heuristic_strategy(pair, tag, profile)
    meta["via"] = "heuristic"
    obs_event("veritas.machina.done", severity="LOW", trace_id=trace_id, meta=meta)
    return {"code": code, "meta": meta}
