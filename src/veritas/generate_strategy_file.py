# src/veritas/generate_strategy_file.py
# [NOCTRIA_CORE_REQUIRED]
#!/usr/bin/env python3
# coding: utf-8

"""
🛠️ Veritas Machina 戦略ファイル生成（KEEP-safe, merged）

目的
- ML系のシンプル戦略テンプレを**原子的に保存**する（既存挙動を維持）。
- オプションで Veritas の本体（machina）/ LLM に**委譲して実戦コード**を生成（保存まで）。
- Airflow/DAG importを壊さないため **重依存は遅延import**、失敗時は **HOLD→テンプレ**にフォールバック。
- すべての操作を `trace_id` と `obs_event` で観測ログ化。

CLI 例
  # 既存と同じテンプレ生成（デフォルト）
  python -m src.veritas.generate_strategy_file --name veritas_strategy

  # 保存先を明示
  python -m src.veritas.generate_strategy_file --name breakout --out-dir src/strategies/veritas_generated

  # Veritas本体で生成（machina優先→LLM→テンプレ）
  python -m src.veritas.generate_strategy_file --name momo --mode machina --pair USD/JPY --tag momentum_core

  # LLMモデルを指定してmachina経由で生成（存在すれば使用）
  python -m src.veritas.generate_strategy_file --mode machina --pair EUR/JPY --tag breakout --model-dir /models/local-llm

"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

# ---------------- sys.path 調整（既存互換） ----------------
_SRC = Path(__file__).resolve().parents[1]  # src/
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


# ---------------- 小ユーティリティ（遅延import / パス / ロガー / 観測ログ） -----
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
            "STRATEGIES_DIR": getattr(mod, "STRATEGIES_DIR", root / "src" / "strategies"),
            "LOGS_DIR": getattr(mod, "LOGS_DIR", root / "logs"),
        }
    return {
        "ROOT": root,
        "STRATEGIES_DIR": root / "src" / "strategies",
        "LOGS_DIR": root / "logs",
    }


def _logger():
    mod = _lazy_import("src.core.logger") or _lazy_import("core.logger")
    p = _paths()
    log_path = Path(p["LOGS_DIR"]) / "veritas" / "generator_file.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if mod and hasattr(mod, "setup_logger"):
        return mod.setup_logger("VeritasGenFile", log_path)  # type: ignore[attr-defined]
    import logging

    lg = logging.getLogger("VeritasGenFile")
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
        mk_trace_id_f = getattr(mod, "mk_trace_id", mk_trace_id)  # type: ignore
        obs_event_f = getattr(mod, "obs_event", obs_event)  # type: ignore
        return mk_trace_id_f, obs_event_f
    return mk_trace_id, obs_event


LOGGER = _logger()
PATHS = _paths()
mk_trace_id, obs_event = _obs()


# ---------------- 原子的保存 ---------------------------------------------------
def _atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", delete=False, dir=str(path.parent), encoding=encoding
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


# ---------------- 既存テンプレ（そのまま維持） ---------------------------------
STRATEGY_TEMPLATE = """\
import pandas as pd
import numpy as np

def simulate(data: pd.DataFrame) -> dict:
    \"""
    RSIとspreadに基づいたML的なシンプル戦略
    BUY: RSI > 50 and spread < 2
    SELL: RSI < 50 or spread > 2
    \"""
    capital = 1_000_000
    position = 0
    entry_price = 0
    wins = 0
    losses = 0
    capital_history = [capital]

    for i in range(1, len(data)):
        rsi = data.loc[i, 'RSI(14)']
        spread = data.loc[i, 'spread']
        price = data.loc[i, 'price']

        if position == 0 and rsi > 50 and spread < 2:
            position = capital / price
            entry_price = price

        elif position > 0 and (rsi < 50 or spread > 2):
            exit_price = price
            new_capital = position * exit_price
            if new_capital > capital:
                wins += 1
            else:
                losses += 1
            capital = new_capital
            capital_history.append(capital)
            position = 0

    if position > 0:
        capital = position * data.iloc[-1]['price']
        capital_history.append(capital)

    total_trades = wins + losses
    win_rate = wins / total_trades if total_trades > 0 else 0.0
    peak = capital_history[0]
    max_drawdown = 0.0

    for val in capital_history:
        if val > peak:
            peak = val
        dd = (peak - val) / peak
        max_drawdown = max(max_drawdown, dd)

    return {
        "final_capital": round(capital),
        "win_rate": round(win_rate, 4),
        "max_drawdown": round(max_drawdown, 4),
        "total_trades": total_trades
    }
"""


# ---------------- テンプレを保存 ----------------------------------------------
def generate_strategy_file(
    strategy_name: str, *, out_dir: Optional[Path] = None, content: Optional[str] = None
) -> Path:
    """
    既存のテンプレ生成をKEEP-safe化（原子的保存＋obsログ）
    """
    trace_id = mk_trace_id()
    obs_event(
        "veritas.genfile.start", trace_id=trace_id, meta={"name": strategy_name, "mode": "template"}
    )

    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{strategy_name}_{ts}.py"
    base_dir = Path(out_dir) if out_dir else (Path(PATHS["STRATEGIES_DIR"]) / "veritas_generated")
    dest = base_dir / filename

    text = content if content is not None else STRATEGY_TEMPLATE
    _atomic_write_text(dest, text)

    LOGGER.info(f"💾 ML戦略ファイルを保存: {dest}")
    obs_event(
        "veritas.genfile.done", trace_id=trace_id, meta={"path": str(dest), "mode": "template"}
    )
    print(f"👑 ML戦略ファイルを王国に記録しました：{dest}")
    return dest


# ---------------- machina/LLM 経由の生成（任意） -------------------------------
def generate_via_machina(
    *,
    name: str,
    pair: str = "USD/JPY",
    tag: str = "momentum_core",
    profile: Optional[str] = None,
    model_dir: Optional[str] = None,
    safe_mode: bool = False,
    out_dir: Optional[Path] = None,
) -> Path:
    """
    Veritas 本体へ委譲して戦略コードを生成・保存（保存は本体側でも行うが、明示 out_dir がある場合は上書き保存）。
    """
    trace_id = mk_trace_id()
    obs_event(
        "veritas.genfile.machina.start",
        trace_id=trace_id,
        meta={"name": name, "pair": pair, "tag": tag, "profile": profile, "safe_mode": safe_mode},
    )

    # 遅延import: run_generation
    sg = _lazy_import("src.veritas.strategy_generator") or _lazy_import(
        "veritas.strategy_generator"
    )
    if not sg or not hasattr(sg, "run_generation"):
        # HOLD → テンプレ
        LOGGER.warning("veritas.strategy_generator が見つからないためテンプレにフォールバック")
        return generate_strategy_file(name, out_dir=out_dir)

    result = sg.run_generation(  # type: ignore[attr-defined]
        pair=pair,
        tag=tag,
        profile=profile,
        model_dir=model_dir,
        dry_run=False,
        safe_mode=safe_mode,
        seed=None,
        out_dir=(Path(out_dir) if out_dir else None),
    )

    # run_generation は自前で保存済み。path があればそれを使う。
    saved_path = result.get("path")
    code = result.get("code", "")
    if out_dir:
        # 指定があれば再保存（原子的）
        ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
        dest = Path(out_dir) / f"{name}_{ts}.py"
        _atomic_write_text(dest, code or "# empty")
        saved_path = str(dest)

    obs_event(
        "veritas.genfile.machina.done",
        trace_id=trace_id,
        meta={"path": saved_path, "via": result.get("meta", {}).get("via")},
    )
    LOGGER.info(f"🦅 Veritas本体で戦略生成: {saved_path}")
    print(f"👑 戦略ファイルを王国に記録しました：{saved_path}")
    return (
        Path(saved_path)
        if saved_path
        else generate_strategy_file(name, out_dir=out_dir, content=code or STRATEGY_TEMPLATE)
    )


# ---------------- CLI ---------------------------------------------------------
def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate Veritas strategy file (KEEP-safe, merged)")
    p.add_argument(
        "--name",
        default="veritas_strategy",
        help="戦略ファイルのベース名（拡張子・日時は自動付与）",
    )
    p.add_argument(
        "--out-dir",
        default=None,
        help="保存先ディレクトリ。未指定なら strategies/veritas_generated",
    )
    p.add_argument("--mode", choices=["template", "machina"], default="template", help="生成モード")
    # machina モード用オプション
    p.add_argument("--pair", default="USD/JPY")
    p.add_argument("--tag", default="momentum_core")
    p.add_argument("--profile", default=None)
    p.add_argument("--model-dir", default=os.getenv("VERITAS_LLM_DIR", None))
    p.add_argument(
        "--safe-mode",
        action="store_true",
        help="LLM/重依存を使わずテンプレ生成を強制（machina経由時も有効）",
    )
    p.add_argument("--json", action="store_true", help="結果をJSONで標準出力（pathなど）")
    return p.parse_args(argv or sys.argv[1:])


def main(argv: Optional[list[str]] = None) -> int:
    ns = _parse_args(argv)
    out_dir = Path(ns.out_dir) if ns.out_dir else None
    try:
        if ns.mode == "machina":
            path = generate_via_machina(
                name=ns.name,
                pair=ns.pair,
                tag=ns.tag,
                profile=ns.profile,
                model_dir=ns.model_dir,
                safe_mode=ns.safe_mode,
                out_dir=out_dir,
            )
        else:
            path = generate_strategy_file(ns.name, out_dir=out_dir)

        if ns.json:
            print(json.dumps({"path": str(path)}, ensure_ascii=False))
        return 0
    except Exception as e:
        tid = mk_trace_id()
        obs_event(
            "veritas.genfile.unhandled", severity="CRITICAL", trace_id=tid, meta={"exc": repr(e)}
        )
        LOGGER.error(f"予期せぬエラー: {e}", exc_info=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
