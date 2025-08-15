以下は、明日以降も再生成できるように詳細な備忘録として記録するための **Extended README** の例です。  
この README では、各フォルダ・ファイルの役割、実装した機能一覧、そして Noctria Kingdom の物語的な側面（王と4人の臣下の特性や役割）についても説明しています。  

---

# Noctria Kingdom - 自律型FXトレーディングシステム

**概要:**  
Noctria Kingdom は、AI 主導の自律型FXトレーディングシステムです。  
市場の変動に応じて自己進化し、戦略、リスク管理、データ解析、さらにMT5用 Expert Advisor (EA) を統合したオールインワンのシステムとなっています。  
システム全体は、技術面の最先端（強化学習、量子市場予測、NSGA-II による多目的最適化、Explainable AI など）と、戦略的な物語性（王と臣下の役割分担）という2つの側面で設計されています。

---

## フォルダ構成と各ファイルの役割

```
Noctria_Kingdom/
├── core/                # システム統括モジュール（王：Noctria が全体を統括）
│   ├── Noctria.py       # 統括AI。すべての意思決定と調整を行い、王として全体を統括。
│   ├── config.yaml      # システム設定情報。各モジュールのパラメータや接続情報が記載。
│   ├── logger.py        # ログ管理。システム全体のログ出力を担当。
│   ├── utils.py         # 各種ユーティリティ関数。日時フォーマット、JSON保存/読込などを提供。
│   ├── init.py          # 初期化処理。必要なディレクトリの作成やシステム初期化を実施。
│
├── strategies/          # 戦略モジュール（臣下）
│   ├── Aurus_Singularis.py    # 臣下A: 戦略設計AI。進化型戦略として市場トレンドを解析し柔軟に戦術を策定。
│   ├── Levia_Tempest.py       # 臣下B: スキャルピングAI。高速で小さな価格変動を捉える短期取引戦略を実行。
│   ├── Noctus_Sentinella.py   # 臣下C: リスク管理AI。市場リスクの評価と異常検知を担当。資本保護の役割。
│   ├── Prometheus_Oracle.py   # 臣下D: 未来予測AI。中長期的な市場動向予測を行い、未来への指針を提供。
│   ├── quantum_prediction.py  # 量子市場予測AI。量子コンピューティングによる新たな予測手法を統合。
│   ├── portfolio_optimizer.py # ポートフォリオ管理。リスクとリターンのバランスを最適化する戦略を実装。
│   ├── market_analysis.py     # 市場データの分析。詳細な統計分析と市場の局面検出を実施。
│   ├── strategy_runner.py     # 戦略適用。時系列データをもとに各戦略モジュールの呼び出し管理。
│   ├── auto_adjustment.py     # 自動戦略調整。環境変化に応じた戦略パラメータの動的調整を行う。
│   ├── reinforcement_learning.py  # 強化学習を用いた戦略最適化。過去のデータから学習を実施。
│   └── adaptive_trading.py    # 自己進化トレード。戦略自体が進化し、最適なトレード方法を生成。
│
├── data/                 # データ処理モジュール
│   ├── raw_data_loader.py          # 市場データ取得。生データの読み込みと初期前処理を行う。
│   ├── processed_data_handler.py   # 特徴量抽出・前処理。正規化や統計値算出を実施。
│   ├── sentiment_analysis.py       # 市場心理解析。ニュースやSNSなどからセンチメントスコアを抽出。
│   ├── fundamental_analysis.py     # ファンダメンタル分析。企業財務指標から市場健全性を評価。
│   ├── multi_objective_optimizer.py  # NSGA-II による多目的最適化。複数の目的関数の調整を図る。
│   ├── anomaly_detection.py        # 異常検知モジュール。市場データから異常値を検出してリスク評価。
│   ├── ensemble_learning.py        # アンサンブル学習。複数モデルの統合により予測精度を向上。
│   ├── market_regime_detector.py   # 市場状態分類。ブル/ベア/ニュートラルの市場環境を判定。
│   ├── explainable_ai.py           # 透明性向上AI。予測の理由をSHAP等で説明する機能を提供。
│   ├── high_frequency_trading.py   # 超高速取引システム。低レイテンシで迅速にトレード実行。
│   ├── institutional_order_monitor.py  # 大口注文監視。機関投資家の注文流れを検知。
│   ├── quantum_computing_integration.py  # 量子統合予測AI。量子コンピューティング関連の実験的予測。
│
├── execution/            # トレード実行モジュール
│   ├── order_execution.py   # 注文執行処理。トレードのエントリー／エグジットを実施。
│   ├── risk_control.py      # リスク管理アルゴリズム。ストップロス・資金管理を統括。
│   ├── trade_monitor.py     # トレード監視システム。リアルタイムで注文状況をモニタリング。
│   ├── execution_manager.py # 実行フロー管理。注文のタイミングと流れを調整。
│
├── experts/              # MT5用 EA (Expert Advisor) モジュール
│   ├── core_EA.mq5              # 統括EA。Noctria Kingdom の全体戦略・執行制御を担当（王の意思を反映）。
│   ├── aurus_singularis.mq5     # 戦略設計EA。臣下Aの戦術を実装し、トレードシグナルを生成。
│   ├── levia_tempest.mq5        # スキャルピングEA。臣下Bの短期取引シグナルを解析し実行。
│   ├── noctus_sentinella.mq5    # リスク管理EA。臣下Cのリスク評価ロジックを組み込み、資金管理を強化。
│   ├── prometheus_oracle.mq5    # 未来予測EA。臣下Dの未来予測とシグナル生成を担当。
│   ├── quantum_prediction.mq5   # 量子市場予測EA。量子予測技術を実装し、新たなアプローチを試みる。
│   ├── auto_evolution.mq5       # EA 自己進化モジュール。システムの自動最適化による戦略進化を実現。
│
├── tests/                # テスト・検証モジュール
│   ├── unit_tests.py       # ユニットテスト。各モジュール・関数の個別テストを実施。
│   ├── backtesting.py      # FXバックテスト。過去データを用いて戦略の有効性を検証。
│   ├── stress_tests.py     # システム負荷検証。高頻度データ下でのシステム動作をチェック。
│
└── docs/                 # ドキュメント
    ├── architecture.md        # システム設計。全体のアーキテクチャ及び各モジュールの連携を説明。
    ├── strategy_manual.md     # 戦略適用ガイド。各戦略の使用方法・パラメータ調整手順を記載。
    ├── data_handling.md       # データ処理の説明。データ取得から前処理、解析までの流れを記録。
    ├── optimization_notes.md  # 最適化メモ。パフォーマンス向上やエラー対応の記録。
    ├── api_reference.md       # API 仕様書。システム内外部のインターフェースおよびデータ形式を記述。
```

---

## プロジェクト概要と実装機能一覧

### 1. **コアモジュール（core/）**
- **Noctria.py**  
  ・システム全体の統括。すべてのモジュール間の連携と意思決定を担当。  
- **config.yaml**  
  ・各モジュールのパラメータ（取引サイズ、リスク閾値、API設定など）を集中管理。  
- **logger.py / utils.py**  
  ・運用ログの出力、デバッグ、共通機能（日時フォーマット、JSON操作）の提供。  
- **init.py**  
  ・起動時の環境構築（必要なディレクトリの作成、初期設定の読み込み）。

### 2. **戦略モジュール（strategies/）**
- **Aurus_Singularis.py**  
  ・市場トレンドの詳細解析や進化型戦略の策定。  
  ・臣下A「戦略設計AI」として、柔軟なシグナル生成を実施。  
- **Levia_Tempest.py**  
  ・高速スキャルピング戦略を担当。  
  ・非常に短期な時間枠での価格変動を捉えてトレードを実行。  
- **Noctus_Sentinella.py**  
  ・リスク管理・異常検知を行い、システム全体の安定性を保つ。  
- **Prometheus_Oracle.py**  
  ・未来市場予測を行い、中長期的なシグナルを生成。  
- **quantum_prediction.py**  
  ・量子コンピューティングの概念を取り入れた、市場予測モデルを実装。  
- **portfolio_optimizer.py**  
  ・ポートフォリオ内の資産配分を最適化し、リスクとリターンのバランスを保つ。  
- **market_analysis.py**  
  ・詳細な統計分析により市場局面（ブル／ベア／ニュートラル）を判定。  
- **strategy_runner.py**  
  ・各戦略モジュールの統合運用と、適切なタイミングでの起動を管理。  
- **auto_adjustment.py**  
  ・市場環境に応じた戦略パラメータの自動調整機能。  
- **reinforcement_learning.py**  
  ・強化学習により、過去のデータからより良い戦略を学習・最適化。  
- **adaptive_trading.py**  
  ・システム自体が進化する仕組みを実装。リアルタイムにトレード戦略を改善。

### 3. **データ処理モジュール（data/）**
- **raw_data_loader.py**  
  ・市場からの生データ取得、CSVやAPI経由のデータ読込。  
- **processed_data_handler.py**  
  ・データ正規化、欠損値処理、特徴量抽出などの前処理を実施。  
- **sentiment_analysis.py**  
  ・ニュースやSNSなどから市場心理を抽出し、シグナルとして利用。  
- **fundamental_analysis.py**  
  ・企業の財務指標やセクターの動向を評価し、ファンダメンタル面からの分析を提供。  
- **multi_objective_optimizer.py**  
  ・NSGA-II による多目的最適化を実現し、複数の戦略目的を同時に最適化。  
- **anomaly_detection.py**  
  ・市場データ中の異常値を自動検出し、リスクフィルタとして活用。  
- **ensemble_learning.py**  
  ・複数のモデルによる予測を統合し、精度と頑健性を向上。  
- **market_regime_detector.py**  
  ・市場のトレンドや局面をリアルタイムで分類。  
- **explainable_ai.py**  
  ・SHAP などを用い、AIの予測理由を可視化。  
- **high_frequency_trading.py**  
  ・超高速取引の実現に向けた、低レイテンシ注文ロジックを実装。  
- **institutional_order_monitor.py**  
  ・大口注文や機関投資家の動向を監視し、市場の流動性を評価。  
- **quantum_computing_integration.py**  
  ・実験的に量子理論を応用した市場予測モデルを統合。

### 4. **トレード実行モジュール（execution/）**
- **order_execution.py**  
  ・実際のトレード注文の執行ロジック。  
- **risk_control.py**  
  ・資金管理、ストップロス設定など、リスクを制御するアルゴリズムを実装。  
- **trade_monitor.py**  
  ・オープンポジションと注文の状態をモニタリング。  
- **execution_manager.py**  
  ・注文のタイミング、優先順位、フロー管理など、実行全体を調整。

### 5. **MT5用 EA モジュール（experts/）**
EA 部分は、各戦略やリスク管理のロジックをリアルタイムでMT5上に実装し、自動売買を実現。  
- **core_EA.mq5**  
  ・統括EAとして、全体の意思決定を反映。Noctria（王）の指令に従い、必要なEA（臣下）の各ロジックを統合。
- **aurus_singularis.mq5**  
  ・王の側近（臣下A）として、市場トレンドや戦略シグナルを生成。
- **levia_tempest.mq5**  
  ・高速スキャルピング戦略を実装。短期的な価格変動に迅速に反応。
- **noctus_sentinella.mq5**  
  ・リスク管理のロジックを実装。市場危機時の防御機能として作動。
- **prometheus_oracle.mq5**  
  ・未来予測シグナルを計算し、長期トレンドに基づく判断を補助。
- **quantum_prediction.mq5**  
  ・量子市場予測機能を実験的に実装し、新たな手法でシグナルを生成。
- **auto_evolution.mq5**  
  ・自己進化モジュールとして、システム自体のパラメータを市場状況に合わせて動的に最適化。

### 6. **テスト・検証モジュール（tests/）**
- **unit_tests.py**  
  ・各モジュールの単体テストを実施し、機能の正確性を検証。
- **backtesting.py**  
  ・過去の市場データを用いて戦略のパフォーマンスをシミュレーション。  
- **stress_tests.py**  
  ・システムの負荷テストや高頻度データ時の安定性を検証。

### 7. **ドキュメント（docs/）**
- **architecture.md**  
  ・システムの全体設計、モジュール間の連携、データフローの詳細を説明。  
- **strategy_manual.md**  
  ・各戦略の使用方法、パラメータの調整方法、運用のベストプラクティスを記載。  
- **data_handling.md**  
  ・データ取得、前処理、解析の流れと使用する技術について記録。  
- **optimization_notes.md**  
  ・パフォーマンス改善、エラー修正、システム最適化に関するメモ。  
- **api_reference.md**  
  ・内部および外部向けのAPI仕様、データフォーマット、連携方法の詳細。

---

## キャラクター設定（プロジェクトの物語的側面）

Noctria Kingdom の世界では、システム全体が一国の体制に見立てられています。  
- **王 (Noctria)**  
  - コアモジュールとして、全体の統括管理や意思決定を行う。  
  - 各モジュールやEAからの情報を集約し、戦略的な指令を下す中心的存在。

- **4人の臣下（主要戦略アドバイザー）**  
  1. **臣下 A: Aurus_Singularis**  
     - 戦略設計AIとして市場トレンドの解析と戦術の策定を担当。  
     - 進化型戦略を提案し、システムの戦略的方向性を決める。
  2. **臣下 B: Levia_Tempest**  
     - 短期のスキャルピングおよび瞬間的な市場変動に対応。  
     - 高速取引と小刻みな利益獲得を実現し、流動性のある取引環境を構築。
  3. **臣下 C: Noctus_Sentinella**  
     - リスク管理と異常検知に特化。  
     - 市場の急変や異常な動きを素早く察知・対応することで資本保護に貢献。
  4. **臣下 D: Prometheus_Oracle**  
     - 未来予測AIとして、長期的な市場動向の分析を担当。  
     - 将来のトレンドを予測し、システム全体の戦略に先見性をもたらす。

この王と臣下の体制により、Noctria Kingdom は戦略的な柔軟性と安定性を兼ね備え、市場のあらゆる局面に対応する仕組みが実現されています。

---

## 開発経緯と今後の展望

**これまでの進捗:**  
- システム全体の構造設計、各モジュールのプロトタイプ実装。  
- 各戦略およびデータ解析モジュールの基礎コード確立。  
- MT5 用のEA（Expert Advisor）の初期ロジックを各ファイルに実装。  
- キャラクターとしての王（Noctria）と4人の臣下の役割を設計。

**今後の展望:**  
- 各モジュールの機能拡充とパラメータチューニング。  
- ストレステストやバックテストを通じた実運用シナリオの検証。  
- 自己進化・強化学習機能の実装で市場環境に合わせた動的最適化。  
- さらなる透明性向上やExplainable AIの実装による運用の信頼性向上。  
- チーム内でのフィードバックを集約し、継続的な改善と新機能の追加。

---

## 終わりに

この README は、Noctria Kingdom の全体像と各モジュールの役割、実装機能、さらには物語的な背景（王と臣下の設定）を詳細に記録しています。  
明日以降、ソースコードの再生成や機能追加の際に参照できるよう、必ず最新版を保存してください。  
また、プロジェクトの進捗や改善点、将来の実装計画はドキュメント（docs/）にもまとめているので、そちらも合わせて確認してください。

---

この備忘録がプロジェクトの全体像を把握する助けとなり、今後の開発の指針として活用されることを願っています。  

何か修正・追記があれば、この README を更新する形で運用を続けてください。  
Happy coding and trading in the Kingdom!  
  
---  

以上が **Noctria Kingdom の Extended README** です。  
この内容を保存すれば、いつでもシステム全体の構成や開発経緯、物語的背景を再現・再生成できます。
<!-- AUTODOC:BEGIN mode=git_log path_globs=docs/misc/*.md title="Misc 文書更新履歴（最近30）" limit=30 since=2025-08-01 -->
### Misc 文書更新履歴（最近30）

- **7111b30** 2025-08-15T19:38:34+09:00 — docs: AUTODOCブロック挿入および本文更新 (by Veritas Machina)
  - `docs/00_index/00-INDEX.md`
  - `docs/00_index/00-INDEX.md.bak`
  - `docs/README.md`
  - `docs/README.md.bak`
  - `docs/_partials/apis/Do-Layer-Contract/01_scope_principles.md`
  - `docs/_partials/apis/Do-Layer-Contract/02_flow_overview.md`
  - `docs/_partials/apis/Do-Layer-Contract/03_entities_schemas.md`
  - `docs/_partials/apis/Do-Layer-Contract/04_order_request.md`
  - `docs/_partials/apis/Do-Layer-Contract/05_exec_result.md`
  - `docs/_partials/apis/Do-Layer-Contract/06_audit_order.md`
  - `docs/_partials/apis/Do-Layer-Contract/07_financial_correctness.md`
  - `docs/_partials/apis/Do-Layer-Contract/08_idempotency_concurrency.md`
  - `docs/_partials/apis/Do-Layer-Contract/09_error_codes.md`
  - `docs/_partials/apis/Do-Layer-Contract/10_samples_min.md`
  - `docs/_partials/apis/Do-Layer-Contract/11_contract_tests.md`
  - `docs/_partials/apis/Do-Layer-Contract/12_changelog.md`
  - `docs/adrs/ADRs.md`
  - `docs/adrs/ADRs.md.bak`
  - `docs/apis/Do-Layer-Contract.md`
  - `docs/apis/Do-Layer-Contract.md.bak`
- **30ae379** 2025-08-15T18:55:06+09:00 — 📄 AutoDoc: update docs from index (by Veritas Machina)
  - `action`
  - `data/decisions/ledger.csv`
  - `data/models/prometheus/PPO/obs8/latest`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:18:10+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:18:10+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:19:41+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:19:41+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:22:19+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:22:19+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:33:11+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T14:33:11+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T15:44:05+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T15:44:05+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:20:12.935706+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:20:12.935706+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:21:36.023694+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:21:36.023694+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:27:02.701382+00:00/metadata.json`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T16:27:02.701382+00:00/model.zip`
  - `data/models/prometheus/PPO/obs8/manual__2025-08-11T17:21:59.539332+00:00/metadata.json`
<!-- AUTODOC:END -->
