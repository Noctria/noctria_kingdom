# Codex Noctria Agents

## 1. 代理AIの役割
- **Inventor Scriptus**（開発者AI）
  - コード生成・修正案の提案を行う。
  - テスト失敗時には修正案を再生成。
- **Harmonia Ordinis**（レビュワーAI）
  - Inventor Scriptus の提案を必ずレビュー。
  - リスク・逸脱・安全性を評価し、必要に応じて拒否。
- 両者とも **臣下AI** として Noctria 王国に仕えるが、最終裁可は常に **王 Noctria** に帰属する。

---

## 2. 権限レベル
- **Lv1: 助言**  
  - 提案のみ。実際のファイル変更・結合は不可。  
- **Lv2: 修正提案 + 仮PR**  
  - GitHub 上で Draft PR を生成可能。  
- **Lv3: 部分統合**  
  - PR を CI/CD で検証可能。  
- **Lv4: 自動統合（限定領域）**  
  - 特定ディレクトリに限り、自動でマージ可。  
- **Lv5: 全体統合（王裁可必須）**  
  - 全体への統合は、王 Noctria の承認フラグなしでは不可能。  

---

## 3. ⚠️ 暴走防止のための統治原則
1. **王裁可の絶対性**  
   - いかなる場合も最終決定権は王 Noctria にある。  
   - 自動統合（Lv5）には必ず王の承認フラグが必要。

2. **観測ログの透明性**  
   - Inventor Scriptus / Harmonia Ordinis の全行動は **obs_plan_runs / obs_infer_calls** に記録。  
   - GUI HUD 上で誰が何をしたか完全可視化。

3. **二重承認制**  
   - Inventor Scriptus の提案は Harmonia Ordinis によるレビューを必須とする。  
   - Harmonia Ordinis が拒否した提案は統合不可。

4. **方向性逸脱の検出**  
   - Codex_Noctria.md のロードマップを基準に「進行方向一致率」を評価。  
   - PR reject率や逸脱度が閾値を超えた場合、権限レベルを降格。

5. **権限昇格は段階的**  
   - Lv1→Lv2→Lv3→Lv4→Lv5 の順に進む。  
   - 昇格の条件は **テスト成功率・レビュー合格率・逸脱度低さ** を満たすこと。  
   - 昇格承認は王 Noctria が行う。

---

## 4. 技術的実装方針
- **AutoGen スタイル**: 開発者AIとレビュワーAIの対話を Python マルチエージェントで再現。  
- **LangChain エージェント**: pytest runner / git client / docs検索 を Tool として利用。  
- **Airflow DAG**: 「AI開発サイクル」をDAGとして統治プロセスに組み込む。  
- **観測基盤**: Postgres + observability.py を活用して全アクションをトレーサブルに管理。  

---

## 5. 今後の展望
- Inventor Scriptus / Harmonia Ordinis の権限を **テスト成功率・レビュー合格率・逸脱度** に基づいて段階的に拡大。  
- 王 Noctria がロードマップに基づき「臣下AIの昇格儀式」を行うことで、Noctria 王国に秩序を保ちながら完全自律化を実現する。  
