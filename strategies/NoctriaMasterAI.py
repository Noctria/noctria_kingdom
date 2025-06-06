class NoctusSentinella:
    def __init__(self):
        pass

    def process(self, market_state):
        """
        リスク管理系戦略ロジック（ダミー例）
        """
        return "HOLD"  # ダミー出力

    def decide_action(self, market_state):
        return self.process(market_state)
