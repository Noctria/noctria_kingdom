<!-- docs/ops/dev-flow.md -->
# 開発運用ガイド（GitHub主導 + adopt/* 自動化）

最終更新: 2025-09-14

このガイドは **「手動は GitHub の `main` を直接編集→ローカルは pull」**、**「生成/検証は `adopt/*` ブランチで自己ホストCI→PR→main」** の二本立て運用をまとめたものです。

---

## 目次
1. [手動開発フロー（人手で書く）](#1-手動開発フロー人手で書く)
2. [AI/PDCA フロー（adopt/* で検証）](#2-aipdca-フローadopt-で検証)
3. [ワークフロー一覧とトリガ](#3-ワークフロー一覧とトリガ)
4. [ブランチ保護・運用ルール](#4-ブランチ保護運用ルール)
5. [自己ホストランナーの確認](#5-自己ホストランナーの確認)
6. [トラブルシューティング](#6-トラブルシューティング)
7. [コマンド速見表](#7-コマンド速見表)

---

## 1) 手動開発フロー（人手で書く）

### 1-1. GitHub（ブラウザ側）
1. `main` ブランチで対象ファイルを編集
2. **Commit directly to `main`** で保存
3. 必要に応じて Actions の軽いチェックを確認

> ポリシー: **小さな修正・設定調整は GitHub 側で行う**。ローカルは pull で同期するだけに寄せる。

### 1-2. ローカル（WSL/venv）
```bash
git fetch origin
git switch main
git pull --ff-only          # GitHubの変更を取り込む（fast-forwardのみ）
```

**注意**: `adopt/*` に居る状態で `git pull` すると「追跡がない」警告になりやすい。  
→ **pull は main 上で実行**が安全。

---

## 2) AI/PDCA フロー（adopt/* で検証）

### 2-1. ローカルで作業（生成・大改修用）
```bash
git switch -c adopt/<topic>  # 例: adopt/alpha-sizer-v2
# 生成/修正/テスト...
git add -A
git commit -m "feat: <変更概要>"
git push -u origin HEAD
```

### 2-2. 何が自動で起きる？
- **Adopt Auto PR（Hosted）** が走り、`adopt/<topic>` → `main` の **PRを自動作成**
- **Backtest on Adopt PR（Self-hosted）** が起動し、自己ホストランナーで検証
- 成果物（ログ/JSON/HTML レポート）は Actions の **Artifacts** に収集

### 2-3. 取り込み
- PR の Checks が **グリーン**になったら **Merge**（Squash 推奨）
- ローカルを同期
```bash
git switch main
git pull --ff-only
git branch -d adopt/<topic>
git push origin --delete adopt/<topic>   # リモート掃除（任意）
```

---

## 3) ワークフロー一覧とトリガ

| ワークフロー名 | 役割 | 主なトリガ | ランナー |
|---|---|---|---|
| **Adopt Auto PR** | adopt ブランチから PR 自動作成 | `push`（`adopt/*`）・手動 | Hosted |
| **Backtest on Adopt PR (self-hosted)** | adopt PR 自動検証・成果物収集・PRコメント | `pull_request`（adopt→main）・手動 | Self-hosted |
| **Airflow Backtest (Local)** | ローカルスクリプト or Airflow 連携の簡易バックテスト | `workflow_dispatch` / `schedule` | Hosted |

**代表的なチェック名（例）**
- `Adopt Auto PR / create-or-update-pr (push)`
- `Backtest on Adopt PR (self-hosted) / backtest-on-adopt`
- `Codex Quality Gate / quality (pull_request)`
- `noctria_policy_check / policy (pull_request)`

**手動実行のコツ**
- Actions → 対象ワークフロー → **Run workflow** からブランチや引数を指定
- PR で一度走らせると、**ブランチ保護の「Required status checks」候補に出やすい**

---

## 4) ブランチ保護・運用ルール

> プライベートRepoでの Free プランは**完全強制にならない**場合あり。  
> 当面は**運用で徹底**し、将来的に有効化を検討。

推奨設定（GitHub の Branch protection rules）:
- ✅ **Require a pull request before merging**
- ✅ **Require approvals**（最低 1）
- ✅ **Require approval of the most recent reviewable push**
- ✅ **Require status checks to pass before merging**  
  - Backtest on Adopt PR（self-hosted）
  - Codex Quality Gate
  - noctria_policy_check
- ✅ **Require branches to be up to date before merging**

運用ルール:
- `main` へは **PR 経由のみ**（手動編集は GitHub UI で直接コミットする小変更に限定）
- 生成や重い検証は **必ず `adopt/*`** で行い、自己ホストでチェックを通す

---

## 5) 自己ホストランナーの確認

- GitHub → **Actions → Runners** にオンライン表示されていること
- ホスト側ディレクトリ:
  - ルート: `actions-runner/`
  - 作業領域: `actions-runner/_work/<repo>/<repo>/`
  - 診断ログ: `actions-runner/_diag/Runner_*.log`
- 再起動（対話）:
```bash
cd actions-runner
./run.sh
```
> systemd 未導入の場合は手動起動でOK。常駐化したい場合は `svc.sh install` を検討（要権限）。

---

## 6) トラブルシューティング

### 6-1. 「pull できない/追跡がない」
```bash
git fetch origin
git switch main
git pull --ff-only
# adopt ブランチで pull したいなら（推奨はしない）
git branch --set-upstream-to=origin/adopt/<topic>
```

### 6-2. `.gitignore` に無視されて add できない
```bash
git check-ignore -v <file>  # どのルールに当たったか確認
git add -f <file>           # 本当に必要なときだけ強制追加
```

### 6-3. pre-commit に止められる
- `main` の allowed_files は厳格。**基本は GitHub で main を編集**。
- `adopt/*` は緩和済み。どうしてもなら `--no-verify`（緊急時のみ）。

### 6-4. 「Run workflow」が出ない／候補にチェック名が出ない
- 一度 PR/Run を走らせて**実績**を作る（候補リストに出るようになる）
- `workflow_dispatch` が定義されたブランチであることを確認

### 6-5. 「Actions は PR を作成できません（403）」  
- リポジトリのポリシー（Actions が PR を作れるか）を緩和済みか確認

### 6-6. 「Validation Failed: No commits between main and adopt/...」
- 差分が無い。**対象ファイルに実変更**を入れて再 push

### 6-7. Self-hosted にジョブが来ない
- ジョブの `runs-on` が `self-hosted` になっているか
- ランナーがオンラインか（Actions → Runners / `_diag` ログ）
- Runner のラベル/グループでフィルタしていないか（`runs-on: [self-hosted, linux]` など）

---

## 7) コマンド速見表

```bash
# GitHubでmainを編集した後、ローカルに反映
git fetch origin && git switch main && git pull --ff-only

# 新しいPDCAトピック開始
git switch -c adopt/<topic>

# 変更をPRに載せる（自動PR作成トリガ）
git add -A && git commit -m "feat: <msg>" && git push -u origin HEAD

# PRがグリーンになったらMerge→ローカル同期
git switch main && git pull --ff-only

# adoptブランチの後片付け
git branch -d adopt/<topic> && git push origin --delete adopt/<topic>
```

---
**備考**
- Airflow 連携（任意）: Secrets `AIRFLOW_BASE_URL` / `AIRFLOW_TOKEN` 設定時に DAG をトリガ可能  
- 成果物: `airflow_docker/backtests/**/result.json` / `report.html` / `logs/*.json` などが Artifacts に収集
- ブランチ命名: `adopt/<目的-短い説明>`（例: `adopt/alpha-sizer-v2`）
