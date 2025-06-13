class CentralBankAI:
    """
    中央銀行AI: CPI、金利差、失業率などから市場の金融政策バイアスを判定し、
    スコア（buy/bullish方向の強さ）を返す。
    """

    def __init__(self, cpi_weight=0.4, interest_weight=0.4, unemployment_weight=0.2):
        self.cpi_weight = cpi_weight
        self.interest_weight = interest_weight
        self.unemployment_weight = unemployment_weight

    def get_policy_score(self, data):
        """
        ファンダメンタルデータに基づいて中央銀行的なスコア（0〜1）を返す。
        高スコア = 金融引き締め（通貨高）傾向。
        """

        # データ取得（0.0で補完）
        cpi = data.get("cpi", 0.0)
        interest_diff = data.get("interest_diff", 0.0)
        unemployment = data.get("unemployment", 0.0)

        # 正規化（仮の閾値基準で正規化）
        norm_cpi = min(max((cpi - 2.0) / 2.0, 0.0), 1.0)  # CPI 2%以上で強気方向へ
        norm_interest = min(max((interest_diff + 1.0) / 2.0, 0.0), 1.0)  # 金利差 +1%以上が強気
        norm_unemployment = 1.0 - min(max((unemployment - 3.0) / 3.0, 0.0), 1.0)  # 失業率が低いほど強気

        # 重み付き合計スコア
        score = (
            norm_cpi * self.cpi_weight +
            norm_interest * self.interest_weight +
            norm_unemployment * self.unemployment_weight
        )

        return round(score, 4)
