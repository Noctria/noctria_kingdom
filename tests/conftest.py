# tests/conftest.py
"""
pytest の共通設定 (Codex/Noctria テスト制御)

目的:
- Codex (CPU/tensorflow-cpu 環境) では重いテストを自動 skip
- GPU/本番環境 (torch, gym, MetaTrader5 あり) では全テスト実行
"""

import pytest
import importlib.util
import os


def pytest_ignore_collect(path, config):
    """
    テスト収集時にライブラリが無ければ、そのテストファイルを無視する。
    """
    skip_map = {
        # PyTorch (RL/DQN 系)
        "torch": [
            "tests/test_dqn_agent.py",
        ],
        # Gym (MetaAI 強化学習系)
        "gym": [
            "tests/test_meta_ai_env_rl.py",
            "tests/test_meta_ai_rl.py",
            "tests/test_meta_ai_rl_longrun.py",
            "tests/test_meta_ai_rl_real_data.py",
        ],
        # MetaTrader5 (外部ブローカー接続)
        "MetaTrader5": [
            "tests/test_mt5_connection.py",
        ],
    }

    for lib, files in skip_map.items():
        if not importlib.util.find_spec(lib):  # ライブラリが存在しない場合
            if any(str(path).endswith(f) for f in files):
                return True  # → pytest がそのファイルをスキップ


def pytest_collection_modifyitems(config, items):
    """
    環境変数などで制御したい場合に使える hook。
    例: CODEX_LIGHT=1 のときは integration テストを skip。
    """
    if os.getenv("CODEX_LIGHT"):
        skip_integration = pytest.mark.skip(reason="Skipping integration tests in CODEX_LIGHT mode")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
