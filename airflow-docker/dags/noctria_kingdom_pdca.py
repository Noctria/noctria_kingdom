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
    description='👑 Noctria Kingdom AIスーパートレーダーの自動PDCAサイクル',
    schedule_interval='@daily',  # 例: 毎日実行
    start_date=days_ago(1),
    catchup=False,
) as dag:

    # 1️⃣ データ収集・整形
    fetch_data = BashOperator(
        task_id='fetch_data',
        bash_command='echo "👑 王: Aurus、Prometheusよ、情報収集せよ！" && python3 /opt/airflow/scripts/fetch_and_clean_fundamentals.py',
    )

    # 2️⃣ AI学習
    train_ai = BashOperator(
        task_id='train_ai',
        bash_command='echo "⚔️ Aurus: 戦略AI学習を開始します！" && python3 /opt/airflow/scripts/meta_ai_tensorboard_train.py',
    )

    # 3️⃣ 戦略成果の分析
    analyze_results = BashOperator(
        task_id='analyze_results',
        bash_command='echo "🛡️ Noctus: 戦略の健全性を分析します！" && python3 /opt/airflow/scripts/analyze_results.py',
    )

    # 4️⃣ パラメータ最適化
    optimize_params = BashOperator(
        task_id='optimize_params',
        bash_command='echo "🔮 Prometheus: 未来予測に基づく最適化を進めます！" && python3 /opt/airflow/scripts/optimize_params.py',
    )

    # 5️⃣ 最適化結果を即時適用
    apply_best_params = BashOperator(
        task_id='apply_best_params',
        bash_command='echo "⚡ Levia: 最適化内容を即時反映！" && python3 /opt/airflow/scripts/apply_best_params.py',
    )

    # タスクの実行順序
    fetch_data >> train_ai >> analyze_results >> optimize_params >> apply_best_params
