# -*- coding: utf-8 -*-
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Dict, Any
from datetime import datetime
import numpy as np

# できる限り軽依存に。存在しない場合はフォールバックで続行。
try:
    from src.core.data_loader import MarketDataFetcher  # 実在すれば使用
except Exception:
    MarketDataFetcher = None  # フォールバック

try:
    from src.core.risk_manager import RiskManager  # 実在すれば使用
except Exception:
    RiskManager = None

# 戦略は“存在すれば使う”。なければダミー採点。
try:
    from src.strategies.aurus_singularis import AurusSingularis
except Exception:
    AurusSingularis = None
try:
    from src.strategies.levia_tempest import LeviaTempest
except Exception:
    LeviaTempest = None
try:
    from src.strategies.noctus_sentinella import NoctusSentinella
except Exception:
    NoctusSentinella = None
try:
    from src.strategies.prometheus_oracle import PrometheusOracle
except Exception:
    PrometheusOracle = None

log = logging.getLogger("Noctria")

@dataclass
class Decision:
    strategy: str
    action: str           # "BUY" | "SELL" | "HOLD"
    confidence: float     # 0.0 ~ 1.0
    reason: str

class Noctria:
    """
    王の決断・軽量版（シム）
    - 依存が見つかれば使う、無ければ乱数で決める
    - 返り値は JSON 化しやすい dict（DAG→監査の橋渡し）
    """

    def __init__(self) -> None:
        self.strategies = []
        if AurusSingularis:   self.strategies.append(("Aurus", AurusSingularis()))
        if LeviaTempest:      self.strategies.append(("Levia", LeviaTempest()))
        if NoctusSentinella:  self.strategies.append(("Noctus", NoctusSentinella()))
        if PrometheusOracle:  self.strategies.append(("Prometheus", PrometheusOracle()))

        # 市場データ/リスク管理（あれば）
        self.fetcher = MarketDataFetcher() if MarketDataFetcher else None
        self.risk = RiskManager(historical_data=None) if RiskManager else None

    def analyze_market(self) -> Decision:
        """
        戦略があれば投票、無ければ乱数で決断。
        """
        candidates = ["BUY", "SELL", "HOLD"]
        # 簡易：各戦略が .decide() 的なものを持っている場合だけ使う
        votes = []
        for name, agent in self.strategies:
            decide = getattr(agent, "decide", None) or getattr(agent, "signal", None)
            if callable(decide):
                try:
                    act = decide()  # 実体に合わせて引数が必要なら後で調整
                    if act in candidates:
                        votes.append((name, act, 0.6))
                except Exception as e:
                    log.warning("strategy %s decide() failed: %s", name, e)

        if votes:
            # 最頻値で決定、同点は乱択
            acts = [a for _, a, _ in votes]
            winner = max(set(acts), key=acts.count)
            conf = min(1.0, acts.count(winner) / max(1, len(votes)))
            strat = [n for n, a, _ in votes if a == winner][0]
            return Decision(strategy=strat, action=winner, confidence=conf, reason="majority_vote")
        else:
            # ダミー決断
            act = np.random.choice(candidates)
            conf = float(np.random.uniform(0.4, 0.7))
            return Decision(strategy="Dummy", action=act, confidence=conf, reason="random_fallback")

    def execute_trade(self) -> Dict[str, Any]:
        """
        ここでは“まだ発注はしない”。将来：
          Decision → (P)PreTradeValidator → (D)Router/Broker → (C)監査 → (A)調整
        """
        d = self.analyze_market()

        # --- 将来の P 層フック（PreTradeValidator）挿入ポイント ---
        # from src.plan_data.pretrade.pretrade_validator import PreTradeValidator
        # vr = PreTradeValidator().validate(order_context)
        # if vr.auto_action == "BLOCK": return {...}

        result = {
            "final_decision": d.action,              # BUY / SELL / HOLD
            "chosen_strategy": d.strategy,           # 例: "Aurus" / "Dummy"
            "confidence": round(d.confidence, 3),
            "reason": d.reason,
            "ts": datetime.utcnow().isoformat() + "Z",
            # 将来ここに order_context / validation_report / execution_report を付ける
        }
        log.info("Royal decision: %s", result)
        return result

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(Noctria().execute_trade())
