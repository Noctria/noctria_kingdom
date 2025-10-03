# Noctria Kingdom 統治プロンプト完全版

生成日時: 2025-09-20T04:06:00.629843

---

## 📘 Codex 本編

# docs/codex/Codex_Noctria.md

# 🏰 Codex Noctria - 全体ロードマップとタスク表

## 1. 目的
Noctria王国における自律型AI開発体制の確立を目指す。  
中心となる王Noctriaが裁可を下し、臣下AIたち（Hermes, Veritas, Inventor Scriptus, Harmonia Ordinis）が開発を進める。

---

## 2. ロードマップ

### 🔹 短期 (段階1)
- **Inventor Scriptus (開発者AI)**: pytest失敗時に修正案をテキストで提示  
- **Harmonia Ordinis (レビュワーAI)**: pytestログを精査し、指摘を返す  
- **統合タスク**:
  - GUIからテスト実行ボタン
  - AutoGen/pytest runner の初期統合
  - Observability(DB) にログ記録

### 🔹 中期 (段階2)
- **Inventor Scriptus**: 自動パッチ生成（diffやファイル全体コード）
- **Harmonia Ordinis**: パッチレビューを自動化し、PRをapprove/reject
- **統合タスク**:
  - GitHub Actions連携でPR自動生成
  - PRレビュー履歴をPostgresに保存
  - FastAPI HUDに「PRレビュー」ページ

### 🔹 長期 (段階3)
- **Inventor Scriptus**: Airflow DAGによりnightly自動修正ループを実行
- **Harmonia Ordinis**: すべてのレビュー/決定をObservabilityへ記録
- **統合タスク**:
  - Airflow DAG `autogen_devcycle` の設計
  - observability.py を拡張してAI開発行動を記録
  - GUIに「自律開発進捗ダッシュボード」

### 🔹 最終 (段階4)
- **Inventor Scriptus**: 全工程を自律的に遂行
- **Harmonia Ordinis**: 自動マージとリリース承認を提案
- **王Noctria**: 「承認ボタン」だけで全開発が流れる
- **統合タスク**:
  - FastAPI HUDに「王の裁可UI」
  - PDCAループとAI開発サイクルを完全統合
  - GPUクラウドML + ChatGPT APIを両輪で活用

---

## 3. タスク表

| フェーズ | タスク | 担当AI |
|----------|--------|--------|
| 段階1 | pytest結果解析 → 修正案提示 | Inventor Scriptus |
| 段階1 | 修正案レビュー（自然言語） | Harmonia Ordinis |
| 段階2 | 自動パッチ生成 | Inventor Scriptus |
| 段階2 | 自動PRレビュー/approve | Harmonia Ordinis |
| 段階3 | nightly自律開発DAG実行 | Inventor Scriptus |
| 段階3 | 行動ログの可観測化 | Harmonia Ordinis |
| 段階4 | 全自律開発（承認UI） | Inventor Scriptus / Harmonia Ordinis / 王Noctria |

---


---

## 🧩 Codex Agents 定義

# Codex Noctria Agents — 開発者AIとレビュワーAI

## 1. エージェントの位置付け
- **Inventor Scriptus**（開発者AI）  
  - コード生成・修正を担当。  
  - pytestを実行して失敗時は修正案を出す。  

- **Harmonia Ordinis**（レビュワーAI）  
  - 生成コードの品質審査。  
  - 設計方針や王国の理念に沿っているかを検証。  

両者は「Noctria王国の臣下」として王Noctriaに仕える。

---

## 2. 権限レベル
- **Lv1: 提案のみ**  
  - Inventor Scriptus: 修正案を出す  
  - Harmonia Ordinis: 論理的レビューを行う  

- **Lv2: パッチ生成**  
  - Inventor Scriptus: 実際にパッチ形式で修正を出す  
  - Harmonia Ordinis: パッチの妥当性をレビュー  

- **Lv3: 自動テスト反映**  
  - Inventor Scriptus: 軽量テストを自動実行し、パスした場合のみ修正を維持  
  - Harmonia Ordinis: テスト結果を踏まえて承認  

- **Lv4: 本番統合**（将来段階）  
  - PR作成、Airflow連携、自動昇格審査へ  

---

## 3. 権限昇格条件
- 提案精度（失敗修正率）が一定水準を超えること  
- レビュワーによる承認率が高いこと  
- 不要な変更や方針逸脱が発生しないこと  
- 王Noctria（人間開発者）が明示承認した場合のみ昇格  

---

## 4. 技術的アプローチ
### A. AutoGenスタイル
- Pythonマルチエージェント  
- pytest失敗 → 修正案再生成  
- GitHub PR自動化  

### B. LangChainエージェント
- ChatOpenAI + Tools（pytest runner / git client / docs検索）  
- observability.py で Postgres に全行動を記録  

### C. Airflow連携
- autogen_devcycle DAG  
- fetch → pytest → failならGPT修正 → patch生成 → commit → pytest再実行 → passならPR  

---

## 5. ⚙️ 開発環境整備：テスト分離
代理AIを安全に立ち上げるため、テストを以下の2段階に分離する。

- **軽量テスト（ローカル, venv_codex）**  
  - pandas, numpy, tensorflow-cpu など軽依存  
  - 実行対象: `test_quality_gate_alerts.py`, `test_noctus_gate_block.py` など  
  - 代理AIが日常的に回す「自動開発サイクル」はここで実行  

- **重テスト（GPU, gpusoroban / venv_codex+GPU）**  
  - torch, gym, MetaTrader5, RL系長時間テスト  
  - 実行対象: RL訓練や統合e2e系のテスト  
  - 本番昇格審査やAirflow DAGで実行  

### 意義
- 代理AIが「環境依存のImportError」に惑わされず、本当に修正すべきロジックエラーだけを扱える。  
- ローカルで高速修正ループを回せる。  
- 本番GPU環境でのみ統合チェックを実行できる。  

---

## 6. 今後のロードマップ（エージェント関連）
1. 軽量テスト分離の確立 ✅  
2. Inventor Scriptus に「修正案生成＋pytest再実行」を組み込み  
3. Harmonia Ordinis に「レビューロジック」追加  
4. 権限Lv2 → Lv3 昇格実験  
5. GPU環境（gpusoroban）での重テスト連携  
6. Airflow DAG に開発サイクルを統合  


---

## 👑 King Noctria 定義

```python
#!/usr/bin/env python3
# coding: utf-8

"""
👑 King Noctria (理想型 v3.2) - Noctusにリスク・ロット計算を委譲版
- decision_id, caller, reason で統治判断を一元管理
- 全DAG/AI/臣下呼び出し・御前会議・トリガーでdecision_idを必ず発行・伝搬
- 統治履歴は全てdecision_id単位でJSONログ保存
- Do層 order_execution.py をリスクガード・SL強制付きで一元制御
- ロット/リスク計算はNoctus（NoctusSentinella）へ委譲！
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import requests

from core.path_config import AIRFLOW_API_BASE
from src.execution.order_execution import OrderExecution
from src.strategies.aurus_singularis import AurusSingularis
from src.strategies.hermes_cognitor import HermesCognitorStrategy
from src.strategies.levia_tempest import LeviaTempest
from src.strategies.noctus_sentinella import NoctusSentinella
from src.strategies.prometheus_oracle import PrometheusOracle
from src.veritas.veritas_machina import VeritasMachina

KING_LOG_PATH = "/opt/airflow/data/king_decision_log.json"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [%(levelname)s] - 👑 KingNoctria: %(message)s"
)


class KingNoctria:
    def __init__(self):
        logging.info("王の評議会を構成するため、五臣を招集します。")
        self.veritas = VeritasMachina()
        self.prometheus = PrometheusOracle()
        self.aurus = AurusSingularis()
        self.levia = LeviaTempest()
        self.noctus = NoctusSentinella()
        self.hermes = HermesCognitorStrategy()
        self.order_executor = OrderExecution(api_url="http://host.docker.internal:5001/order")
        logging.info("五臣の招集が完了しました。")

    def _generate_decision_id(self, prefix="KC"):
        dt = datetime.now().strftime("%Y%m%d-%H%M%S")
        unique = uuid.uuid4().hex[:6].upper()
        return f"{prefix}-{dt}-{unique}"

    def _save_king_log(self, entry: dict):
        try:
            with open(KING_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logging.error(f"King log保存失敗: {e}")

    # --- ★ Noctusに計算委譲！ ---
    def order_trade(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss_price: float,
        capital: float,
        risk_percent: float = 0.01,
        feature_dict: Optional[dict] = None,
        caller: str = "king_noctria",
        reason: str = "AI指令自動注文",
    ) -> dict:
        """
        王命による安全発注メソッド。ロット計算とリスク許可判定はNoctusに委譲。
        """
        # --- 1. ロット/リスク判定をNoctusに依頼 ---
        if feature_dict is None:
            # 最低限必要な情報だけ組み立て
            feature_dict = {
                "price": entry_price,
                "volume": 100,  # 仮値。実運用ではPlan層feature_dict推奨
                "spread": 0.01,  # 仮値
                "volatility": 0.15,  # 仮値
                "historical_data": pd.DataFrame({"Close": np.random.normal(entry_price, 2, 100)}),
            }
        # Noctusに"計算してもらう"（仮想メソッド。実装はNoctusに加筆）
        noctus_result = self.noctus.calculate_lot_and_risk(
            feature_dict=feature_dict,
            side=side,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            capital=capital,
            risk_percent=risk_percent,
            decision_id=self._generate_decision_id(),
            caller=caller,
            reason=reason,
        )
        # VETOなら終了
        if noctus_result["decision"] != "APPROVE":
            self._save_king_log(
                {
                    "timestamp": datetime.now().isoformat(),
                    "decision_id": noctus_result.get("decision_id", ""),
                    "caller": caller,
                    "reason": reason,
                    "symbol": symbol,
                    "side": side,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss_price,
                    "capital": capital,
                    "risk_percent": risk_percent,
                    "noctus_result": noctus_result,
                    "status": "REJECTED",
                }
            )
            return {"status": "rejected", "noctus_result": noctus_result}

        lot = noctus_result["lot"]
        # --- 2. Do層API発注（SL必須） ---
        result = self.order_executor.execute_order(
            symbol=symbol,
            lot=lot,
            order_type=side,
            entry_price=entry_price,
            stop_loss=stop_loss_price,
        )
        # --- 3. 王の決裁ログ記録 ---
        order_log = {
            "timestamp": datetime.now().isoformat(),
            "decision_id": noctus_result.get("decision_id", self._generate_decision_id()),
            "caller": caller,
            "reason": reason,
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "stop_loss": stop_loss_price,
            "lot": lot,
            "capital": capital,
            "risk_percent": risk_percent,
            "noctus_result": noctus_result,
            "api_result": result,
            "status": "EXECUTED",
        }
        self._save_king_log(order_log)
        return result

    def hold_council(self, market_data: dict, caller="king_routes", reason="御前会議決裁") -> dict:
        decision_id = self._generate_decision_id()
        timestamp = datetime.now().isoformat()
        logging.info(f"--------------------\n📣 御前会議を開催（decision_id={decision_id}）…")

        # 臣下AIの報告収集
        aurus_proposal = self.aurus.propose(market_data)
        levia_proposal = self.levia.propose(market_data)
        prometheus_forecast = self.prometheus.predict(n_days=7)
        hermes_explanation = self.hermes.propose(
            {
                "features": market_data,
                "labels": [
                    "Aurus: " + aurus_proposal.get("signal", ""),
                    "Levia: " + levia_proposal.get("signal", ""),
                ],
                "reason": reason,
            }
        )

        # 決定プロセス
        primary_action = aurus_proposal.get("signal")
        if primary_action == "HOLD":
            logging.info("Aurusは静観を推奨。Leviaの短期的な見解を求めます。")
            primary_action = levia_proposal.get("signal")
        logging.info(f"主たる進言は『{primary_action}』と決定しました。")

        noctus_assessment = self.noctus.assess(market_data, primary_action)
        final_decision = primary_action
        if noctus_assessment.get("decision") == "VETO":
            logging.warning(f"Noctusが拒否権を発動！理由: {noctus_assessment.get('reason')}")
            logging.warning("安全を最優先し、最終判断を『HOLD』に変更します。")
            final_decision = "HOLD"
        else:
            logging.info("Noctusは行動を承認。進言通りに最終判断を下します。")
        logging.info(f"👑 下される王命: 『{final_decision}』\n--------------------")

        council_report = {
            "decision_id": decision_id,
            "timestamp": timestamp,
            "caller": caller,
            "reason": reason,
            "final_decision": final_decision,
            "assessments": {
                "aurus_proposal": aurus_proposal,
                "levia_proposal": levia_proposal,
                "noctus_assessment": noctus_assessment,
                "prometheus_forecast": prometheus_forecast,
                "hermes_explanation": hermes_explanation,
            },
        }
        self._save_king_log(council_report)
        return council_report

    def _trigger_dag(
        self,
        dag_id: str,
        conf: Optional[Dict[str, Any]] = None,
        airflow_user: str = "admin",
        airflow_pw: str = "admin",
        caller="king_noctria",
        reason="王命トリガー",
    ) -> dict:
        decision_id = self._generate_decision_id()
        payload_conf = conf or {}
        payload_conf.update(
            {
                "decision_id": decision_id,
                "caller": caller,
                "reason": reason,
            }
        )
        endpoint = f"{AIRFLOW_API_BASE}/api/v1/dags/{dag_id}/dagRuns"
        auth = (airflow_user, airflow_pw)
        timestamp = datetime.now().isoformat()
        try:
            resp = requests.post(endpoint, json={"conf": payload_conf}, auth=auth)
            resp.raise_for_status()
            log_entry = {
                "decision_id": decision_id,
                "timestamp": timestamp,
                "dag_id": dag_id,
                "trigger_conf": payload_conf,
                "caller": caller,
                "reason": reason,
                "trigger_type": "dag",
                "status": "success",
                "result": resp.json(),
            }
            self._save_king_log(log_entry)
            return {"status": "success", "result": resp.json()}
        except Exception as e:
            log_entry = {
                "decision_id": decision_id,
                "timestamp": timestamp,
                "dag_id": dag_id,
                "trigger_conf": payload_conf,
                "caller": caller,
                "reason": reason,
                "trigger_type": "dag",
                "status": "error",
                "error": str(e),
            }
            self._save_king_log(log_entry)
            logging.error(f"Airflow DAG [{dag_id}] トリガー失敗: {e}")
            return {"status": "error", "error": str(e)}

    # ...（DAGトリガー系は従来どおり）...


if __name__ == "__main__":
    logging.info("--- 王の中枢機能、単独試練の儀を開始 ---")

    king = KingNoctria()

    # 例：AI/PDCA/DAGからの公式発注ラッパ使用例
    result = king.order_trade(
        symbol="USDJPY",
        side="buy",
        entry_price=157.20,
        stop_loss_price=156.70,
        capital=20000,  # 現口座資金
        risk_percent=0.007,  # 0.7%など
        caller="AIシナリオ",
        reason="AI推奨取引",
    )
    print("公式発注結果:", result)

    logging.info("--- 王の中枢機能、単独試練の儀を完了 ---")
```

---

## 📜 Fintokei ルール要約

## behavior_rules.md

# 📜 docs/rules/fintokei/behavior_rules.md

## Fintokei 一般的な行為規定（ギャンブル行為に関する規定）

### 概要
- Fintokeiでは「ギャンブル的行為」に分類されるトレードは禁止されている。
- 短期的な利益追求や無計画なポジションは、長期的な健全トレードと区別される。

### 要点
- **極端に高いリスクを取る行為**（例：許容資金に対して過度なロットサイズ）。
- **ランダム性の高い売買**（裏付けのないエントリーやマーチンゲール手法）。
- **利益目標を一度に達成するための投機的行動**。
- **短時間で大量取引を繰り返す行為**は、裁量のない「賭け」と見なされる場合がある。

### 開発における示唆
- 戦略設計は「リスク管理を伴う合理的な意思決定」として設計する必要がある。
- PDCAサイクルにおいて「ギャンブル的判定」を受けないよう、ロット・リスクをNoctusで厳格管理する。



---

## max_risk.md

# 📜 docs/rules/fintokei/max_risk.md

## オープンポジションにおける最大リスク

### 概要
- 各取引ごとに設定可能な「最大リスク割合」が規定されている。
- Sapphireプランなど口座プランごとに上限が設定されている。

### 要点
- **1取引のリスク上限**はプラン条件で決まる（例：サファイアプランで 5%）。
- 計算式：  
  `リスク額 = (エントリー価格 - ストップロス価格) × ロット × 取引単位`  
  このリスク額が口座資金に対して上限%を超えないこと。
- 違反すると「リスク違反」として即失格の対象になる。

### 開発における示唆
- Noctusが常にリスクチェックを実施し、`order_trade` 前に最大リスクを超過しないことを保証する必要がある。
# 最大リスク/ドローダウン（要約メモ）
- 日次DD上限 / 累積DD上限 / レバレッジ / 注文ロット制限 等


---

## one_trade_profit_rule.md

# 📜 docs/rules/fintokei/one_trade_profit_rule.md

## 同一銘柄・同日での利益目標達成に関するルール

### 概要
- 「1回の取引」または「同日に同じ銘柄の複数取引」で利益目標を一気に達成することは禁止されている。

### 要点
- 複数ポジションを組み合わせて同日に利益目標を達成 → 違反扱い。
- 目標利益は「段階的な利益獲得」を前提にしており、一撃狙いは禁止。
- 検出されると挑戦は失格となる。

### 開発における示唆
- Aurus/Leviaの戦略生成では「同日内に同銘柄で目標利益を超える」ような取引を回避する制御を加える。


---

## plan_sapphire.md

# 📜 docs/rules/fintokei/plan_sapphire.md

## サファイアプランの条件

### 概要
- あなたが契約している「Sapphire（サファイア）プラン」のルール要約。

### 要点
- **初期資金**: 200,000 USD
- **最大リスク**: 5%/取引
- **利益目標**: 20,000 USD（10%）
- **最大損失**: -10%（20,000 USD）
- **最小取引日数**: 10日間
- **最大取引期間**: 60日
- **1日最大損失**: -5%（10,000 USD）
- **禁止ルール**: ギャンブル行為、コピー取引、禁止行為リストに従う。

### 開発における示唆
- PDCA管理の「Plan」層で目標利益・最大リスクを自動的に監視。
- ActフェーズではFintokeiルール違反を避けるフィルターを組み込む。
# サファイアプラン（自分の契約）— 要約メモ
- このプラン固有の制限や進捗条件、資金ステージ、出金条件など


---

## prohibited_behaviors.md

# 📜 docs/rules/fintokei/prohibited_behaviors.md

## 禁止されている行為一覧

### 概要
- Fintokeiが明示的に禁止する行為群。違反が検出されると失格扱い。

### 要点
- **コピー取引やシグナルトレード**（他人の戦略を模倣する行為は禁止）。
- **アービトラージ（裁定取引）**を含む不正確定利益行為。
- **ヘッジ取引の濫用**（同一口座または関連口座で反対売買を行うなど）。
- **フロントランニング行為**（価格操作や不公平な優位性を持つ取引）。
- **禁止されている取引ツールや自動売買手法**の使用。

### 開発における示唆
- VeritasやAurusが戦略生成を行う際、これら行為を自動的に避けるルールを明文化して組み込む必要がある。
# 禁止されている行為（要約メモ）
- 例: ランウェイ利用・コピー/ミラー取引・レイテンシーアービトラージ 等


---

## 📂 プロジェクトツリー構造 (最新 snapshot)

```text
.
├── 0529progress.md
├── 0625引継ぎ書
├── 20250530.md
├── 20250603.md
├── 20250607update
├── 20250610議事録
├── 20250704_議事録
├── API_Keys.md
├── AirFlow-pip-list.md
├── AirFlow_start.md
├── Airflow 3.0.2ベースでイメージを構築しよう.md
├── Alpha Vantage API key
├── ChatGPT API Key
├── Dockerfile
├── EA_Strategies
│   ├── Aurus_Singularis
│   ├── Levia_Tempest
│   ├── Noctus_Sentinella
│   └── Prometheus_Oracle
├── FRED_API_Key
├── Hugging_Face_token
├── Makefile
├── README.md
├── README_latest.md
├── Tensor Boardの起動方法.md
├── _graveyard
│   └── 2025-09-06
│       ├── airflow_docker
│       ├── noctria_gui
│       └── src
├── action
├── actions-runner
│   ├── _diag
│   │   ├── Runner_20250912-185920-utc.log
│   │   ├── Runner_20250912-190055-utc.log
│   │   ├── Runner_20250914-094214-utc.log
│   │   ├── Worker_20250912-192351-utc.log
│   │   ├── Worker_20250912-193040-utc.log
│   │   └── Worker_20250914-100211-utc.log
│   └── _work
│       ├── _actions
│       ├── _tool
│       └── noctria_kingdom
├── add_ai_label.py
├── airflow-dockerイメージのバックアップと復元.md
├── airflow_docker
│   ├── Dockerfile_GPU
│   ├── dags
│   │   ├── __pycache__
│   │   ├── aurus_strategy_dag.py
│   │   ├── generated
│   │   ├── hermes_strategy_dag.py
│   │   ├── inventor_pipeline_dag.py
│   │   ├── levia_strategy_dag.py
│   │   ├── metaai_apply_dag.py
│   │   ├── metaai_evaluate_dag.disabled
│   │   ├── noctria_act_pipeline.py
│   │   ├── noctria_backtest_dag.py
│   │   ├── noctria_kingdom_dag.py
│   │   ├── noctria_kingdom_pdca_dag.py
│   │   ├── noctus_strategy_dag.py
│   │   ├── pdca_plan_summary_dag.py
│   │   ├── prometheus_strategy_dag.py
│   │   ├── simulate_strategy_dag.py
│   │   ├── structure_check_dag.py
│   │   ├── train_prometheus_obs8_dag.py
│   │   ├── verify_path_config_dag.py
│   │   ├── veritas_act_record_dag.py
│   │   ├── veritas_eval_dag.py
│   │   ├── veritas_eval_single_dag.py
│   │   ├── veritas_generate_dag.py
│   │   ├── veritas_pdca_dag.py
│   │   ├── veritas_push_dag.py
│   │   ├── veritas_recheck_all_dag.py
│   │   ├── veritas_recheck_dag.py
│   │   ├── veritas_refactor_dag.py
│   │   ├── veritas_replay_dag.py
│   │   └── veritas_to_order_dag.py
│   ├── data
│   │   ├── __init__.py
│   │   └── fundamental
│   ├── docker
│   │   ├── Dockerfile
│   │   ├── Dockerfile_GPU
│   │   ├── constraints.txt
│   │   ├── create_admin_user.py
│   │   ├── entrypoint.sh
│   │   ├── init
│   │   └── requirements_airflow.txt
│   ├── docker-compose.yaml
│   ├── execution
│   │   └── __init__.py
│   ├── inspect_generated_files.py
│   ├── institutions
│   │   └── central_bank_ai.py
│   ├── logs
│   │   ├── dag_id=recheck_dag
│   │   ├── dag_processor_manager
│   │   ├── king_log.json
│   │   ├── refactor_plan.json
│   │   ├── scheduler
│   │   ├── system.log
│   │   ├── veritas_eval_result.json
│   │   ├── veritas_evaluate.log
│   │   └── veritas_generate.log
│   ├── pod_templates
│   │   └── gpu_job.yaml
│   ├── pvc
│   │   ├── airflow-dags-pv.yaml
│   │   └── airflow-dags-pvc.yaml
│   ├── requirements.txt
│   ├── requirements_extra.txt
│   ├── scripts
│   │   ├── airflow-init.sh
│   │   ├── analyze_results.py
│   │   ├── apply_best_params.py
│   │   ├── download_openhermes.py
│   │   ├── download_veritas_model.py
│   │   ├── evaluate_generated_strategies.py
│   │   ├── fetch_and_clean_fundamentals.py
│   │   ├── github_push.py
│   │   ├── meta_ai_tensorboard_train.py
│   │   ├── migrate_study_sqlite_to_pg.py
│   │   ├── optimize_params.py
│   │   ├── plot_trade_performance.py
│   │   ├── prepare_usdjpy_with_fundamental.py
│   │   ├── preprocess_usdjpy_data.py
│   │   ├── run_veritas_generate_dag.py
│   │   ├── test_ollama_veritas.py
│   │   └── veritas_local_test.py
│   └── values
│       └── airflow-values.yaml
├── allowed_files.txt
├── autogen_scripts
│   ├── clean_generated_jp_lines.py
│   ├── clean_generated_md_lines.py
│   ├── clean_generated_tests.py
│   ├── find_undefined_symbols.py
│   ├── fix_missing_imports.py
│   ├── gen_prompt_for_undefined_symbols.py
│   ├── gen_requirements_from_imports.py
│   ├── generate_skeleton_files.py
│   ├── openai_noctria_dev.py
│   ├── undefined_symbols.txt
│   └── utils
│       └── cycle_logger.py
├── autogen_venv
│   ├── bin
│   │   ├── Activate.ps1
│   │   ├── activate
│   │   ├── activate.csh
│   │   ├── activate.fish
│   │   ├── distro
│   │   ├── dotenv
│   │   ├── f2py
│   │   ├── flask
│   │   ├── httpx
│   │   ├── import_pb_to_tensorboard
│   │   ├── markdown-it
│   │   ├── markdown_py
│   │   ├── normalizer
│   │   ├── numpy-config
│   │   ├── openai
│   │   ├── pip
│   │   ├── pip3
│   │   ├── pip3.12
│   │   ├── py.test
│   │   ├── pygmentize
│   │   ├── pytest
│   │   ├── python -> python3
│   │   ├── python3 -> /usr/bin/python3
│   │   ├── python3.12 -> python3
│   │   ├── saved_model_cli
│   │   ├── tensorboard
│   │   ├── tf_upgrade_v2
│   │   ├── tflite_convert
│   │   ├── toco
│   │   ├── tqdm
│   │   └── wheel
│   ├── include
│   │   └── python3.12
│   ├── lib
│   │   └── python3.12
│   ├── lib64 -> lib
│   └── pyvenv.cfg
├── callmemo_20250602.md
├── codex_reports
│   ├── context
│   │   └── allowed_files.txt
│   ├── decision_registry.jsonl
│   ├── inventor_last.json
│   ├── patches
│   │   └── 0001_tests-align-fallback-size-guard_20250911-013855.patch
│   └── repo_xray.md
├── config
│   ├── airflow.cfg.example
│   └── risk_policy.yml
├── configs
│   └── profiles.yaml
├── conversation_history_manager.py
├── cpu.packages.txt
├── cpu.requirements.txt
├── current_requirements.txt
├── dags
│   └── example_dag.py
├── data
│   ├── act_logs
│   │   ├── git_push_history
│   │   └── veritas_adoptions
│   ├── anomaly_detection.py
│   ├── decisions
│   │   └── ledger.csv
│   ├── ensemble_learning.py
│   ├── explainable_ai.py
│   ├── fundamental
│   │   ├── fetch_and_clean_fundamentals.py
│   │   ├── fetch_fred_data.py
│   │   └── fetch_fred_data_cleaned.py
│   ├── fundamental_analysis.py
│   ├── high_frequency_trading.py
│   ├── institutional_order_monitor.py
│   ├── lstm_data_processor.py
│   ├── market_regime_detector.py
│   ├── models
│   │   ├── metaai_model_20250919-132614.zip
│   │   ├── metaai_model_latest.zip -> /opt/airflow/data/models/metaai_model_20250919-132614.zip
│   │   ├── production
│   │   └── prometheus
│   ├── multi_objective_optimizer.py
│   ├── pdca_logs
│   │   └── veritas_orders
│   ├── policy
│   ├── preprocessed_usdjpy_with_fundamental.csv
│   ├── preprocessing
│   │   ├── integrate_fundamental_data.py
│   │   ├── integrate_multiple_fundamental_data.py
│   │   └── preprocess_usdjpy_1h.py
│   ├── processed_data_handler.py
│   ├── quantum_computing_integration.py
│   ├── raw_data_loader.py
│   ├── repo_dependencies.mmd
│   ├── sample_test_data.csv
│   ├── sentiment_analysis.py
│   ├── stats
│   │   ├── aurus_strategy_20250707.json
│   │   ├── levia_strategy_20250707.json
│   │   ├── noctus_strategy_20250707.json
│   │   ├── prometheus_strategy_20250707.json
│   │   ├── veritas_eval_result.json
│   │   └── {strategy}.json
│   └── tradingview_fetcher.py
├── deploy_scripts
│   └── deploy.py
├── docker use.md
├── docker_tensorflow_gpu_setup.md
├── docs
│   ├── 00_index
│   │   ├── 00-INDEX.md
│   │   └── 00-INDEX.md.bak
│   ├── Geminiリファクタリング案
│   ├── Next Actions — Noctria PDCA Hardening Plan.md
│   ├── Next Actions — Noctria PDCA Hardening Plan.md.bak
│   ├── Noctria Kingdom Plan層 標準特徴量セット（v2025.08）
│   ├── Noctria Kingdom 全体リファクタリング計画（v3.0対応）
│   ├── Noctria_Kingdom_System_Design_v2025-08.md
│   ├── Noctria_Kingdom_System_Design_v2025-08.md.bak
│   ├── README.md
│   ├── README.md.bak
│   ├── _build
│   │   └── logs
│   ├── _generated
│   │   ├── diff_report.md
│   │   ├── diff_report.md.bak
│   │   ├── dummy
│   │   ├── governance_prompt_full.md
│   │   ├── tree_snapshot.txt
│   │   └── update_docs.log
│   ├── _partials
│   │   └── apis
│   ├── _partials_full
│   │   └── docs
│   ├── adrs
│   │   ├── ADRs.md
│   │   └── ADRs.md.bak
│   ├── airflow
│   │   └── DAG-PDCA-Recheck.md
│   ├── api_reference.md
│   ├── api_reference.md.bak
│   ├── apis
│   │   ├── API.md
│   │   ├── API.md.bak
│   │   ├── Do-Layer-Contract.md
│   │   ├── Do-Layer-Contract.md.bak
│   │   ├── Do-Layer-OrderAPI-Spec.md
│   │   ├── PDCA-API-Design-Guidelines.md
│   │   ├── PDCA-GUI-API-Spec.md
│   │   ├── PDCA-Recheck-API-Spec.md
│   │   ├── observability
│   │   └── openapi
│   ├── architecture
│   │   ├── Architecture-Overview.md
│   │   ├── Architecture-Overview.md.bak
│   │   ├── BrokerAdapter-Design.md
│   │   ├── Design-Governance-2025-08-24.md
│   │   ├── NonFunctionalRequirements-DoLayer.md
│   │   ├── Outbox-Worker-Protocol.md
│   │   ├── PDCA-Spec.md
│   │   ├── Plan-Layer.md
│   │   ├── Plan-Layer.md.bak
│   │   ├── canon.yaml
│   │   ├── components
│   │   ├── contracts
│   │   ├── diagrams
│   │   ├── patterns
│   │   ├── pdca_interface_matrix.mmd
│   │   └── schema
│   ├── architecture.md`
│   ├── architecture_bak.md
│   ├── architecture_bak.md.bak
│   ├── autodoc_rules.yaml
│   ├── codex
│   │   ├── Codex_Noctria.md
│   │   ├── Codex_Noctria_Agents.md
│   │   └── codex_noctria_policy.yaml
│   ├── data_handling.md
│   ├── data_handling.md.bak
│   ├── dev
│   │   └── PDCA-Contract-Tests-and-Codegen.md
│   ├── diagnostics
│   │   └── tree_snapshot.txt
│   ├── governance
│   │   ├── Coding-Standards.md
│   │   ├── Coding-Standards.md.bak
│   │   ├── Vision-Governance.md
│   │   └── Vision-Governance.md.bak
│   ├── howto
│   │   ├── howto-*.md
│   │   └── howto-*.md.bak
│   ├── incidents
│   │   ├── Incident-Postmortems.md
│   │   └── Incident-Postmortems.md.bak
│   ├── integration
│   │   └── Airflow-RestAdapter-Design.md
│   ├── knowledge.md
│   ├── knowledge.md.bak
│   ├── misc
│   │   ├── 0529progress.md
│   │   ├── 0529progress.md.bak
│   │   ├── 20250530.md
│   │   ├── 20250530.md.bak
│   │   ├── 20250603.md
│   │   ├── 20250603.md.bak
│   │   ├── API_Keys.md.bak
│   │   ├── AirFlow-pip-list.md
│   │   ├── AirFlow-pip-list.md.bak
│   │   ├── AirFlow_start.md
│   │   ├── AirFlow_start.md.bak
│   │   ├── Airflow 3.0.2ベースでイメージを構築しよう.md
│   │   ├── Airflow 3.0.2ベースでイメージを構築しよう.md.bak
│   │   ├── README.md
│   │   ├── README.md.bak
│   │   ├── README_latest.md
│   │   ├── README_latest.md.bak
│   │   ├── Tensor Boardの起動方法.md
│   │   ├── Tensor Boardの起動方法.md.bak
│   │   ├── airflow-dockerイメージのバックアップと復元.md
│   │   ├── airflow-dockerイメージのバックアップと復元.md.bak
│   │   ├── callmemo_20250602.md
│   │   ├── callmemo_20250602.md.bak
│   │   ├── docker use.md
│   │   ├── docker use.md.bak
│   │   ├── docker_tensorflow_gpu_setup.md
│   │   ├── docker_tensorflow_gpu_setup.md.bak
│   │   ├── how-to-use-git.md
│   │   ├── how-to-use-git.md.bak
│   │   ├── latest_tree_and_functions.md
│   │   ├── latest_tree_and_functions.md.bak
│   │   ├── tree_L3_snapshot.txt
│   │   ├── カスタムAirflowイメージを作る.md
│   │   └── カスタムAirflowイメージを作る.md.bak
│   ├── models
│   │   ├── ModelCard-Prometheus-PPO.md
│   │   ├── ModelCard-Prometheus-PPO.md.bak
│   │   ├── Strategy-Lifecycle.md
│   │   └── Strategy-Lifecycle.md.bak
│   ├── observability
│   │   ├── DoLayer-Metrics.md
│   │   ├── Idempotency-Ledger.md
│   │   ├── Observability.md
│   │   └── Observability.md.bak
│   ├── operations
│   │   ├── Airflow-DAGs.md
│   │   ├── Airflow-DAGs.md.bak
│   │   ├── Config-Registry.md
│   │   ├── Config-Registry.md.bak
│   │   ├── PDCA
│   │   ├── Runbook-PDCA.md
│   │   ├── Runbooks.md
│   │   ├── Runbooks.md.bak
│   │   └── dev-flow.md
│   ├── optimization_notes.md
│   ├── optimization_notes.md.bak
│   ├── plan_feature_spec.md
│   ├── plan_feature_spec.md.bak
│   ├── platform
│   │   ├── Config-Reference-DoLayer.md
│   │   └── RateLimit-Quota-DoLayer.md
│   ├── qa
│   │   ├── DoLayer-E2E-TestPlan.md
│   │   ├── Testing-And-QA.md
│   │   └── Testing-And-QA.md.bak
│   ├── risks
│   │   ├── Risk-Register.md
│   │   └── Risk-Register.md.bak
│   ├── roadmap
│   │   ├── Release-Notes.md
│   │   ├── Release-Notes.md.bak
│   │   ├── Roadmap-OKRs.md
│   │   └── Roadmap-OKRs.md.bak
│   ├── rules
│   │   └── fintokei
│   ├── rurles
│   ├── security
│   │   ├── AuthN-AuthZ-DoLayer.md
│   │   ├── Secrets-Policy.md
│   │   ├── Security-And-Access.md
│   │   └── Security-And-Access.md.bak
│   ├── strategy_manual.md
│   ├── strategy_manual.md.bak
│   ├── structure_principles.md
│   ├── structure_principles.md.bak
│   ├── ui
│   │   └── PDCA-GUI-Screens.md
│   ├── wrap_rules.yaml
│   ├── 最新の手引き
│   ├── 議事録20250721
│   └── 👑 プロジェクト「Noctria Kingdom」開発推進プラン提案
├── experts
│   ├── aurus_singularis.mq5
│   ├── auto_evolution.mq5
│   ├── core_EA.mq5
│   ├── levia_tempest.mq5
│   ├── noctria_executor.mq5
│   ├── noctus_sentinella.mq5
│   ├── prometheus_oracle.mq5
│   └── quantum_prediction.mq5
├── generated_code
│   ├── __init__.py
│   ├── chat_log.txt
│   ├── data_collection.py
│   ├── data_collector.py
│   ├── data_fetcher.py
│   ├── data_handler.py
│   ├── data_pipeline.py
│   ├── data_preprocessing.py
│   ├── data_preprocessor.py
│   ├── doc_turn1.py
│   ├── doc_turn2.py
│   ├── doc_turn3.py
│   ├── doc_turn4.py
│   ├── doc_turn5.py
│   ├── doc_turn6.py
│   ├── example.py
│   ├── feature_engineering.py
│   ├── gui_management.py
│   ├── implement_turn1.py
│   ├── implement_turn2.py
│   ├── implement_turn3.py
│   ├── implement_turn4.py
│   ├── implement_turn5.py
│   ├── implement_turn6.py
│   ├── king_noctria.py
│   ├── main.py
│   ├── market_data.py
│   ├── ml_model.py
│   ├── model_design.py
│   ├── model_evaluation.py
│   ├── model_selection.py
│   ├── model_training.py
│   ├── order_execution.py
│   ├── order_executor.py
│   ├── performance_evaluation.py
│   ├── risk_management.py
│   ├── risk_manager.py
│   ├── src
│   │   ├── core
│   │   ├── data_preprocessing.py
│   │   ├── model_training.py
│   │   └── order_execution.py
│   ├── strategy.py
│   ├── strategy_decider.py
│   ├── strategy_execution.py
│   ├── strategy_model.py
│   ├── test_data_collection.py
│   ├── test_data_fetcher.py
│   ├── test_data_preprocessing.py
│   ├── test_feature_engineering.py
│   ├── test_ml_model.py
│   ├── test_model_design.py
│   ├── test_model_evaluation.py
│   ├── test_model_training.py
│   ├── test_order_execution.py
│   ├── test_order_executor.py
│   ├── test_risk_manager.py
│   ├── test_strategy_decider.py
│   ├── test_strategy_execution.py
│   ├── test_strategy_model.py
│   ├── test_trading_strategy.py
│   ├── test_trading_system.py
│   ├── test_turn1.py
│   ├── trading_strategy.py
│   └── veritas_ml.py
├── how-to-use-git.md
├── latest_tree_and_functions.md
├── llm_server
│   ├── docker-compose.gpu.yaml
│   ├── llm_prompt_builder.py
│   ├── main.py
│   ├── requirements_server.txt
│   ├── veritas_eval_api.py
│   └── veritas_llm_server.py
├── logs
│   ├── dag_id=aurus_strategy_dag
│   │   ├── run_id=manual__2025-07-19T12:27:17.458835+00:00
│   │   ├── run_id=manual__2025-07-19T12:35:49.384580+00:00
│   │   ├── run_id=manual__2025-07-19T12:37:56.199658+00:00
│   │   ├── run_id=manual__2025-07-19T12:44:17.393206+00:00
│   │   ├── run_id=manual__2025-07-19T13:06:44.595115+00:00
│   │   └── run_id=manual__2025-07-19T13:11:17.002374+00:00
│   ├── dag_id=levia_strategy_dag
│   │   ├── run_id=manual__2025-07-19T12:48:26.775551+00:00
│   │   ├── run_id=manual__2025-07-19T12:53:48.623600+00:00
│   │   └── run_id=manual__2025-07-19T12:59:42.668761+00:00
│   ├── dag_id=noctria_kingdom_pdca_dag
│   │   ├── run_id=__airflow_temporary_run_2025-08-10T20:01:30.724354+00:00__
│   │   ├── run_id=__airflow_temporary_run_2025-08-10T20:03:04.417774+00:00__
│   │   ├── run_id=manual__2025-07-18T02:08:54+09:00
│   │   ├── run_id=manual__2025-07-19T01:52:05+09:00
│   │   ├── run_id=manual__2025-07-19T01:54:27+09:00
│   │   ├── run_id=manual__2025-07-19T01:57:16+09:00
│   │   ├── run_id=manual__2025-07-19T11:32:55+09:00
│   │   ├── run_id=manual__2025-07-19T15:45:13+09:00
│   │   ├── run_id=manual__2025-07-19T15:50:23+09:00
│   │   ├── run_id=manual__2025-07-19T15:53:19+09:00
│   │   ├── run_id=manual__2025-07-19T16:51:16+09:00
│   │   ├── run_id=manual__2025-07-19T17:44:34+09:00
│   │   ├── run_id=manual__2025-07-19T17:50:37+09:00
│   │   ├── run_id=manual__2025-07-19T19:04:58+09:00
│   │   ├── run_id=manual__2025-07-19T21:08:34+09:00
│   │   ├── run_id=manual__2025-07-19T21:13:56+09:00
│   │   ├── run_id=manual__2025-07-19T21:17:24+09:00
│   │   ├── run_id=manual__2025-07-19T22:13:13+09:00
│   │   ├── run_id=manual__2025-07-19T22:18:41+09:00
│   │   ├── run_id=manual__2025-07-19T22:23:47+09:00
│   │   ├── run_id=manual__2025-07-19T23:29:26+09:00
│   │   ├── run_id=manual__2025-07-19T23:32:15+09:00
│   │   ├── run_id=manual__2025-07-19T23:39:20+09:00
│   │   ├── run_id=manual__2025-07-19T23:42:30+09:00
│   │   ├── run_id=manual__2025-07-19T23:51:26+09:00
│   │   ├── run_id=manual__2025-07-20T00:43:34+09:00
│   │   ├── run_id=manual__2025-07-20T00:50:59+09:00
│   │   ├── run_id=manual__2025-07-20T01:00:36+09:00
│   │   ├── run_id=manual__2025-07-20T01:11:13+09:00
│   │   ├── run_id=manual__2025-07-20T03:58:31+09:00
│   │   ├── run_id=manual__2025-08-10T12:01:43+00:00
│   │   ├── run_id=manual__2025-08-10T20:05:02+00:00
│   │   ├── run_id=manual__2025-08-10T20:05:41+00:00
│   │   ├── run_id=manual__2025-08-10T20:07:31+00:00
│   │   ├── run_id=manual__2025-08-10T20:44:45+00:00
│   │   ├── run_id=scheduled__2025-07-25T00:00:00+00:00
│   │   ├── run_id=scheduled__2025-07-26T00:00:00+00:00
│   │   ├── run_id=scheduled__2025-08-03T00:00:00+00:00
│   │   ├── run_id=scheduled__2025-08-09T00:00:00+00:00
│   │   └── run_id=scheduled__2025-08-10T00:00:00+00:00
│   ├── dag_id=noctria_kingdom_royal_council_dag
│   │   ├── run_id=manual__2025-08-03T19:40:37.841326+00:00
│   │   ├── run_id=manual__2025-08-04T18:45:12.159045+00:00
│   │   ├── run_id=manual__2025-08-04T18:50:58.218785+00:00
│   │   ├── run_id=scheduled__2025-08-03T18:00:00+00:00
│   │   ├── run_id=scheduled__2025-08-03T19:00:00+00:00
│   │   ├── run_id=scheduled__2025-08-04T15:00:00+00:00
│   │   ├── run_id=scheduled__2025-08-04T16:00:00+00:00
│   │   └── run_id=scheduled__2025-08-04T17:00:00+00:00
│   ├── dag_id=train_prometheus_obs8
│   │   ├── run_id=manual__2025-08-11T14:04:53+00:00
│   │   ├── run_id=manual__2025-08-11T14:12:13+00:00
│   │   ├── run_id=manual__2025-08-11T14:18:10+00:00
│   │   ├── run_id=manual__2025-08-11T14:19:41+00:00
│   │   ├── run_id=manual__2025-08-11T14:22:19+00:00
│   │   ├── run_id=manual__2025-08-11T14:33:11+00:00
│   │   ├── run_id=manual__2025-08-11T15:44:05+00:00
│   │   ├── run_id=manual__2025-08-11T16:20:12.935706+00:00
│   │   ├── run_id=manual__2025-08-11T16:21:36.023694+00:00
│   │   ├── run_id=manual__2025-08-11T16:27:02.701382+00:00
│   │   └── run_id=manual__2025-08-11T17:21:59.539332+00:00
│   ├── dag_id=veritas_generate_dag
│   │   ├── run_id=manual__2025-07-27T07:17:06.241792+00:00
│   │   ├── run_id=manual__2025-07-27T08:04:13.060137+00:00
│   │   ├── run_id=manual__2025-07-27T08:23:43.497722+00:00
│   │   ├── run_id=manual__2025-07-27T10:11:49.280643+00:00
│   │   ├── run_id=manual__2025-07-27T10:45:22.152873+00:00
│   │   ├── run_id=manual__2025-07-27T13:58:55.815154+00:00
│   │   └── run_id=manual__2025-08-03T19:47:58.228649+00:00
│   ├── dag_processor_manager
│   │   └── dag_processor_manager.log
│   ├── dependency_report.json
│   ├── observability_gui_latency.jsonl
│   ├── refactor_plan.json
│   ├── scheduler
│   │   ├── 2025-07-11
│   │   ├── 2025-07-12
│   │   ├── 2025-07-17
│   │   ├── 2025-07-18
│   │   ├── 2025-07-19
│   │   ├── 2025-07-26
│   │   ├── 2025-07-27
│   │   ├── 2025-08-01
│   │   ├── 2025-08-02
│   │   ├── 2025-08-03
│   │   ├── 2025-08-04
│   │   ├── 2025-08-06
│   │   ├── 2025-08-07
│   │   ├── 2025-08-08
│   │   ├── 2025-08-09
│   │   ├── 2025-08-10
│   │   ├── 2025-08-11
│   │   ├── 2025-08-12
│   │   ├── 2025-08-13
│   │   ├── 2025-08-14
│   │   └── latest -> 2025-08-14
│   ├── tb
│   │   └── optuna_ppo
│   └── trade_history_2025-05-31_to_2025-06-07.csv
├── migrations
│   ├── 20250824_add_idempo_ledger.sql
│   ├── 20250825_plan_news_enrichment.sql
│   ├── 20250915_agents_pdca.sql
│   ├── 20250915_chronicle.sql
│   └── 2025xxxx_add_outbox_orders.sql
├── mt5_test.py
├── noctria_gui
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── __init__.cpython-312.pyc
│   │   └── main.cpython-312.pyc
│   ├── backend
│   │   ├── Dockerfile
│   │   ├── __init__.py
│   │   ├── app
│   │   ├── dag_runner.py
│   │   ├── requirements.txt
│   │   └── xcom_fetcher.py
│   ├── docker-compose.override.yml
│   ├── main.py
│   ├── requirements.txt
│   ├── requirements_gui.txt
│   ├── routes
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── act_adopt.py
│   │   ├── act_history.py
│   │   ├── act_history_detail.py
│   │   ├── adoptions.py
│   │   ├── ai_detail.py
│   │   ├── ai_routes.py
│   │   ├── airflow_runs.py
│   │   ├── app_main.py
│   │   ├── backtest_results.py
│   │   ├── backtests.py
│   │   ├── chat_api.py
│   │   ├── chat_history_api.py
│   │   ├── chat_history_db_api.py
│   │   ├── codex.py
│   │   ├── dashboard.py
│   │   ├── decision_registry.py
│   │   ├── devcycle_history.py
│   │   ├── git_tags.py
│   │   ├── hermes.py
│   │   ├── home_routes.py
│   │   ├── king_routes.py
│   │   ├── logs_routes.py
│   │   ├── obs_latency_dashboard.py
│   │   ├── observability.py
│   │   ├── observability_latency.py
│   │   ├── path_checker.py
│   │   ├── pdca.py
│   │   ├── pdca_api.py
│   │   ├── pdca_api_details.py
│   │   ├── pdca_push.py
│   │   ├── pdca_recheck.py
│   │   ├── pdca_routes.py
│   │   ├── pdca_summary.py
│   │   ├── pdca_widgets.py
│   │   ├── plan_news.py
│   │   ├── prometheus_routes.py
│   │   ├── push.py
│   │   ├── push_history.py
│   │   ├── statistics
│   │   ├── statistics.py
│   │   ├── statistics_compare.py
│   │   ├── statistics_detail.py
│   │   ├── statistics_ranking.py
│   │   ├── statistics_routes.py
│   │   ├── statistics_scoreboard.py
│   │   ├── statistics_tag_ranking.py
│   │   ├── strategy_detail.py
│   │   ├── strategy_heatmap.py
│   │   ├── strategy_routes.py
│   │   ├── tag_heatmap.py
│   │   ├── tag_summary.py
│   │   ├── tag_summary_detail.py
│   │   ├── task_api.py
│   │   ├── task_manager.py
│   │   ├── trigger.py
│   │   ├── upload.py
│   │   └── upload_history.py
│   ├── services
│   │   ├── __pycache__
│   │   ├── act_log_service.py
│   │   ├── dashboard_service.py
│   │   ├── plan_news_service.py
│   │   ├── push_history_service.py
│   │   ├── statistics_service.py
│   │   ├── strategy_handler.py
│   │   ├── tag_summary_service.py
│   │   └── upload_actions.py
│   ├── static
│   │   ├── codex_reports
│   │   ├── hud_style.css
│   │   ├── js
│   │   ├── style.css
│   │   └── vendor
│   ├── templates
│   │   ├── act_adopt.html
│   │   ├── act_history.html
│   │   ├── act_history_detail.html
│   │   ├── adoptions.html
│   │   ├── ai_detail.html
│   │   ├── ai_list.html
│   │   ├── airflow_runs.html
│   │   ├── backtest_detail.html
│   │   ├── backtest_report.html
│   │   ├── backtests
│   │   ├── backtests.html
│   │   ├── base.html
│   │   ├── base_hud.html
│   │   ├── base_layout.html
│   │   ├── chat_history.html
│   │   ├── chat_ui.html
│   │   ├── codex.html
│   │   ├── dashboard.html
│   │   ├── decision_registry.html
│   │   ├── devcycle_history.html
│   │   ├── git_tags.html
│   │   ├── king_history.html
│   │   ├── king_prometheus.html
│   │   ├── log_dashboard.html
│   │   ├── logs_dashboard.html
│   │   ├── obs_latency.html
│   │   ├── obs_latency_dashboard.html
│   │   ├── partials
│   │   ├── pdca
│   │   ├── pdca_control.html
│   │   ├── pdca_dashboard.html
│   │   ├── pdca_history.html
│   │   ├── pdca_latency_daily.html
│   │   ├── pdca_summary.html
│   │   ├── pdca_timeline.html
│   │   ├── plan_news.html
│   │   ├── push_history.html
│   │   ├── push_history_detail.html
│   │   ├── scoreboard.html
│   │   ├── statistics_compare.html
│   │   ├── statistics_dashboard.html
│   │   ├── statistics_detail.html
│   │   ├── statistics_ranking.html
│   │   ├── statistics_scoreboard.html
│   │   ├── statistics_tag_ranking.html
│   │   ├── strategies
│   │   ├── strategy_compare.html
│   │   ├── strategy_compare_result.html
│   │   ├── strategy_detail.html
│   │   ├── tag_detail.html
│   │   ├── tag_summary.html
│   │   ├── task_list.html
│   │   ├── trigger.html
│   │   ├── upload_history.html
│   │   ├── upload_strategy.html
│   │   └── widgets
│   └── trigger_pdca_api.py
├── optimization
│   └── reinforcement_learning.py
├── order_api.py
├── pytest.ini
├── requirements
│   └── requirements_veritas.txt
├── requirements-codex-gpu.txt
├── requirements-codex.txt
├── requirements.txt
├── requirements_gui.txt
├── requirements_veritas.txt
├── scripts
│   ├── __pycache__
│   │   ├── _scribe.cpython-312.pyc
│   │   └── show_last_inventor_decision.cpython-312.pyc
│   ├── _pdca_db.py
│   ├── _scribe.py
│   ├── apply_codex_patch.sh
│   ├── backtest_runner.py
│   ├── build_context.py
│   ├── check_imports.py
│   ├── codex_progress_check.py
│   ├── db-migrate.sh
│   ├── fix_docs.sh
│   ├── gen_governance_prompt.py
│   ├── gen_graphs.py
│   ├── generate_docs_diff_report.py
│   ├── generate_handoff.py
│   ├── git_playbook.sh
│   ├── init_obs_schema.sql
│   ├── insert_autodoc_markers.py
│   ├── local_ci.sh
│   ├── local_ci_gpu.sh
│   ├── map_tests.py
│   ├── mark_heavy_tests.sh
│   ├── noctria-docs.sh
│   ├── noctria_dead_code_detector.py
│   ├── pdca_agent.py
│   ├── repo_xray.py
│   ├── run_codex_cycle.sh
│   ├── run_pdca_agents.py
│   ├── search_redirects.py
│   ├── show_last_inventor_decision.py
│   ├── show_last_inventor_decision.py.bak
│   ├── trigger_backtest_dag.py
│   ├── trigger_noctria_act.sh
│   ├── update_docs_from_index.py
│   └── wrap_sections_with_autodoc.py
├── setup.packages.sh
├── setup.python.sh
├── setup.sources.sh
├── src
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── __init__.cpython-311.pyc
│   │   └── __init__.cpython-312.pyc
│   ├── agents
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   └── guardrails
│   ├── codex
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── agents
│   │   ├── mini_loop.py
│   │   ├── quarantine.sh
│   │   ├── run_codex_cycle.py
│   │   └── tools
│   ├── codex_config
│   │   ├── __init__.py
│   │   └── agents.yaml
│   ├── codex_reports
│   │   ├── context
│   │   ├── dead_code
│   │   ├── graphs
│   │   ├── harmonia_review.md
│   │   ├── inventor_suggestions.json
│   │   ├── inventor_suggestions.md
│   │   ├── latest_codex_cycle.md
│   │   ├── patches
│   │   ├── patches_index.md
│   │   ├── pdca_log.db
│   │   ├── pdca_log.db-shm
│   │   ├── pdca_log.db-wal
│   │   ├── proxy_pytest_last.log
│   │   ├── pytest_last.xml
│   │   ├── pytest_summary.md
│   │   ├── ruff
│   │   └── tmp.json
│   ├── core
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── act_service.py
│   │   ├── airflow_client.py
│   │   ├── config.yaml
│   │   ├── dag_trigger.py
│   │   ├── data
│   │   ├── data_loader.py
│   │   ├── db_logging.py
│   │   ├── decision_hooks.py
│   │   ├── decision_registry.py
│   │   ├── env_config.py
│   │   ├── git_utils.py
│   │   ├── king_noctria.py
│   │   ├── logger.py
│   │   ├── logs
│   │   ├── market_loader.py
│   │   ├── meta_ai.py
│   │   ├── meta_ai_env.py
│   │   ├── meta_ai_env_with_fundamentals.py
│   │   ├── noctriaenv.py
│   │   ├── path_config.py
│   │   ├── pdca_log_parser.py
│   │   ├── policy_engine.py
│   │   ├── risk_control.py
│   │   ├── risk_manager.py
│   │   ├── settings.py
│   │   ├── strategy_evaluator.py
│   │   ├── strategy_optimizer_adjusted.py
│   │   ├── task_scheduler.py
│   │   ├── trace.py
│   │   ├── utils.py
│   │   └── veritas_trigger_api.py
│   ├── dammy
│   ├── decision
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── decision_engine.py
│   │   └── quality_gate.py
│   ├── e2e
│   │   ├── __init__.py
│   │   └── decision_minidemo.py
│   ├── envs
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   └── noctria_fx_trading_env.py
│   ├── execution
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── challenge_monitor.py
│   │   ├── execution_manager.py
│   │   ├── generate_order_json.py
│   │   ├── optimized_order_execution.py
│   │   ├── order_execution.py
│   │   ├── risk_gate.py
│   │   ├── risk_policy.py
│   │   ├── save_model_metadata.py
│   │   ├── simulate_official_strategy.py
│   │   ├── switch_to_best_model.py
│   │   ├── tensorflow_task.py
│   │   ├── trade_analysis.py
│   │   ├── trade_monitor.py
│   │   └── trade_simulator.py
│   ├── hermes
│   │   ├── __pycache__
│   │   ├── models
│   │   └── strategy_generator.py
│   ├── noctria_ai
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── dammy
│   │   └── noctria.py
│   ├── order_execution.py
│   ├── plan_data
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── adapter_to_decision.py
│   │   ├── adapter_to_decision_cli.py
│   │   ├── ai_adapter.py
│   │   ├── analyzer.py
│   │   ├── anomaly_detector.py
│   │   ├── collector.py
│   │   ├── contracts.py
│   │   ├── feature_spec.py
│   │   ├── features.py
│   │   ├── inventor.py
│   │   ├── kpi_minidemo.py
│   │   ├── llm_plan_prompt.py
│   │   ├── noctus_gate.py
│   │   ├── observability.py
│   │   ├── observation_adapter.py
│   │   ├── pdca_summary_service.py
│   │   ├── plan_to_all_minidemo.py
│   │   ├── plan_to_aurus_demo.py
│   │   ├── plan_to_hermes_demo.py
│   │   ├── plan_to_levia_demo.py
│   │   ├── plan_to_noctus_demo.py
│   │   ├── plan_to_prometheus_demo.py
│   │   ├── plan_to_veritas_demo.py
│   │   ├── profile_loader.py
│   │   ├── quality_gate.py
│   │   ├── run_inventor.py
│   │   ├── run_pdca_plan_workflow.py
│   │   ├── run_with_profile.py
│   │   ├── standard_feature_schema.py
│   │   ├── statistics.py
│   │   ├── strategy_adapter.py
│   │   ├── test_plan_analyzer.py
│   │   └── trace.py
│   ├── scripts
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── apply_best_params_to_kingdom.py
│   │   ├── apply_best_params_to_metaai.py
│   │   ├── check_path_integrity.sh
│   │   ├── evaluate_metaai_model.py
│   │   ├── evaluate_single_strategy.py
│   │   ├── generate_dummy_logs.py
│   │   ├── generate_path_mapping.py
│   │   ├── github_push_adopted_strategies.py
│   │   ├── log_pdca_result.py
│   │   ├── meta_ai_tensorboard_train.py
│   │   ├── optimize_params_with_optuna.py
│   │   ├── push_generated_strategy.py
│   │   ├── push_generated_strategy_to_github_dag.py
│   │   ├── recheck_runner.py
│   │   └── tag_adoption_log.py
│   ├── strategies
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── adaptive_trading.py
│   │   ├── aurus_singularis.py
│   │   ├── auto_adjustment.py
│   │   ├── evolutionary
│   │   ├── hermes_cognitor.py
│   │   ├── levia_tempest.py
│   │   ├── market_analysis.py
│   │   ├── noctus_sentinella.py
│   │   ├── official
│   │   ├── portfolio_optimizer.py
│   │   ├── prometheus_oracle.py
│   │   ├── quantum_prediction.py
│   │   ├── reinforcement
│   │   ├── self_play.py
│   │   ├── strategy_runner.py
│   │   └── veritas_generated
│   ├── tools
│   │   ├── apply_path_fixes.py
│   │   ├── apply_refactor_plan_v2.py
│   │   ├── cleanup_commands.sh
│   │   ├── dependency_analyzer.py
│   │   ├── diagnose_dependencies.py
│   │   ├── export_all_logs.py
│   │   ├── fix_import_paths.py
│   │   ├── fix_logger_usage.py
│   │   ├── fix_path_violations.py
│   │   ├── generate_cleanup_script.py
│   │   ├── generate_github_template_summary.py
│   │   ├── generate_readme_summary.py
│   │   ├── generate_refactor_plan.py
│   │   ├── generate_routes_init.py
│   │   ├── git_commit_veritas_gui.sh
│   │   ├── git_handler.py
│   │   ├── hardcoded_path_replacer.py
│   │   ├── push_official_strategy_to_github.py
│   │   ├── refactor_manager.py
│   │   ├── reorganize_docs.py
│   │   ├── resolve_merge_conflicts.py
│   │   ├── save_tree_snapshot.py
│   │   ├── scan_and_fix_paths.py
│   │   ├── scan_refactor_plan.py
│   │   ├── show_timeline.py
│   │   ├── strategy_classifier.py
│   │   ├── structure_auditor.py
│   │   ├── structure_refactor.py
│   │   ├── tag_summary_generator.py
│   │   ├── verify_imports.py
│   │   ├── verify_path_config.py
│   │   └── verify_path_config_usage.py
│   ├── training
│   │   └── train_prometheus.py
│   ├── utils
│   │   └── model_io.py
│   └── veritas
│       ├── __pycache__
│       ├── evaluate_veritas.py
│       ├── generate
│       ├── generate_strategy_file.py
│       ├── models
│       ├── promote_accepted_strategies.py
│       ├── record_act_log.py
│       ├── strategy_generator.py
│       ├── veritas_airflow_executor.py
│       ├── veritas_generate_strategy.py
│       └── veritas_machina.py
├── ssh_test.txt
├── system_start
├── tests
│   ├── __pycache__
│   │   ├── conftest.cpython-312-pytest-7.4.4.pyc
│   │   ├── conftest.cpython-312-pytest-8.4.2.pyc
│   │   ├── test_decision_fallback_size.cpython-312-pytest-7.4.4.pyc
│   │   ├── test_decision_fallback_size.cpython-312-pytest-8.4.2.pyc
│   │   ├── test_decision_fallback_size.cpython-312.pyc
│   │   ├── test_dqn_agent.cpython-312.pyc
│   │   ├── test_dummy.cpython-312.pyc
│   │   ├── test_floor_mod.cpython-312.pyc
│   │   ├── test_floor_mod_gpu.cpython-312.pyc
│   │   ├── test_harmonia_rerank.cpython-312-pytest-7.4.4.pyc
│   │   ├── test_harmonia_rerank.cpython-312-pytest-8.4.2.pyc
│   │   ├── test_harmonia_rerank.cpython-312.pyc
│   │   ├── test_meta_ai_env_rl.cpython-312.pyc
│   │   ├── test_meta_ai_rl.cpython-312.pyc
│   │   ├── test_meta_ai_rl_longrun.cpython-312.pyc
│   │   ├── test_meta_ai_rl_real_data.cpython-312.pyc
│   │   ├── test_minidemo_smoke.cpython-312.pyc
│   │   ├── test_mt5_connection.cpython-312.pyc
│   │   ├── test_noctria.cpython-312-pytest-8.4.2.pyc
│   │   ├── test_noctria.cpython-312.pyc
│   │   ├── test_noctria_master_ai.cpython-312.pyc
│   │   ├── test_noctus_gate_block.cpython-312-pytest-8.4.2.pyc
│   │   ├── test_noctus_gate_block.cpython-312.pyc
│   │   ├── test_path_config.cpython-312.pyc
│   │   ├── test_policy_guard.cpython-312-pytest-8.4.2.pyc
│   │   ├── test_policy_guard.cpython-312.pyc
│   │   ├── test_quality_gate_alerts.cpython-312.pyc
│   │   ├── test_trace_and_integration.cpython-312.pyc
│   │   └── test_trace_decision_e2e.cpython-312.pyc
│   ├── backtesting
│   │   └── dqn_backtest.py
│   ├── backtesting.py
│   ├── conftest.py
│   ├── cuda-keyring_1.1-1_all.deb
│   ├── execute_order_test.py
│   ├── forward_test_meta_ai.py
│   ├── integration_test_noctria.py
│   ├── run_ai_trading_loop.py
│   ├── stress_tests.py
│   ├── test_decision_fallback_size.py
│   ├── test_dqn_agent.py
│   ├── test_dummy.py
│   ├── test_floor_mod.py
│   ├── test_floor_mod_gpu.py
│   ├── test_harmonia_rerank.py
│   ├── test_meta_ai_env_rl.py
│   ├── test_meta_ai_rl.py
│   ├── test_meta_ai_rl_longrun.py
│   ├── test_meta_ai_rl_real_data.py
│   ├── test_minidemo_smoke.py
│   ├── test_mt5_connection.py
│   ├── test_noctria.py
│   ├── test_noctria.py.bak
│   ├── test_noctria_master_ai.py
│   ├── test_noctus_gate_block.py
│   ├── test_path_config.py
│   ├── test_policy_guard.py
│   ├── test_quality_gate_alerts.py
│   ├── test_trace_and_integration.py
│   ├── test_trace_decision_e2e.py
│   └── unit_tests.py
├── token
├── tools
│   ├── advanced_import_map.py
│   ├── collect_autogen_devcycle_pg.py
│   ├── find_non_pathconfig_paths.py
│   ├── fix_quarantine.py
│   ├── generate_full_import_map.py
│   ├── generate_import_map.py
│   ├── init_optuna.sql
│   └── scan_repo_to_mermaid.py
├── venv_codex
│   ├── bin
│   │   ├── Activate.ps1
│   │   ├── activate
│   │   ├── activate.csh
│   │   ├── activate.fish
│   │   ├── bandit
│   │   ├── bandit-baseline
│   │   ├── bandit-config-generator
│   │   ├── black
│   │   ├── blackd
│   │   ├── cairosvg
│   │   ├── distro
│   │   ├── dmypy
│   │   ├── dotenv
│   │   ├── f2py
│   │   ├── httpx
│   │   ├── import_pb_to_tensorboard
│   │   ├── jsondiff
│   │   ├── jsonpatch
│   │   ├── jsonpointer
│   │   ├── markdown-it
│   │   ├── markdown_py
│   │   ├── mypy
│   │   ├── mypyc
│   │   ├── normalizer
│   │   ├── numpy-config
│   │   ├── openai
│   │   ├── pip
│   │   ├── pip3
│   │   ├── pip3.12
│   │   ├── py.test
│   │   ├── pydocstyle
│   │   ├── pygmentize
│   │   ├── pytest
│   │   ├── python -> python3
│   │   ├── python3 -> /usr/bin/python3
│   │   ├── python3.12 -> python3
│   │   ├── ruff
│   │   ├── saved_model_cli
│   │   ├── stubgen
│   │   ├── stubtest
│   │   ├── tensorboard
│   │   ├── tf_upgrade_v2
│   │   ├── tflite_convert
│   │   ├── toco
│   │   ├── tqdm
│   │   ├── wheel
│   │   └── yamllint
│   ├── include
│   │   ├── python3.12
│   │   └── site
│   ├── lib
│   │   └── python3.12
│   ├── lib64 -> lib
│   ├── pyvenv.cfg
│   └── share
│       └── man
├── venv_gui
│   ├── bin
│   │   ├── Activate.ps1
│   │   ├── activate
│   │   ├── activate.csh
│   │   ├── activate.fish
│   │   ├── alembic
│   │   ├── distro
│   │   ├── dotenv
│   │   ├── f2py
│   │   ├── fastapi
│   │   ├── flask
│   │   ├── gunicorn
│   │   ├── httpx
│   │   ├── huggingface-cli
│   │   ├── import_pb_to_tensorboard
│   │   ├── isympy
│   │   ├── mako-render
│   │   ├── markdown-it
│   │   ├── markdown_py
│   │   ├── normalizer
│   │   ├── numpy-config
│   │   ├── openai
│   │   ├── pip
│   │   ├── pip3
│   │   ├── pip3.12
│   │   ├── proton
│   │   ├── proton-viewer
│   │   ├── pwiz.py
│   │   ├── py.test
│   │   ├── pygmentize
│   │   ├── pytest
│   │   ├── python -> python3
│   │   ├── python3 -> /usr/bin/python3
│   │   ├── python3.12 -> python3
│   │   ├── ruff
│   │   ├── sample
│   │   ├── saved_model_cli
│   │   ├── tensorboard
│   │   ├── tf_upgrade_v2
│   │   ├── tflite_convert
│   │   ├── tiny-agents
│   │   ├── toco
│   │   ├── torchfrtrace
│   │   ├── torchrun
│   │   ├── tqdm
│   │   ├── transformers
│   │   ├── transformers-cli
│   │   ├── uvicorn
│   │   ├── watchfiles
│   │   ├── websockets
│   │   └── wheel
│   ├── include
│   │   ├── python3.12
│   │   └── site
│   ├── lib
│   │   └── python3.12
│   ├── lib64 -> lib
│   ├── pyvenv.cfg
│   └── share
│       └── man
├── venv_noctria
│   ├── bin
│   │   ├── Activate.ps1
│   │   ├── activate
│   │   ├── activate.csh
│   │   ├── activate.fish
│   │   ├── dotenv
│   │   ├── f2py
│   │   ├── fastapi
│   │   ├── flask
│   │   ├── import_pb_to_tensorboard
│   │   ├── isympy
│   │   ├── markdown-it
│   │   ├── markdown_py
│   │   ├── normalizer
│   │   ├── pip
│   │   ├── pip3
│   │   ├── pip3.12
│   │   ├── proton
│   │   ├── proton-viewer
│   │   ├── pwiz.py
│   │   ├── py.test
│   │   ├── pygmentize
│   │   ├── pytest
│   │   ├── python -> python3
│   │   ├── python3 -> /usr/bin/python3
│   │   ├── python3.12 -> python3
│   │   ├── sample
│   │   ├── saved_model_cli
│   │   ├── tensorboard
│   │   ├── tf_upgrade_v2
│   │   ├── tflite_convert
│   │   ├── toco
│   │   ├── toco_from_protos
│   │   ├── torchfrtrace
│   │   ├── torchrun
│   │   ├── uvicorn
│   │   ├── watchfiles
│   │   ├── websockets
│   │   └── wheel
│   ├── include
│   │   └── python3.12
│   ├── lib
│   │   └── python3.12
│   ├── lib64 -> lib
│   ├── pyvenv.cfg
│   └── share
│       └── man
├── venv_veritas
│   ├── bin
│   │   ├── Activate.ps1
│   │   ├── activate
│   │   ├── activate.csh
│   │   ├── activate.fish
│   │   ├── dotenv
│   │   ├── f2py
│   │   ├── fonttools
│   │   ├── pip
│   │   ├── pip3
│   │   ├── pip3.12
│   │   ├── pyftmerge
│   │   ├── pyftsubset
│   │   ├── python -> python3
│   │   ├── python3 -> /usr/bin/python3
│   │   ├── python3.12 -> python3
│   │   └── ttx
│   ├── include
│   │   └── python3.12
│   ├── lib
│   │   └── python3.12
│   ├── lib64 -> lib
│   ├── pyvenv.cfg
│   └── share
│       └── man
├── workflows
│   ├── build_and_deploy.yml
│   └── update_docs.yml
├── カスタムAirflowイメージを作る.md
└── パス参照MAP

330 directories, 1019 files
```
