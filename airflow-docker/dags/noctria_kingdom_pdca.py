from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

default_args = {
    'owner': 'noctria_kingdom',
    'depends_on_past': False,
    'email_on_failure': False,
}

with DAG(
    dag_id='noctria_kingdom_pdca',
    default_args=default_args,
    description='👑 Noctria Kingdom 自律型AIスーパートレーダーのPDCAサイクル',
    schedule_interval='@daily',  # 1日1回実行
    start_date=days_ago(1),
    catchup=False,
) as dag:

    # 1️⃣ 王（Noctria）: 王国の市場情報収集命令
    fetch_data = BashOperator(
        task_id='noctria_order_data_fetch',
        bash_command='echo "👑 王Noctria: 市場データを収集せよ！" && python scripts/fetch_and_clean_fundamentals.py',
    )

    # 2️⃣ Aurus: 戦略を練り、学習を進める
    train_aurus = BashOperator(
        task_id='aurus_train_strategy',
        bash_command='echo "⚔️ Aurus: 市場データを基に戦略を練り、学習を進めます！" && python scripts/meta_ai_tensorboard_train.py',
    )

    # 3️⃣ Noctus: 市場の危険を検証し、戦略の健全性を守る
    analyze_noctus = BashOperator(
        task_id='noctus_risk_analysis',
        bash_command='echo "🛡️ Noctus: 市場の異常を検証し、リスクを管理します！" && python scripts/analyze_results.py',
    )

    # 4️⃣ Prometheus: 未来を見据え、次なる最適化を導く
    optimize_prometheus = BashOperator(
        task_id='prometheus_optimize_future',
        bash_command='echo "🔮 Prometheus: 未来予測に基づき、戦略の最適化を進めます！" && python scripts/optimize_params.py',
    )

    # 5️⃣ Levia: 市場の波を捉え、最適化結果を即座に適用
    apply_levia = BashOperator(
        task_id='levia_apply_optimized_strategy',
        bash_command='echo "⚡ Levia: 最適化された戦略を即時適用し、短期取引の刈り取りに備えます！" && python scripts/apply_best_params.py',
    )

    # 実行順序
    fetch_data >> train_aurus >> analyze_noctus >> optimize_prometheus >> apply_levia
