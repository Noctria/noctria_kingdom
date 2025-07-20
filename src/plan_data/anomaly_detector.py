# src/plan_data/anomaly_detector.py
def detect_drawdown_anomalies(eval_results, dd_threshold=20):
    """最大DDが異常値の戦略を検出"""
    return [r for r in eval_results if r.get("max_drawdown", 0) > dd_threshold]

def detect_low_win_rate(eval_results, rate_threshold=40):
    """勝率が著しく低い戦略"""
    return [r for r in eval_results if r.get("win_rate", 100) < rate_threshold]

