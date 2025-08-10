# -*- coding: utf-8 -*-
from pathlib import Path
from __future__ import annotations
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Tuple

import numpy as np

log = logging.getLogger("Noctria")

# 依存は“あれば使う”方針（無ければスキップ）
try:
    from src.core.data_loader import MarketDataFetcher  # 実在すれば使用（Deprecated表記は別PRで対応）
except Exception:
    MarketDataFetcher = None  # type: ignore

try:
    from src.core.risk_manager import RiskManager
except Exception:
    RiskManager = None  # type: ignore

try:
    from src.strategies.aurus_singularis import AurusSingularis
except Exception:
    AurusSingularis = None  # type: ignore

try:
    from src.strategies.levia_tempest import LeviaTempest
except Exception:
    LeviaTempest = None  # type: ignore

try:
    from src.strategies.noctus_sentinella import NoctusSentinella
except Exception:
    NoctusSentinella = None  # type: ignore

try:
    from src.strategies.prometheus_oracle import PrometheusOracle
except Exception:
    PrometheusOracle = None  # type: ignore


@dataclass
class Decision:
    strategy: str
    action: str         # "BUY" | "SELL" | "HOLD"
    confidence: float   # 0.0 ~ 1.0
    reason: str


class Noctria:
    """
    王の決断・軽量ファサード
    - 戦略プラグインを“安全に”組み込み、最終判断を返す
    - モデルが無い戦略はスキップして続行（E2Eを止めない）
    - 環境変数 NOCTRIA_MODEL_PATH で昇格済みモデルのパスを受け付け
    """

    # Prometheus の既定（古いKeras想定パス）※存在しなければ使わない
    _DEFAULT_PROMETHEUS_PATH = "/opt/***/src/veritas/models/prometheus_oracle.keras"

    def __init__(self) -> None:
        self.strategies: List[Tuple[str, Any]] = []

        # データ/リスクは存在すれば使う
        self.fetcher = MarketDataFetcher() if MarketDataFetcher else None
        self.risk = RiskManager(historical_data=None) if RiskManager else None

        # 使用する戦略の選択（環境変数でON/OFF可能）
        # 例: NOCTRIA_STRATEGIES="aurus,levia,noctus,prometheus"
        enabled = set(os.environ.get("NOCTRIA_STRATEGIES", "aurus,levia,noctus,prometheus")
                      .replace(" ", "").split(","))
        self._maybe_add_strategy("Aurus", AurusSingularis, enabled, key="aurus")
        self._maybe_add_strategy("Levia", LeviaTempest, enabled, key="levia")
        self._maybe_add_strategy("Noctus", NoctusSentinella, enabled, key="noctus")

        # Prometheus はモデルファイルの存在を確認の上で組み込む
        if "prometheus" in enabled and PrometheusOracle:
            model_path = os.environ.get("NOCTRIA_MODEL_PATH", self._DEFAULT_PROMETHEUS_PATH)
            p = Path(model_path) if model_path else None
            if p and p.exists():
                try:
                    self.strategies.append(("Prometheus", PrometheusOracle(model_path=str(p))))
                except Exception as e:
                    log.warning("PrometheusOracle 初期化に失敗: %s", e)
            else:
                log.info("PrometheusOracle 無効化（モデルファイル未検出）: %s", model_path)

        if not self.strategies:
            log.info("有効な戦略が見つからなかったため、ダミー決断にフォールバックします。")

    def _maybe_add_strategy(self, name: str, cls: Any, enabled: set, key: str) -> None:
        if key not in enabled or not cls:
            return
        try:
            self.strategies.append((name, cls()))
        except Exception as e:
            # 戦略の __init__ でコケても全体は止めない
            log.warning("strategy %s 初期化失敗: %s", name, e)

    # ---- 決断ロジック ----
    def analyze_market(self) -> Decision:
        """
        戦略があれば投票、無ければ乱数で決断。
        戦略の decide()/signal() が存在しない、または例外なら無視。
        """
        candidates = ["BUY", "SELL", "HOLD"]
        votes: List[Tuple[str, str, float]] = []

        for name, agent in self.strategies:
            decide = getattr(agent, "decide", None) or getattr(agent, "signal", None)
            if not callable(decide):
                continue
            try:
                # 実装によっては引数が必要な場合がある。簡易版は引数なし呼び。
                act = decide()
                if act in candidates:
                    votes.append((name, act, 0.6))
            except Exception as e:
                log.warning("strategy %s decide() 失敗: %s", name, e)

        if votes:
            acts = [a for _, a, _ in votes]
            winner = max(set(acts), key=acts.count)
            conf = min(1.0, acts.count(winner) / max(1, len(votes)))
            strat = [n for n, a, _ in votes if a == winner][0]
            return Decision(strategy=strat, action=winner, confidence=conf, reason="majority_vote")

        # --- ダミー決断（戦略なしでもE2Eが止まらないように） ---
        act = np.random.choice(candidates)
        conf = float(np.random.uniform(0.4, 0.7))
        return Decision(strategy="Dummy", action=act, confidence=conf, reason="random_fallback")

    def execute_trade(self) -> Dict[str, Any]:
        """
        ここでは“まだ発注はしない”。将来：
          Decision → (P)PreTradeValidator → (D)Router/Broker → (C)監査 → (A)調整
        """
        d = self.analyze_market()

        result = {
            "final_decision": d.action,
            "chosen_strategy": d.strategy,
            "confidence": round(d.confidence, 3),
            "reason": d.reason,
            "ts": datetime.utcnow().isoformat() + "Z",
        }
        log.info("Royal decision: %s", result)
        return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(Noctria().execute_trade())
