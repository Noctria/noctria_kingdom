# src/strategies/veritas_generated/Aurus_Singularis.py
class AurusSingularis:
    def propose(self, market_data=None):
        # ダミー戦略 — 常に固定ポジションを返す
        return {
            "symbol": "USDJPY",
            "action": "HOLD",
            "confidence": 0.0
        }
