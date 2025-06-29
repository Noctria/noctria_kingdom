# veritas/generate/llm_prompt_builder.py

from pathlib import Path

def load_strategy_template() -> str:
    """
    Veritas戦略テンプレート（simulate関数付き）を読み込む関数。
    Airflow互換の構造に準拠したテンプレートを返す。
    """
    path = Path(__file__).parent / "templates" / "strategy_template.py"
    if not path.exists():
        raise FileNotFoundError(f"❌ テンプレートが見つかりません: {path}")
    return path.read_text()
