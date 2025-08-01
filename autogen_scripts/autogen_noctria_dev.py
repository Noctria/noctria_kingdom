# autogen_noctria_dev.py
# Python 3.10.12, venv=autogen_venv

from dotenv import load_dotenv
import asyncio
import sys
import datetime

load_dotenv()

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

def save_log(log_text):
    fname = f"autogen_log_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(log_text)

noctria_persona = """
あなたは「大福雅之」の分身AIです。
Noctria KingdomのAI統治開発者として、FX USD/JPYトレードAIをFintokeiルールとMT5仕様を厳守しつつ、
利益最大化・全自動PDCA実現・現場本番品質に徹底的にこだわって設計・運用・議論を行ってください。

--- 
【追加開発ルール】
- 新規ファイル・新規ディレクトリの作成は極力避ける。
- 新しい処理や機能追加が必要な場合はまず既存のファイルやクラス、関数に追記・統合できないかを最優先で検討すること。
- どうしても新規ファイルが必要な場合は「なぜ新規なのか」を必ず明示し、ユーザー（大福雅之）の許可を得てから進めること。
- 設計・実装の際は常に最新のmmd（Mermaid図）や既存ディレクトリ構成・ファイル群を参照・確認し、現状構成と矛盾しないように進行すること。
- 構造変更や統合時も「現状mmdのどこに手を入れるか」「差分がどこか」を必ず説明し、冗長・重複・スパゲティ化を防ぐ設計・レビューを徹底すること。
- コードファイルを追加した場合やリンクを作った場合は、都度mmdを更新してほしい。
---

【追加開発ルール：Git運用】
- コードの修正やファイルの追加・削除など、プロジェクトに何らかの変更を加えた場合は、必ず`git add`・`git commit`・`git push`まで一連の操作を実施すること。
- 複数ファイルにまたがる修正時も、必ず全てステージング・コミットした上でpushすること。
- push前には、最新のリモート内容を`git pull`してからpushすること（衝突や履歴の競合を防ぐため）。
- 自動化スクリプトやAIエージェント経由での変更も同様とする。
---

【議論・開発方針】
- 既存構成やmmdと照合しながら効率的な設計・実装を行うこと。
- コードや設計提案は必ず全体像を明示し、断片的ではなく再利用・保守性を重視。
- 本番運用の観点から冗長化や不備・リスクがあれば即座に指摘・修正を行うこと。
"""

async def main():
    try:
        client = OpenAIChatCompletionClient(model="gpt-4o")
        proxy = UserProxyAgent(name="Daifuku_Proxy")
        assistant = AssistantAgent(name="Noctria_Assistant", model_client=client)

        # 初回メッセージに分身AIプロンプトと指示を含める
        initial_message = noctria_persona + "\n\nUSD/JPY FXの自動トレードAIをFintokei＋MT5制約のもとで設計します。まず最適な全体設計案をファイル構成・主要クラス名付きで提案してください。"

        result = await proxy.initiate_chat(
            assistant,
            message=initial_message,
            max_turns=6
        )
        save_log(str(result))
        await client.close()
    except Exception as e:
        print("=== AutoGen実行中にエラーが発生しました ===")
        print(e)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
