#!/usr/bin/env python3
# coding: utf-8

"""
Noctus → OrderExecution スモークテスト
- ダミー特徴量を作成
- NoctusSentinella.calculate_lot_and_risk() で判定＆ロット算出
- APPROVE のとき OrderExecution.execute_order() を dry_run で発注シミュレーション
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.noctus_sentinella import NoctusSentinella
from src.execution.order_execution import OrderExecution


def build_dummy_features(price: float = 152.5) -> dict:
    """テスト用の簡易特徴量セットを作る"""
    hist = pd.DataFrame({"Close": np.random.normal(loc=price, scale=2, size=200)})
    # Noctus/RiskManager 側が参照し得る列名に合わせて用意
    hist["returns"] = hist["Close"].pct_change()
    return {
        "price": price,
        "volume": 200,
        "spread": 0.012,
        "volatility": 0.15,
        "historical_data": hist,
    }


def main():
    # 1) Noctusでロット＆リスク判定
    features = build_dummy_features(price=152.5)
    noctus = NoctusSentinella()

    res = noctus.calculate_lot_and_risk(
        feature_dict=features,
        side="BUY",
        entry_price=152.60,
        stop_loss_price=152.30,
        capital=20_000,
        risk_percent=0.007,  # 0.7%
        decision_id="TEST-NOCTUS",
        caller="smoke_test",
        reason="calc_only",
    )
    print("noctus:", res)

    # 2) APPROVEなら発注シミュレーション（dry_run）
    if res.get("decision") == "APPROVE":
        exec_client = OrderExecution(api_url="http://localhost:5001/order", dry_run=True)
        out = exec_client.execute_order(
            symbol="USDJPY",
            lot=res["lot"],
            order_type="BUY",
            entry_price=152.60,
            stop_loss=152.30,
            decision_id=res.get("decision_id", "TEST-NOCTUS"),
            caller="smoke_test",
            reason="from_noctus",
        )
        print("order:", out)
    else:
        print("Noctus vetoed. 発注は行いません。")


if __name__ == "__main__":
    main()
