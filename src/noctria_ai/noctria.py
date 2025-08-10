# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
import inspect
import numpy as np

log = logging.getLogger("Noctria")

# 依存は“あれば使う”
try:
    from src.core.data_loader import MarketDataFetcher  # Deprecated表記は別対応
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
        enabled = set(
            os.environ.get("NOCTRIA_STRATEGIES", "aurus,levia,noctus,prometheus")
            .replace(" ", "")
            .split(",")
        )
        self._maybe_add_strategy("Aurus", AurusSingularis, enabled, key="aurus")
        self._maybe_add_strategy("Levia", LeviaTempest, enabled, key="levia")
        self._maybe_add_strategy("Noctus", NoctusSentinella, enabled, key="noctus")

        # Prometheus はモデルファイルの存在を確認の上で組み込む（Pathを渡す）
        if "prometheus" in enabled and PrometheusOracle:
            model_path_env = os.environ.get("NOCTRIA_MODEL_PATH", self._DEFAULT_PROMETHEUS_PATH)
            p = Path(model_path_env) if model_path_env else None
            if p and p.exists():
                self._try_add_prometheus(p)
            else:
                log.info("PrometheusOracle 無効化（モデルファイル未検出）: %s", model_path_env)

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

    def _try_add_prometheus(self, path_obj: Path) -> None:
        """PrometheusOracle のコンストラクタ差異に耐える初期化（Path優先、だめならstr等も試す）"""
        try:
            sig = inspect.signature(PrometheusOracle)  # type: ignore[arg-type]
            # 1) model_path キーワードに Path
            if "model_path" in sig.parameters:
                self.strategies.append(("Prometheus", PrometheusOracle(model_path=path_obj)))  # type: ignore[misc]
                return
            # 2) 位置引数に Path
            try:
                self.strategies.append(("Prometheus", PrometheusOracle(path_obj)))  # type: ignore[misc]
                return
            except Exception:
                pass
            # 3) キーワードに str
            if "model_path" in sig.parameters:
                self.strategies.append(("Prometheus", PrometheusOracle(model_path=str(path_obj))))  # type: ignore[misc]
                return
            # 4) 位置引数に str
            self.strategies.append(("Prometheus", PrometheusOracle(str(path_obj))))  # type: ignore[misc]
        except Exception as e:
            log.warning("PrometheusOracle 初期化に失敗: %s", e)

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
                act = decide()  # 必要に応じて引数は実装へ合わせる
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
