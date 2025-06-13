# institutions/central_bank_ai.py

class CentralBankAI:
    """
    Noctria Kingdom 中央銀行AI：CPI・金利差・失業率に基づく政策スタンス評価
    """

    def __init__(self, inflation_target=2.0, unemployment_threshold=5.0, interest_neutral=0.5):
        self.inflation_target = inflation_target
        self.unemployment_threshold = unemployment_threshold
        self.interest_neutral = interest_neutral

    def determine_policy_mode(self, fundamentals: dict) -> str:
        """
        経済指標から中央銀行の政策モードを分類
        :param fundamentals: dict with keys 'cpi', 'interest_diff', 'unemployment'
        :return: 'EASING' | 'NEUTRAL' | 'TIGHTENING'
        """
        cpi = fundamentals.get("cpi", 0.0)
        interest_diff = fundamentals.get("interest_diff", 0.0)
        unemployment = fundamentals.get("unemployment", 5.0)

        if cpi < self.inflation_target - 0.5 or unemployment > self.unemployment_threshold:
            return "EASING"
        elif cpi > self.inflation_target + 0.5 and interest_diff > self.interest_neutral:
            return "TIGHTENING"
        else:
            return "NEUTRAL"

    def encode_policy_to_score(self, mode: str) -> float:
        """
        政策モードを MetaAI で利用可能な数値スコアへ変換
        :param mode: policy mode string
        :return: float score: +1 (EASING), 0 (NEUTRAL), -1 (TIGHTENING)
        """
        mapping = {
            "EASING": +1.0,
            "NEUTRAL": 0.0,
            "TIGHTENING": -1.0
        }
        return mapping.get(mode.upper(), 0.0)

    def evaluate(self, fundamentals: dict) -> float:
        """
        外部から呼び出す際の統合関数：スコアを即返す
        :param fundamentals: dict with cpi, interest_diff, unemployment
        :return: float score (-1.0〜+1.0)
        """
        mode = self.determine_policy_mode(fundamentals)
        return self.encode_policy_to_score(mode)


# ✅ テスト実行例
if __name__ == "__main__":
    cb = CentralBankAI()
    test_data = {
        "cpi": 3.2,
        "interest_diff": 0.75,
        "unemployment": 3.5
    }
    mode = cb.determine_policy_mode(test_data)
    score = cb.evaluate(test_data)
    print(f"📊 政策モード: {mode} → スコア: {score}")
