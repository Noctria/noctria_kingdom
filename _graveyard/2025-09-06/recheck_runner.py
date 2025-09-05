#!/usr/bin/env python3
# coding: utf-8

"""
📘 scripts/recheck_runner.py（v3.1統合版）
"""

import sys
from core.strategy_evaluator import evaluate_strategy


def main():
    if len(sys.argv) < 2:
        print("Usage: recheck_runner.py <strategy_id>", file=sys.stderr)
        sys.exit(1)

    strategy_id = sys.argv[1]

    try:
        result = evaluate_strategy(strategy_id)
        print(f"✅ 再評価完了: {result}")
    except Exception as e:
        print(f"❌ 再評価中にエラー: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
