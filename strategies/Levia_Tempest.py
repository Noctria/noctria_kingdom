class LeviaTempest:
    def __init__(self):
        pass

    def process(self, market_state):
        """
        短期スキャルピング系戦略ロジック（ダミー例）
        """
        return "SELL"  # ダミー出力

    def decide_action(self, market_state):
        return self.process(market_state)
