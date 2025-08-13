# 🗂 ADRs — Architecture Decision Records (Index) / Noctria Kingdom

**Document Version:** 1.0  
**Status:** Adopted  
**Last Updated:** 2025-08-14 (JST)

> このファイルは **ADRs（Architecture Decision Records）** の「索引」と「運用ルール」「テンプレート」を提供します。  
> **注意:** 本ファイルは *Coding Standards* ではありません。コーディング規約は `../governance/Coding-Standards.md` を正とします。

---

## 1) 目的と適用範囲
- **目的:** 重要な技術/運用の意思決定を小さく、追跡可能に、将来の読み手にも再現できる形で記録する。  
- **対象:** アーキテクチャ、契約/API、可観測性、セキュリティ、データ管理、運用方式（Airflow/DAG）、ガードレール（Noctus）など。  
- **非対象:** 単純なバグ修正や明白なリファクタリング（ただし影響が広ければ ADR 化を検討）。

---

## 2) 形式とディレクトリ
- **場所:** `docs/adrs/`  
- **命名規則:** `ADR-YYYYMMDD-xxxx-snake-case-title.md`  
  - `YYYYMMDD` は決定日、`xxxx` は 4 桁の連番（同日内で昇順）。  
  - 例: `ADR-20250814-0001-json-schema-as-contract.md`
- **リンク:** ADR 同士は相互に相対パスでリンク（`Supersedes:` / `Superseded-by:` を明記）。  
- **言語:** 日本語を基本。必要に応じて短い英語併記可。

---

## 3) ステータス遷移（Lifecycle）
- `Proposed` → レビュー中（PR 上で議論）  
- `Accepted` → 合意し採用。実装/運用ルールに反映。  
- `Rejected` → 採用しない。理由を記録。  
- `Deprecated` → 将来の廃止予定。移行ガイド必須。  
- `Superseded` → 後続 ADR に置換。リンク必須。

---

## 4) いつ ADR を書くか（トリガ）
- **契約/API/スキーマ**の変更（特に Breaking / `/v2` 導入）  
- **可観測性**の基本方針（メトリクス SoT、保持、アラート基準）  
- **セキュリティ/アクセス**（Two-Person Gate、Secrets 運用）  
- **運用方式**（Airflow キュー分離、リトライ/冪等）、**データ保持**  
- **実装原則**（Idempotency-Key 必須、Correlation-ID 貫通、Outbox パターン等）

> 迷ったら **書く**。短くても記録することに価値があります。

---

## 5) テンプレート（コピーして使用）
```md
# ADR-YYYYMMDD-xxxx — {短い決定タイトル}

**Status:** Proposed | Accepted | Rejected | Deprecated | Superseded  
**Date:** YYYY-MM-DD  
**Owners:** {role or people}  
**Supersedes:** ./ADR-YYYYMMDD-xxxx-*.md (あれば)  
**Superseded-by:** ./ADR-YYYYMMDD-xxxx-*.md (あれば)

## Context
- 背景・問題・制約・代替案を簡潔に。関連 Issue/PR/ドキュメント（相対リンク）:
  - ../architecture/Architecture-Overview.md
  - ../observability/Observability.md
  - ../operations/Config-Registry.md
  - ../apis/Do-Layer-Contract.md など

## Decision
- 何を採用/却下するか、**短い要点**で確定文。
- 影響範囲（コード/運用/セキュリティ/スキーマ）も列挙。

## Consequences
- プラス/マイナス/トレードオフ。
- 運用変更（Runbooks 追記点）、監視・SLO への影響。

## Rollout / Migration
- 段階導入（7%→30%→100%）、移行ガイド、ロールバック手順。
- 互換性（SemVer / `/v1` 併存期限）、テスト/契約検証。

## References
- 参考リンク、前提となる ADR、外部標準/仕様など。
```

---

## 6) 運用ルール（Docs-as-Code）
- **PR 同梱:** ADR は **関連コード/設定/Runbooks の変更と同一 PR** で提出。  
- **Two-Person Gate:** `risk_policy / flags / API / Do-Contract / Schemas` の重大変更は **二人承認 + King**。  
- **SemVer:** 契約/スキーマは後方互換を基本。Breaking は `/v2` を併存、移行ガイド必須（`Release-Notes.md` に明記）。  
- **参照の一貫性:** ADR で決めた内容は、`Architecture-Overview.md` / `Observability.md` / `Config-Registry.md` 等へ即反映。  
- **可観測性:** 決定ごとに必要なメトリクス/アラート更新を伴う場合は `deploy/alerts/*` の差分を含める。

---

## 7) レビュー観点チェックリスト
- [ ] **問題設定が明確**（誰が何に困っているか / 制約は何か）  
- [ ] **選択肢の比較**（少なくとも 2–3 案の検討跡）  
- [ ] **決定/非決定の境界が明確**（スコープ外は明記）  
- [ ] **運用/監視/セキュリティへの影響**が整理されている  
- [ ] **ロールアウト/ロールバック手順**が現実的  
- [ ] **関連文書/契約の更新**が同 PR に含まれる  
- [ ] **Two-Person Gate** 対象なら承認者が揃っている

---

## 8) 直近の重要トピック（ADR 候補 / 既決の明文化）
> まだ個別 ADR がないものは **候補**として列挙。順次 ADR 化します。

- **ADR-20250814-0001 — JSON Schema を公式契約とし SemVer 運用**（/api/v1、Breaking は /v2 併存）【候補】  
- **ADR-20250814-0002 — Idempotency-Key の書き込み系必須化（24h 冪等）**【候補】  
- **ADR-20250814-0003 — Correlation-ID（trace_id）の P→D→Exec 貫通**（`X-Trace-Id` / DB obs_*）【候補】  
- **ADR-20250814-0004 — Noctus Gate を Do 層の強制境界として適用**（バイパス禁止）【候補】  
- **ADR-20250814-0005 — Observability SoT（obs_* テーブル + ロールアップ方針）**【候補】  
- **ADR-20250814-0006 — 段階導入曲線 7%→30%→100% を標準化**（Safemode 併用）【候補】  
- **ADR-20250814-0007 — DO 層の Outbox + Idempotency-Key で少なくとも「once」保証**【候補】  
- **ADR-20250814-0008 — 内部時刻は UTC 固定 / 表示は GUI で TZ 補正**【候補】  
- **ADR-20250814-0009 — Airflow キュー分離（critical_do / models）と SLO**【候補】

> 上記は `Architecture-Overview.md` / `Observability.md` / `Runbooks.md` 等に既に記述があり、**ADR としての単体記録**を追加予定です。

---

## 9) 既存ドキュメントとの関係（Cross-Refs）
- アーキテクチャ: `../architecture/Architecture-Overview.md`, `../architecture/Plan-Layer.md`  
- 運用: `../operations/Runbooks.md`, `../operations/Airflow-DAGs.md`, `../operations/Config-Registry.md`  
- 契約/API: `../apis/API.md`, `../apis/Do-Layer-Contract.md`  
- 可観測性: `../observability/Observability.md`  
- セキュリティ: `../security/Security-And-Access.md`  
- QA: `../qa/Testing-And-QA.md`  
- 計画: `../roadmap/Roadmap-OKRs.md`, `../roadmap/Release-Notes.md`

---

## 10) よくある質問（FAQ）
- **Q:** Issue/PR の議論と何が違う？  
  **A:** ADR は**決定の最終形**と**理由**を将来に残す永久記録。議論ログは散逸しがち。  
- **Q:** 小さな変更でも必要？  
  **A:** 影響が広い/戻しにくい/契約や運用方針に触れるなら ADR を推奨。  
- **Q:** 既存の暗黙の方針は？  
  **A:** 今後の変更時に**確定情報として ADR 化**。後追い ADR も価値があります。

---

## 11) 作成ショートカット（任意）
```bash
# 新規 ADR 作成の雛形出力例
d=docs/adrs && today=$(date +%Y%m%d) && seq=0001 && \
cat > $d/ADR-${today}-${seq}-short-title.md <<'EOF'
# ADR-YYYYMMDD-xxxx — {短い決定タイトル}

**Status:** Proposed  
**Date:** YYYY-MM-DD  
**Owners:** {role or people}

## Context
...

## Decision
...

## Consequences
...

## Rollout / Migration
...

## References
...
EOF
```

---

## 12) 変更履歴
- **2025-08-14:** v1.0 初版（索引/運用ルール/テンプレ/候補一覧）。  
  旧内容に *Coding Standards* が含まれていたため、該当内容は `../governance/Coding-Standards.md` を正とする方針を明記。
