import pandas as pd
import numpy as np

class FundamentalAnalysis:
    """企業の財務指標を分析し、市場動向を評価するモジュール"""
    
    def __init__(self):
        self.risk_threshold = 0.5  # 財務健全性の閾値
    
    def analyze_financials(self, financial_data):
        """財務データを評価"""
        health_score = (financial_data["net_income"] / financial_data["total_assets"]) * 100
        return "STABLE" if health_score > self.risk_threshold else "RISKY"

    def evaluate_sector_trends(self, sector_data):
        """業界全体のパフォーマンスを評価"""
        sector_growth = np.mean(sector_data["growth_rate"])
        return "EXPANDING" if sector_growth > 0 else "CONTRACTING"

# ✅ 財務分析テスト
if __name__ == "__main__":
    sample_financials = {"net_income": 5000000, "total_assets": 15000000}
    sample_sector_data = pd.DataFrame({"growth_rate": np.random.uniform(-0.05, 0.10, 10)})

    analyzer = FundamentalAnalysis()
    financial_health = analyzer.analyze_financials(sample_financials)
    sector_trend = analyzer.evaluate_sector_trends(sample_sector_data)

    print("Financial Health Status:", financial_health)
    print("Sector Trend Evaluation:", sector_trend)
