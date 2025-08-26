flowchart TD

%% ====== styles (GitHub-safe) ======
classDef plan fill:#262e44,stroke:#47617a,color:#d8e0f7;
classDef ai fill:#2f3136,stroke:#a97e2c,color:#ffe476;
classDef do fill:#3d2d2d,stroke:#cc9999,color:#ffcccc;
classDef todo fill:#323232,stroke:#ff9f43,color:#ffd8a8;
classDef partial fill:#2e2e2e,stroke:#ffcc66,color:#fff2cc;
classDef obs fill:#1e2a36,stroke:#5dade2,color:#d6eaf8;
classDef demo fill:#202020,stroke:#8a8a8a,color:#eaeaea;

%% ====== PLAN layer ======
subgraph PLAN ["PLAN layer (src/plan_data)"]
  COLLECT["collector.py<br/>market data collection"]:::plan
  FEATURES["features.py<br/>feature engineering"]:::plan
  FEATDF["FeatureBundle output<br/>(df + context)<br/>v1.0"]:::plan
  ANALYZER["analyzer.py<br/>factor extraction"]:::plan
  STATS["statistics.py<br/>KPI aggregation"]:::plan
  ADAPTER["strategy_adapter.py<br/>propose_with_logging<br/>logs obs_infer_calls"]:::plan
  ADP2DEC["adapter_to_decision.py<br/>run_strategy_and_decide<br/>(NEW)"]:::plan
end

%% ====== AI underlings ======
subgraph AI_UNDERLINGS ["AI underlings (src/strategies)"]
  AURUS["Aurus<br/>propose()"]:::ai
  LEVIA["Levia<br/>propose()"]:::ai
  PROM["Prometheus<br/>predict_future()"]:::ai
  VERITAS["Veritas<br/>propose()"]:::ai
  HERMES["Hermes<br/>LLM explain (non-exec)"]:::ai
end

%% ====== Decision & Risk ======
DECISION["DecisionEngine (min)<br/>integrate & log<br/>(IMPLEMENTED)"]:::plan
NOCTUSGATE["Noctus Gate<br/>mandatory risk & lot filter<br/>(TODO)"]:::todo
QUALITY["DataQualityGate<br/>missing_ratio / data_lag → SCALE/FLAT<br/>(PARTIAL)"]:::partial
PROFILES["profiles.yaml<br/>weights & rollout 7->30->100%<br/>(PARTIAL)"]:::partial

%% ====== Contracts ======
CONTRACTS["Contracts<br/>FeatureBundle & StrategyProposal v1.0（実装）<br/>OrderRequest（Do契約に準拠）"]:::partial
TRACEID["Correlation ID trace_id<br/>PLAN/AI/Decision/Exec implemented"]:::plan

%% ====== Do layer (handoff) ======
subgraph DO_LAYER ["Do layer (handoff)"]
  ORDER["order_execution.py<br/>execution API (dummy ok)"]:::do
end

%% ====== Demo & tests ======
subgraph DEMO ["Demo and tests"]
  DECISION_MINI["e2e/decision_minidemo.py<br/>E2E (IMPLEMENTED)"]:::demo
  TEST_E2E["tests/test_trace_decision_e2e.py<br/>integration (IMPLEMENTED)"]:::demo
end

%% ====== Observability taps ======
subgraph OBS ["Observability taps (tables)"]
  OBS_PLAN["obs_plan_runs<br/>collector/features/statistics/analyzer<br/>trace_id present"]:::obs
  OBS_INFER["obs_infer_calls<br/>AI propose/predict latency<br/>trace_id present"]:::obs
  OBS_DEC["obs_decisions<br/>decision metrics & reasons<br/>trace_id present (NEW)"]:::obs
  OBS_EXEC["obs_exec_events<br/>send status / provider response<br/>trace_id present (NEW)"]:::obs
  OBS_ALT["obs_alerts<br/>quality or risk alerts<br/>(PARTIAL)"]:::partial
end

%% ====== PLAN flow ======
COLLECT --> FEATURES --> STATS
FEATURES --> FEATDF
FEATDF --> ANALYZER
ANALYZER --> HERMES
FEATDF --> ADAPTER
ADAPTER --> AURUS
ADAPTER --> LEVIA
ADAPTER --> PROM
ADAPTER --> VERITAS
ADAPTER --> ADP2DEC --> DECISION

%% ====== Contracts wiring ======
FEATDF -. "uses" .-> CONTRACTS
ADAPTER -. "uses" .-> CONTRACTS
AURUS -. "returns" .-> CONTRACTS
LEVIA -. "returns" .-> CONTRACTS
PROM  -. "returns" .-> CONTRACTS
VERITAS -. "returns" .-> CONTRACTS

%% ====== Decision integration path ======
FEATDF --> QUALITY
QUALITY --> DECISION
AURUS --> DECISION
LEVIA --> DECISION
PROM  --> DECISION
VERITAS --> DECISION
PROFILES -. "config" .-> DECISION
DECISION --> NOCTUSGATE
NOCTUSGATE --> ORDER

%% ====== Demo edges ======
DECISION_MINI --> FEATDF
DECISION_MINI --> DECISION
DECISION_MINI --> ORDER
TEST_E2E -. "psql counts by trace_id" .-> OBS_PLAN
TEST_E2E -.-> OBS_INFER
TEST_E2E -.-> OBS_DEC
TEST_E2E -.-> OBS_EXEC

%% ====== Observability wiring ======
COLLECT  -->|log| OBS_PLAN
FEATURES -->|log| OBS_PLAN
STATS    -->|log| OBS_PLAN
ANALYZER -->|log| OBS_PLAN
AURUS    -->|log| OBS_INFER
LEVIA    -->|log| OBS_INFER
PROM     -->|log| OBS_INFER
VERITAS  -->|log| OBS_INFER
DECISION -->|log| OBS_DEC
ORDER    -->|log| OBS_EXEC
NOCTUSGATE -->|alert| OBS_ALT

%% ====== trace_id notes ======
FEATDF -. "trace_id (PLAN & AI implemented)" .-> AURUS
FEATDF -. "trace_id (PLAN & AI implemented)" .-> LEVIA
FEATDF -. "trace_id (PLAN & AI implemented)" .-> PROM
FEATDF -. "trace_id (PLAN & AI implemented)" .-> VERITAS
DECISION -. "trace_id (P->D->Exec implemented)" .-> ORDER

%% ====== class bindings ======
class COLLECT,FEATURES,FEATDF,ANALYZER,STATS,ADAPTER,ADP2DEC plan;
class AURUS,LEVIA,PROM,VERITAS,HERMES ai;
class ORDER do;
class DECISION plan;
class NOCTUSGATE todo;
class QUALITY,PROFILES,CONTRACTS,OBS_ALT partial;
class TRACEID plan;
class OBS_PLAN,OBS_INFER,OBS_DEC,OBS_EXEC obs;
class DECISION_MINI,TEST_E2E demo;
