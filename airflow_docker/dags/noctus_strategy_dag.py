#!/usr/bin/env python3
# coding: utf-8

"""
🛡️ Noctus Sentinella Risk Assessment DAG (v2.0)
- リスク管理官ノクトゥスを起動し、特定の状況下でのリスクを評価する。
- このDAGは主にテストや、特定のシナリオを検証するために手動で実行されることを想定。
"""

import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any
import pandas as pd
import numpy as np

from airflow.decorators import dag, task

# --- 王国の基盤モジュールをインポート ---
# ✅ 修正: Airflowが'src'モジュールを見つけられるように、プロジェクトルートをシステムパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.strategies.noctus_sentinella import NoctusSentinella

# === DAG基本設定 ===
default_args = {
    'owner': 'Noctus',
    'depends_on_past': False,
    'start_date': datetime(2025, 7, 1),
    'retries': 0,
}

@dag(
    dag_id='noctus_risk_assessment_dag',
    default_args=default_args,
    description='守護者ノクトゥスによるリスク評価シミュレーション',
    schedule_interval=None,
    catchup=False,
    tags=['noctria', 'risk_management', 'noctus'],
)
def noctus_risk_assessment_pipeline():
    """
    リスク管理官ノクトゥスが、与えられた市場データと提案アクションに基づき、
    リスク評価を行うパイプライン。
    """

    @task
    def simulate_market_and_proposal() -> Dict[str, Any]:
        """
        テストのために、市場の状況と、他の臣下からの提案（例: BUY）を模擬的に生成する。
        """
        logger = logging.getLogger("ScenarioSimulator")
        logger.info("リスク評価のための模擬シナリオを生成します…")
        
        # テスト用のダミーヒストリカルデータを作成
        dummy_hist_data = pd.DataFrame({
            'Close': np.random.normal(loc=150, scale=2, size=100)
        })
        dummy_hist_data['returns'] = dummy_hist_data['Close'].pct_change().dropna()

        market_data = {
            "price": 152.5, "volume": 150, "spread": 0.012, 
            "volatility": 0.15, "historical_data": dummy_hist_data
        }
        
        proposed_action = "BUY"
        logger.info(f"模擬シナリオ完了。提案アクション: 『{proposed_action}』")
        
        # DataFrameはJSONに変換してXComsで渡す
        market_data['historical_data'] = market_data['historical_data'].to_json()
        
        return {"market_data": market_data, "proposed_action": proposed_action}

    @task
    def assess_risk_task(scenario: Dict[str, Any]):
        """
        Noctusを召喚し、シナリオに基づきリスクを評価させる。
        """
        logger = logging.getLogger("NoctusAssessmentTask")
        
        market_data = scenario['market_data']
        proposed_action = scenario['proposed_action']
        
        # XComから受け取ったJSON文字列をDataFrameに戻す
        market_data['historical_data'] = pd.read_json(market_data['historical_data'])
        
        noctus = NoctusSentinella()
        assessment = noctus.assess(market_data, proposed_action)
        
        logger.info(f"🛡️ ノクトゥスの最終判断: {assessment['decision']} (理由: {assessment['reason']})")
        return assessment

    # --- パイプラインの定義 ---
    scenario_data = simulate_market_and_proposal()
    assess_risk_task(scenario=scenario_data)

# DAGのインスタンス化
noctus_risk_assessment_pipeline()
