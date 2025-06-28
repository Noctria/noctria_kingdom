import logging
from core.Noctria import Noctria

def test_noctria_execute_trade():
    """
    最小限の統合テスト:
    - NoctriaクラスがAI戦略層を呼び出せるか
    - EAとAI統合の結果として、最終戦略が返るか
    """
    logging.basicConfig(level=logging.DEBUG)

    # インスタンス生成
    noctria_ai = Noctria()

    # 実際のトレード実行フローを呼び出す
    result = noctria_ai.execute_trade()

    # 出力確認
    print("テスト結果:", result)
    assert result is not None, "No result returned"
    assert isinstance(result, str), "Result should be a string"

if __name__ == "__main__":
    test_noctria_execute_trade()
