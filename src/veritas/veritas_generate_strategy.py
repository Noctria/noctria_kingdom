#!/usr/bin/env python3
# coding: utf-8

"""
✒️ Veritas Strategy Generator (v2.1)
- LLMからの指示に基づき、新しい戦略のPythonファイルを生成する。
- 固定テンプレートだが、将来的にはLLMがコード自体を生成する想定。
"""

import os
import re
import sys
import logging
from datetime import datetime
from pathlib import Path

# -------------------- パス解決の堅牢化 --------------------
# 1) 通常のパッケージ実行（python -m ...）でのインポート
# 2) 直接実行（python src/veritas/veritas_generate_strategy.py）時に備えて、
#    本ファイルの親ディレクトリからプロジェクトルートを推定して sys.path に追加
try:
    from src.core.path_config import STRATEGIES_VERITAS_GENERATED_DIR
except Exception:
    # スクリプトのある src/veritas/ から 2つ上がプロジェクトルート想定
    this_file = Path(__file__).resolve()
    project_root = this_file.parent.parent.parent  # -> <project>/
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))
    try:
        # ルート直下の core/ を想定（src を切らした起動に対応）
        from core.path_config import STRATEGIES_VERITAS_GENERATED_DIR
    except Exception as e:
        raise ImportError(
            "path_config の読み込みに失敗しました。PYTHONPATH をプロジェクトルート（"
            f"{project_root}）へ通すか、パッケージ実行（python -m ...）で実行してください。"
        ) from e

# -------------------- ロガー設定 --------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")

# -------------------- 戦略テンプレート --------------------
STRATEGY_TEMPLATE = """\
import pandas as pd
import numpy as np

def simulate(data: pd.DataFrame) -> dict:
    \"\"\"
    RSIとspreadに基づいたシンプルな戦略
    BUY: RSI > 50 and spread < 2
    SELL: RSI < 50 or spread > 2
    \"\"\"
    capital = 1_000_000  # 初期資本
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

    # ポジションが残っていれば決済
    if position > 0:
        capital = position * data.iloc[-1]['price']
        capital_history.append(capital)

    # 指標計算
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

# -------------------- ユーティリティ --------------------
def _sanitize_filename(name: str) -> str:
    """安全なファイル名へ（英数字・ハイフン・アンダースコア以外を '_' に）"""
    name = name.strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^A-Za-z0-9_\-]", "_", name)
    return name or "strategy"

# -------------------- 主要関数 --------------------
def generate_strategy_file(strategy_name: str) -> str:
    """
    指定された戦略名で、新しい戦略ファイルを生成する。
    """
    try:
        output_dir: Path = STRATEGIES_VERITAS_GENERATED_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_name = _sanitize_filename(strategy_name)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_{timestamp}.py"
        filepath = output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(STRATEGY_TEMPLATE)

        logging.info(f"✅ 新たな戦略の羊皮紙を生成しました: {filepath}")
        return str(filepath)
    except Exception as e:
        logging.error("❌ 戦略ファイルの生成中にエラーが発生しました", exc_info=True)
        raise

def main():
    """スクリプトとして直接実行された際のメイン関数"""
    logging.info("--- 戦略生成スクリプトを開始します ---")
    generate_strategy_file("veritas_strategy")
    logging.info("--- 戦略生成スクリプトを完了しました ---")

if __name__ == "__main__":
    main()
