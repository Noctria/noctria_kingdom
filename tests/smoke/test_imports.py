"""
Smoke: import が壊れていないかの最小確認。
CIでは -q で実行される想定。
"""

def test_can_import_package():
    # 主要パッケージ名があれば書き換え可（例: noctria_core など）
    # import は失敗しないことだけを確認（存在しなければスキップ）
    try:
        import src.core  # noqa: F401
    except ModuleNotFoundError:
        import pytest
        pytest.skip("src.core がパッケージ化されていないためスキップ")

def test_probe_function_if_exists():
    """
    任意：存在すれば codeowners_probe.ping() が呼べることを確認。
    なくてもスキップ。
    """
    import importlib
    import pytest
    try:
        mod = importlib.import_module("src.core.codeowners_probe")
    except ModuleNotFoundError:
        pytest.skip("codeowners_probe がないのでスキップ")
        return
    assert hasattr(mod, "ping")
    assert mod.ping() == "ok"
