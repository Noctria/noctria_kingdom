# src/hermes/strategy_generator.py
# [NOCTRIA_CORE_REQUIRED]
#!/usr/bin/env python3
# coding: utf-8

"""
🦉 Hermes Cognitor — LLM 戦略コード生成（KEEP-safe版）

目的:
- 既存実装（LLMで戦略コード生成 → 保存 → DB記録）を安全ラッパで包む。
- 重依存（transformers / torch / psycopg2）は **遅延import**。Airflow DAG import を阻害しない。
- 例外時は **HOLD**（副作用なし）／必要に応じて **軽量フォールバック**で継続。
- 生成物の保存は **一時ファイル → os.replace** による原子的更新。
- `trace_id` を自動生成し、`obs_event` で主要ステージを記録。
- CLI: `--symbol` / `--tag` / `--target-metric` / `--dry-run` / `--safe-mode` / `--seed` / `--out` / `--json`.

戻り値契約 (dict):
{
  "trace_id": str,
  "created_at": iso8601,
  "symbol": str,
  "tag": str,
  "target_metric": str,
  "strategy_path": str|None,
  "prompt": str,
  "code": str,
  "meta": {
    "fallback": bool,
    "safe_mode": bool,
    "dry_run": bool,
    "model_dir": str|None,
  }
}
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# ========== 軽量ユーティリティ（遅延import, 観測ログ, パス） ====================


def _lazy_import(name: str):
    try:
        __import__(name)
        return sys.modules[name]
    except Exception:
        return None


def _safe_import_path_config():
    mod = _lazy_import("src.core.path_config") or _lazy_import("core.path_config")
    # 既存コード互換: HERMES_MODELS_DIR, LOGS_DIR, STRATEGIES_DIR を期待
    if mod:
        return {
            "HERMES_MODELS_DIR": getattr(mod, "HERMES_MODELS_DIR", None),
            "LOGS_DIR": getattr(mod, "LOGS_DIR", None),
            "STRATEGIES_DIR": getattr(mod, "STRATEGIES_DIR", None),
        }
    # フォールバック（相対ベース）
    root = Path(__file__).resolve().parents[2]
    return {
        "HERMES_MODELS_DIR": root / "models" / "hermes",
        "LOGS_DIR": root / "logs",
        "STRATEGIES_DIR": root / "src" / "strategies",
    }


def _safe_import_logger():
    # 既存の logger 初期化に合わせる（なければ簡易 logger）
    mod = _lazy_import("src.core.logger") or _lazy_import("core.logger")
    paths = _safe_import_path_config()
    log_path = (
        (paths["LOGS_DIR"] or (Path(__file__).resolve().parents[2] / "logs"))
        / "hermes"
        / "generator.log"
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)

    if mod and hasattr(mod, "setup_logger"):
        return mod.setup_logger("HermesGenerator", log_path)  # type: ignore[attr-defined]
    # フォールバック
    import logging

    logger = logging.getLogger("HermesGenerator")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(str(log_path), encoding="utf-8")
        fmt = logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s")
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        # 標準出力にも出す
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    return logger


def _safe_import_obs():
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


LOGGER = _safe_import_logger()
PATHS = _safe_import_path_config()
mk_trace_id, obs_event = _safe_import_obs()

# ========== 既存互換：環境変数（DB, モデルパス） ===============================

DB_NAME = os.getenv("POSTGRES_DB", "airflow")
DB_USER = os.getenv("POSTGRES_USER", "airflow")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "airflow")
DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

# 既存コードでは HERMES_MODELS_DIR / "nous-hermes-2" を想定
_default_models_dir = PATHS["HERMES_MODELS_DIR"] or (
    Path(__file__).resolve().parents[2] / "models" / "hermes"
)
MODEL_PATH = os.getenv("MODEL_DIR", str(_default_models_dir / "nous-hermes-2"))

# ========== 乱数シード =========================================================


def _set_seed(seed: Optional[int]) -> None:
    try:
        import numpy as _np  # type: ignore

        _np.random.seed(seed if seed is not None else 42)
    except Exception:
        pass
    try:
        import torch as _torch  # type: ignore

        if seed is None:
            seed = 42
        _torch.manual_seed(seed)
        if _torch.cuda.is_available():
            _torch.cuda.manual_seed_all(seed)
    except Exception:
        pass
    random.seed(seed if seed is not None else 42)


# ========== 原子的保存 =========================================================


def _atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", delete=False, dir=str(path.parent), encoding=encoding
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


# ========== LLM ロード（遅延import & HOLD/フォールバック） ====================


def _load_llm_model(model_path: str) -> Tuple[Any, Any]:
    """
    transformers / torch を遅延import。モデル未配置・壊れは例外→上位でフォールバック。
    """
    from pathlib import Path as _Path

    if not _Path(model_path).exists():
        raise FileNotFoundError(f"Model directory not found: {model_path}")

    trf = _lazy_import("transformers")
    if trf is None:
        raise RuntimeError("transformers is not available")

    # torch は `generate` 用に必要だが import は遅延
    _torch = _lazy_import("torch")
    if _torch is None:
        raise RuntimeError("torch is not available")

    LOGGER.info(f"🧠 LLMモデルをロード中: {model_path}")
    AutoModelForCausalLM = getattr(trf, "AutoModelForCausalLM")
    AutoTokenizer = getattr(trf, "AutoTokenizer")
    model = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True)
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    LOGGER.info("✅ LLMモデルのロード完了")
    return model, tokenizer


# ========== プロンプト生成（既存互換） =========================================


def build_prompt(symbol: str, tag: str, target_metric: str) -> str:
    prompt = (
        f"あなたはプロの金融エンジニアです。通貨ペア'{symbol}'を対象とし、"
        f"'{tag}'という特性を持つ取引戦略をPythonで記述してください。"
        f"この戦略は特に'{target_metric}'という指標を最大化することを目的とします。"
        "コードには、戦略のロジックを実装した`simulate()`関数を含めてください。"
    )
    LOGGER.info(f"📝 生成されたプロンプト: {prompt[:100]}...")
    return prompt


# ========== フォールバック戦略コード ===========================================


def _fallback_strategy_code(symbol: str, tag: str, target_metric: str) -> str:
    # シンプルな simulate() スタブ（安全・軽量）
    return f'''# Hermes fallback strategy (symbol={symbol}, tag={tag}, target_metric={target_metric})
def simulate(prices, params=None):
    """
    Minimal fallback strategy.
    - Buys if price above simple MA; otherwise holds.
    - This is a placeholder until full LLM pipeline is available.
    """
    if not prices:
        return {{}}
    ma = sum(prices[-5:]) / max(1, min(5, len(prices)))
    last = prices[-1]
    action = "BUY" if last > ma else "HOLD"
    return {{"action": action, "reason": "fallback-ma-check", "meta": {{"ma": ma, "last": last}}}}
'''


# ========== 戦略生成（LLM / フォールバック） ===================================


def generate_strategy_code(
    prompt: str, *, model_path: Optional[str] = None, safe_mode: bool = False
) -> Tuple[str, bool]:
    """
    戦略コード文字列と fallback 使用の有無(bool) を返す。
    safe_mode=True の場合は LLM を使わず即フォールバック。
    model_path が未指定なら既定の MODEL_PATH を使用（GUIの後方互換）。
    """
    # 既定のモデルパス解決（後方互換）
    model_path = model_path or MODEL_PATH

    if safe_mode:
        LOGGER.warning("⚠️ safe_mode: フォールバック戦略コードを返します")
        return _fallback_strategy_code("UNKNOWN", "safe_mode", "N/A"), True

    try:
        model, tokenizer = _load_llm_model(model_path)
        trf = _lazy_import("transformers")
        _torch = _lazy_import("torch")
        assert trf is not None and _torch is not None

        inputs = tokenizer(prompt, return_tensors="pt")
        with _torch.no_grad():
            outputs = model.generate(
                inputs["input_ids"],
                max_new_tokens=1024,
                pad_token_id=getattr(tokenizer, "eos_token_id", None),
            )
        generated = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # 安全にPythonコード部分を抽出（def simulate 以降を優先）
        match = re.search(r"(def\s+simulate\(.*)", generated, re.DOTALL)
        code_only = match.group(1).strip() if match else generated.strip()
        LOGGER.info("🤖 Hermesによる戦略コードの生成完了")
        return code_only, False

    except Exception as e:
        # HOLD: モデル未配置や依存欠如など → フォールバックへ
        LOGGER.error(f"🚨 LLM生成に失敗（フォールバックへ）: {e}", exc_info=True)
        return _fallback_strategy_code("UNKNOWN", "fallback_error", "N/A"), True


# ========== DB 保存（遅延import & 失敗はログのみで継続） =======================


def save_to_db(prompt: str, response: str) -> bool:
    """
    DB への保存。失敗しても例外を投げず False を返す（HOLD方針）。
    """
    try:
        psycopg2 = _lazy_import("psycopg2")
        if psycopg2 is None:
            raise RuntimeError("psycopg2 is not available")
        conn = psycopg2.connect(  # type: ignore[attr-defined]
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO hermes_outputs (prompt, response, created_at) VALUES (%s, %s, %s)",
                    (prompt, response, dt.datetime.now()),
                )
        LOGGER.info("✅ 生成結果をDBに保存しました。")
        return True
    except Exception as e:
        LOGGER.error(f"🚨 DB保存に失敗（継続）: {e}", exc_info=True)
        return False


# ========== ファイル保存（原子的） =============================================


def save_to_file(code: str, tag: str, out: Optional[Path] = None) -> Path:
    now = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"hermes_{tag}_{now}.py"
    strategies_dir = PATHS["STRATEGIES_DIR"] or (
        Path(__file__).resolve().parents[2] / "src" / "strategies"
    )
    save_dir = strategies_dir / "hermes_generated"
    target = out if out is not None else (save_dir / filename)
    _atomic_write_text(Path(target), code)
    LOGGER.info(f"💾 戦略をファイルに保存しました: {target}")
    return Path(target)


# ========== メインの高水準API ===================================================


def run_generation(
    *,
    symbol: str,
    tag: str,
    target_metric: str,
    model_dir: str,
    dry_run: bool = False,
    safe_mode: bool = False,
    seed: Optional[int] = None,
    out: Optional[Path] = None,
) -> Dict[str, Any]:
    trace_id = mk_trace_id()
    obs_event(
        "hermes.codegen.start",
        severity="LOW",
        trace_id=trace_id,
        meta={
            "symbol": symbol,
            "tag": tag,
            "target_metric": target_metric,
            "dry_run": dry_run,
            "safe_mode": safe_mode,
        },
    )

    _set_seed(seed)

    prompt = build_prompt(symbol, tag, target_metric)
    code, used_fallback = generate_strategy_code(prompt, model_path=model_dir, safe_mode=safe_mode)

    # 生成物保存（dry-run は保存しない）
    strategy_path: Optional[Path] = None
    if not dry_run:
        try:
            strategy_path = save_to_file(code, tag, out=out)
        except Exception as e:
            # 保存失敗は重大だが、ここでは HOLD とし副作用最小化
            obs_event(
                "hermes.codegen.save_error",
                severity="HIGH",
                trace_id=trace_id,
                meta={"exc": repr(e)},
            )
            LOGGER.error(f"🚨 戦略ファイル保存に失敗: {e}", exc_info=True)
            strategy_path = None

    # DB 記録（失敗しても継続）
    _ = save_to_db(prompt, code)

    obs_event(
        "hermes.codegen.done",
        severity="LOW",
        trace_id=trace_id,
        meta={"fallback": used_fallback, "path": str(strategy_path) if strategy_path else None},
    )

    return {
        "trace_id": trace_id,
        "created_at": dt.datetime.utcnow().isoformat() + "Z",
        "symbol": symbol,
        "tag": tag,
        "target_metric": target_metric,
        "strategy_path": str(strategy_path) if strategy_path else None,
        "prompt": prompt,
        "code": code,
        "meta": {
            "fallback": used_fallback,
            "safe_mode": safe_mode,
            "dry_run": dry_run,
            "model_dir": model_dir,
        },
    }


# ========== CLI ================================================================


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Hermes Cognitor — LLM Strategy Generator (KEEP-safe)")
    p.add_argument("--symbol", default="USDJPY", help="通貨ペア（例: USDJPY, EURJPY）")
    p.add_argument(
        "--tag", default="trend_breakout", help="戦略タグ（例: momentum, mean_reversion）"
    )
    p.add_argument("--target-metric", default="win_rate", help="最適化指標（例: win_rate, sharpe）")
    p.add_argument("--model-dir", default=MODEL_PATH, help="ローカル LLM モデルディレクトリ")
    p.add_argument("--dry-run", action="store_true", help="保存を行わない（試行）")
    p.add_argument("--safe-mode", action="store_true", help="LLMを使わずフォールバック生成を強制")
    p.add_argument("--seed", type=int, default=None, help="乱数シード")
    p.add_argument("--out", type=str, default=None, help="保存先パス（.py）")
    p.add_argument("--json", action="store_true", help="結果をJSONで標準出力")
    return p.parse_args(argv or sys.argv[1:])


def main(argv: Optional[list[str]] = None) -> int:
    ns = _parse_args(argv)
    try:
        result = run_generation(
            symbol=ns.symbol,
            tag=ns.tag,
            target_metric=ns.target_metric,
            model_dir=ns.model_dir,
            dry_run=ns.dry_run,
            safe_mode=ns.safe_mode,
            seed=ns.seed,
            out=Path(ns.out) if ns.out else None,
        )
        if ns.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            LOGGER.info("🦉 Hermes大臣による自動戦略生成完了")
        return 0
    except Exception as e:
        # HOLD: 失敗時は副作用なしで安全終了（必要情報はログ/obsに残す）
        tid = mk_trace_id()
        obs_event(
            "hermes.codegen.unhandled", severity="CRITICAL", trace_id=tid, meta={"exc": repr(e)}
        )
        LOGGER.error(f"🚨 予期せぬエラー: {e}", exc_info=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
