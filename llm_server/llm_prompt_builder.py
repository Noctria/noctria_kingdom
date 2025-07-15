#!/usr/bin/env python3
# coding: utf-8

"""
📜 LLM Prompt Builder (v2.0)
- Veritasが戦略を生成する際に使用する、基礎となる戦略テンプレートを読み込む。
"""

import logging
from pathlib import Path

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')


def load_strategy_template() -> str:
    """
    Veritasが新たな戦略を記述するための「魔法の羊皮紙」（戦略テンプレート）を読み込む。
    この羊皮紙は、LLMが王国の作法に則った戦略を生成するための基礎となる。
    """
    try:
        # このスクリプトと同じ階層にある'templates'フォルダ内のテンプレートを指す
        # 注意: このパスが機能するには、`llm_server/templates/strategy_template.py`というファイル構造が必要です。
        template_path = Path(__file__).parent / "templates" / "strategy_template.py"
        
        if not template_path.exists():
            logging.error(f"戦略の羊皮紙が見つかりません。パス: {template_path}")
            raise FileNotFoundError(f"Template not found at: {template_path}")
            
        logging.info(f"戦略の羊皮紙を読み込みました: {template_path}")
        return template_path.read_text(encoding="utf-8")

    except Exception as e:
        error_message = f"戦略の羊皮紙を読み込む際に予期せぬエラーが発生しました: {e}"
        logging.error(error_message, exc_info=True)
        # エラーが発生した場合でも、サーバーが完全に停止しないよう、空のテンプレートを返すか、
        # あるいは呼び出し元で処理できるよう例外を再送出する。ここでは例外を送出する。
        raise


# ========================================
# ✅ 単体テスト＆実行ブロック
# ========================================
if __name__ == "__main__":
    logging.info("--- 羊皮紙読み込み機能の単体テストを開始 ---")
    try:
        template_content = load_strategy_template()
        print("\n📜 読み込まれた羊皮紙の内容（冒頭部分）:")
        print("-" * 30)
        print(template_content[:300] + "...")
        print("-" * 30)
        logging.info("✅ 羊皮紙の読み込みに成功しました。")
    except FileNotFoundError as e:
        logging.error(f"テスト失敗: {e}")
    except Exception as e:
        logging.error(f"テスト中に予期せぬエラーが発生しました: {e}")
    logging.info("--- 羊皮紙読み込み機能の単体テストを終了 ---")

