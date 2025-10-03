# scripts/call_noctria_with_king_ops.py  ← 差し替え版（フル）
from openai import OpenAI
from pathlib import Path

BASE_URL = "http://127.0.0.1:8012/v1"
MODEL = "noctria-king:latest"

king_ops_path = Path("docs/governance/king_ops_prompt.yaml")
king_ops_text = king_ops_path.read_text(encoding="utf-8", errors="ignore")

client = OpenAI(base_url=BASE_URL, api_key="dummy")

messages = [
    {
        "role": "system",
        "content": f"""[Noctria王 SYSTEM 指示書]
---
{king_ops_text}
---

追加運用ルール:
- 出力は Noctria 王国の「今日の運用」に最適化。
- 各タスクは 30〜90分で完了できる粒度に分割。
- **具体的コマンド・対象ファイル・パス・検証手順・完了条件**を必ず含める。
- 失敗時のフォールバック（代替案）も併記する。
- 重要：実行環境は WSL2/Ubuntu、OpenAI互換エンドポイントは http://127.0.0.1:8009/v1、モデルは llama3.1:8b-instruct-q4_K_M。
- 出力フォーマット（厳守）:

# 本日の優先タスク（3）
1) <タイトル>（所要: X分｜優先度: High/Med/Low｜依存: 例 Airflow/DB）
   目的:
   手順:
     - <具体コマンド or 変更手順>（行頭$でシェル、ファイル編集はパス明記）
     - ...
   検証:
     - <何を実行/確認してOKとするか>
   完了条件:
     - <定量 or 具体イベント>
   リスク/代替:
     - <起こりうる失敗と回避/代替>

2) ...
3) ...
"""
    },
    {
        "role": "user",
        "content": """現状:
- GPUブリッジは http://127.0.0.1:8009/v1 で疎通OK（Ollama llama3.1:8b-instruct-q4_K_M）
- プロジェクト: /mnt/d/noctria_kingdom
- 既存: Airflow(DAG)、PDCA/AutoFix、docs/governance/king_ops_prompt.yaml

候補（例、必ず評価の上で選定）:
- ブリッジ側に KING_OPS_PATH を環境変数で設定し、SYSTEM 自動差し込みを実装
- /pdca/summary のHUD整備（期間フィルタ・カード・テーブル）
- Airflow DAG 健全性チェック（importタイムアウト/依存/スケジューラ状態）
- autossh or systemd --user でトンネル恒常化
- モデルエイリアス noctria-king の導入（将来差し替え容易化）

依頼:
- 今日やるべき **最重要の3タスク** を上記フォーマットで具体化して出力。
- それぞれに「なぜ今日やるのが最適か」を手短に含めて。"""
    }
]

resp = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    temperature=0.2,
    max_tokens=1000,
)
print(resp.choices[0].message.content)
