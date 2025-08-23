# 🏰 Noctria PDCA Spec — File/Function Map v1.0
**Status:** Source of Truth for design (no code)  
**Scope:** PDCA layers, Contracts, Observability, Orchestrator/GUI, Governance

> 本書は「どの層で・どのファイルが・何を入出力し・誰が責任を持つか」を固定する**唯一の設計索引**。ここに載っていないファイルはPDCAの外とみなす。変更は必ず本書→関連設計へ反映してから実装に進む。

---

## 0. 共有規約（必読）
- **相関ID:** `trace_id` を全イベントで必須（HTTPでは `X-Trace-Id`）。  
- **契約の後方互換:** SemVer、破壊変更は v2.0+。  
- **冪等性キー:** `OrderRequest.idempotency_key`（v1.1）を「生成→送信→記録」まで貫通。  
- **時刻:** すべて **UTC ISO-8601**、表示はGUIでTZ変換。  
- **観測SoT:** DB（`obs_*` テーブル/ビュー/MV）。GUIはDB出力を表示するだけ。

---

## 1. PLAN 層（`src/plan_data/`）
| File | Role / What it does | Inputs | Outputs | Contracts | Status |
|---|---|---|---|---|---|
| `collector.py` | 市場データ収集 | 外部API/CSV | 原始データ（mem/df） | – | Implemented |
| `features.py` | 特徴量生成 | 原始データ | **FeatureBundle** | FeatureBundle v1.0 | Implemented |
| `statistics.py` | KPI下地集計 | FeatureBundle | 集計KPI/派生指標 | – | Implemented |
| `analyzer.py` | 要因抽出/説明変数 | FeatureBundle | 要因スコア | – | Implemented |
| `strategy_adapter.py` | AI呼び出し＋ログ | FeatureBundle | **StrategyProposal*** | StrategyProposal v1.0 | Implemented |
| `trace.py` | `trace_id` 生成・伝搬 | – | trace_id | – | Implemented |
| `observability.py` | `obs_*` 書き込みヘルパ | 事件情報 | DB行 | – | Implemented |
| `contracts.py` | 契約整合チェック | Bundle/Proposal | 検証結果 | 全契約 | Implemented |

**PLAN→AI 呼出:** Proposalは **複数**（Aurus/Levia/Prometheus/Veritas）。  
**決定経路:** FeatureBundle → (QualityGate予定) → DecisionEngine（D層）。

---

## 2. DO 層（`src/execution/`）
| File | Role / What it does | Inputs | Outputs | Contracts | Status |
|---|---|---|---|---|---|
| `order_execution.py` | 送信I/F本体（place/cancel/replaceの起点） | **OrderRequest** | **exec_result**（Do→Check） | OrderRequest v1.1 | Ready |
| `optimized_order_execution.py` | スリッページ考慮/分割等（将来） | OrderRequest | 複数子注文 | OrderRequest v1.x | Planned |
| `risk_gate.py` | **Noctus Gate**（数量/時間帯/銘柄ガード） | OrderRequest, risk_policy | 許可/縮小/拒否＋**risk_event** | OrderRequest v1.1 | Partial |
| `generate_order_json.py` | 監査用封筒生成（JSONスナップ） | 提案/決定情報 | OrderRequest（署名/キー含む） | OrderRequest v1.1 | Planned |
| `broker_adapter.py` | 外部ブローカ抽象化 | OrderRequest | 送信レスポンス | – | Planned |
| `risk_policy.py` | ポリシー定義/読込 | yml | ルール | – | Ready |

**冪等:** OrderRequest は **idempotency_key（必須推奨）** を保持。`exec_result` にも同キーを含めて戻す。  
**観測:** `obs_exec_events`（送信・約定・失敗）、`obs_alerts`（Gate/異常）。

---

## 3. CHECK 層（`src/check/`）
| File | Role / What it does | Inputs | Outputs | Contracts | Status |
|---|---|---|---|---|---|
| `evaluation.py` | 実績KPI集計 | **exec_result** | `kpi_summary.json` | – | Ready |
| `challenge_monitor.py` | 連敗/最大DD/逸脱監視 | exec_result, risk_event | アラート/抑制指標 | – | Ready |
| `metrics_aggregator.py` | 期間/AI/シンボル別集計 | KPI/ログ | ランキング/比較 | – | Planned |
| `prometheus_exporter.py` | /metrics エクスポート | KPI | Prometheus出力 | – | Planned |

**下流:** `kpi_summary.json` は ACT/GUI の主要入力。

---

## 4. ACT 層（`src/act/` & `noctria_gui/routes/`）
| File | Role / What it does | Inputs | Outputs | Status |
|---|---|---|---|---|
| `pdca_recheck.py` | 再評価/パラメタ探索/A-B | kpi_summary, eval_config | 再評価レポート | Ready |
| `pdca_push.py` | 採用/タグ付け/昇格 | 再評価結果 | release（タグ/記録） | Planned |
| `pdca_summary.py` | 期間/タグ要約 | KPI | サマリJSON/GUI | Ready |
| `feedback_adapter.py` | PLANへの提案返し | KPI/再評価 | plan_update.json | Planned |

**昇格ガバナンス:** Two-Person + King（別紙ポリシー、将来 formalize）。

---

## 5. Decision（`src/decision/`）
| File | Role / What it does | Inputs | Outputs | Contracts | Status |
|---|---|---|---|---|---|
| `decision_engine.py` | **RoyalDecisionEngine**（最終裁定） | FeatureBundle, StrategyProposal* | **DecisionRecord**, **OrderRequest?** | DecisionRecord v1.0, OrderRequest v1.1 | Ready（min） |
| `decision_registry.py` | 戦略登録/重み | profiles.yaml | 重み/有効フラグ | – | Ready |
| `decision_hooks.py` | 前後処理hook | 各レコード | 監査補助 | – | New |

**方針:** 発注が必要なときのみ OrderRequest を生成する。全裁定は DecisionRecord に記録。

---

## 6. 契約（`docs/architecture/contracts/`）
| Contract Doc | Purpose | Producer → Consumer | Version | Notes |
|---|---|---|---|---|
| `FeatureBundle.md` | PLAN→AI の特徴量束 | PLAN → AI群/Decision | v1.0 | df/context/schema |
| `StrategyProposal.md` | AI提案（方向/自信/根拠） | AI群 → Decision | v1.0 | 複数可 |
| `DecisionRecord.md` | 最終裁定（根拠/ロット） | Decision → 監査/GUI | v1.0 | SoT for decisions |
| `OrderRequest.md` | 発注要求（冪等キー含） | Decision → DO | **v1.1** | `idempotency_key` 必須推奨 |

**互換指針:** v1.x は後方互換。破壊変更は v2.0+ で移行計画を同梱。

---

## 7. 可観測性（`docs/observability/*`, `noctria_gui/routes/observability.py`）
| Object | Type | Purpose |
|---|---|---|
| `obs_plan_runs` | table | PLANイベント |
| `obs_infer_calls` | table | AI推論 |
| `obs_decisions` | table | 裁定 |
| `obs_exec_events` | table | 実行/約定 |
| `obs_alerts` | table | リスク/品質 |
| `obs_trace_timeline` | view | 時系列（GUI `/pdca/timeline`） |
| `obs_trace_latency` | view | レイテンシ分解 |
| `obs_latency_daily` | mview | p50/p90/p95/max（日次） |

**GUIルート:**  
- `GET /pdca/timeline`（trace列挙/詳細）  
- `GET /pdca/latency/daily`（30日）  
- `POST /pdca/observability/refresh`（DDL/MV更新）

---

## 8. オーケストレータ/GUI
| Area | Path | Role |
|---|---|---|
| Airflow | `airflow_docker/dags/*.py` | PDCA定期実行（idempotent） |
| GUI | `noctria_gui/routes/*` | 可視化/制御（最小） |
| Templates | `noctria_gui/templates/*` | HTMLテンプレ |

---

## 9. 設計図（Mermaid, `docs/architecture/diagrams/*.mmd`）
- `plan_layer.mmd` — PLAN詳細  
- `do_layer.mmd` — DO詳細（idempotency/Gate/Outboxを注記）  
- `check_layer.mmd` — CHECK詳細  
- `act_layer.mmd` — ACT詳細  
- `integration_overview.mmd` — 全体連携  
- `system_complete.mmd` / `all_overview.mmd` / `gui_tools.mmd` — 補助全景

---

## 10. 変更管理と責任（RACI）
- **R（実装）:** 層オーナー（PLAN/DO/CHECK/ACT/Decision）  
- **A（承認）:** King Noctria（契約/ガード/昇格）  
- **C（相談）:** GUI/Observability/Operations  
- **I（周知）:** 全メンバー（PR/Changelog）

**フロー:** 1) 本書を更新（PR）→ 2) 契約/図/設計を連鎖更新 → 3) 受理後に実装PRを開始。

---

## 11. DOD（Definition of Done）
- 対応層の**設計差分が本書に反映**されている  
- 契約の**互換性方針が明記**されている  
- 観測（`obs_*`）に**最小ログが流れる設計**である  
- GUI/運用の**参照先が一意**である

---

## 12. 未決事項（Backlog）
- DO FSM（place→ack→partial_fill→filled/expired/rejected）  
- Broker Capabilities/RateLimit/Backoff/Recon の細目  
- ACTの昇格基準ポリシー formalize（Two-Person + King）

