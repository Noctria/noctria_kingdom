class CentralBankAI:
    """
    中央銀行AI: CPI、金利差、失業率などから金融政策バイアスを判定し、
    強気（BUY/BULL）バイアスのスコア（0〜1）を返す。
    """

    def __init__(self, weights=None):
        """
        各指標の重みを設定（デフォルト: CPI=0.4, 金利差=0.4, 失業率=0.2）
        """
        default_weights = {"cpi": 0.4, "interest_diff": 0.4, "unemployment": 0.2}
        self.weights = weights or default_weights

    def normalize_cpi(self, cpi):
        """CPI: 2%以上で強気バイアス → 緩やかに1.0に近づく"""
        return min(max((cpi - 2.0) / 2.0, 0.0), 1.0)

    def normalize_interest_diff(self, diff):
        """金利差: +1%以上で強気"""
        return min(max((diff + 1.0) / 2.0, 0.0), 1.0)

    def normalize_unemployment(self, unemployment):
        """失業率: 3%以下が強気 → 高くなると弱気"""
        return 1.0 - min(max((unemployment - 3.0) / 3.0, 0.0), 1.0)

    def get_policy_score(self, data: dict) -> float:
        """
        ファンダメンタルデータに基づいてスコア（0〜1）を返す。
        高スコア = 金融引き締め（通貨高）バイアス。
        """
        cpi = data.get("cpi", 0.0)
        interest = data.get("interest_diff", 0.0)
        unemployment = data.get("unemployment", 0.0)

        score = (
            self.normalize_cpi(cpi) * self.weights["cpi"] +
            self.normalize_interest_diff(interest) * self.weights["interest_diff"] +
            self.normalize_unemployment(unemployment) * self.weights["unemployment"]
        )

        return round(score, 4)
