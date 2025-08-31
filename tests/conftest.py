# tests/conftest.py
"""
pytest 共通設定 (Codex/Noctria)
- 環境に無い重依存 (torch/gym/MetaTrader5) を使うテストを自動 skip
- observability.emit_alert をモンキーパッチしてアラートを捕捉 (capture_alerts)
- CODEX_LIGHT=1 のとき integration を追加で skip
"""

from __future__ import annotations

import os
import importlib.util
from pathlib import Path
from typing import List, Dict, Any

import pytest


# ---------- 収集段階でのスキップ（ライブラリ有無で判定） ----------
def pytest_ignore_collect(collection_path: Path, config):
    """
    pytest>=8 の新シグネチャ: (collection_path: pathlib.Path, config)
    指定ライブラリが無い場合は、該当テストファイルを収集しない。
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
        # 本体側の未整備モジュールに依存するテスト群（必要に応じて追加）
        # 例: "tests/execute_order_test.py" など
        # ランナー側で明示指定することを想定し、ここでは収集抑止しない。
    }

    path_str = collection_path.as_posix()
    for lib, files in skip_map.items():
        if not importlib.util.find_spec(lib):
            if any(path_str.endswith(f) for f in files):
                return True  # → そのファイルを無視（skip）


# ---------- マーカーによるスキップ（環境変数で制御） ----------
def pytest_collection_modifyitems(config, items):
    """
    CODEX_LIGHT=1 のとき、integration マークを付けたテストを skip。
    """
    if os.getenv("CODEX_LIGHT"):
        skip_integration = pytest.mark.skip(reason="Skipping integration tests in CODEX_LIGHT mode")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


# ---------- アラート捕捉フィクスチャ ----------
@pytest.fixture
def capture_alerts(monkeypatch) -> List[Dict[str, Any]]:
    """
    observability.emit_alert を差し替えて、テスト中に発火したアラートを回収する。
    - plan_data.observability.emit_alert
    - src.plan_data.observability.emit_alert
    のどちらにも対応（相対/絶対 import 差分を吸収）
    """
    captured: List[Dict[str, Any]] = []

    def _capture(**kw):
        # そのままの形で記録（テスト側で kind / reason などを参照できる）
        captured.append(kw)

    # 片方しか存在しない場合もあるので raising=False で緩く当てる
    try:
        monkeypatch.setattr("plan_data.observability.emit_alert", _capture, raising=False)
    except Exception:
        pass
    try:
        monkeypatch.setattr("src.plan_data.observability.emit_alert", _capture, raising=False)
    except Exception:
        pass

    return captured
