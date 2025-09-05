# src/plan_data/llm_plan_prompt.py
def build_plan_prompt(stats, anomalies, last_act):
    prompt = (
        "【直近の運用状況・実績指標】\n"
        f"平均勝率: {stats['win_rate']['mean']}%\n"
        f"平均DD: {stats['drawdown']['mean']}%\n"
        f"アクション履歴: {last_act}\n"
        "【異常/失敗パターン】\n"
        f"{anomalies}\n"
        "【次サイクルのプラン提案】\n"
        "→ これらを考慮して次に実施すべき施策をAI的に推奨してください。"
    )
    return prompt

