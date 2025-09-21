from __future__ import annotations

ASSET_SYMBOLS = ["BTC", "ETH", "USDT"]


class PlanDataCollector:
    def collect_all(self) -> dict:
        return {"symbols": ASSET_SYMBOLS, "data": []}

    # Other methods can be defined here as needed.
