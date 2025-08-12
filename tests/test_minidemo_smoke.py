# tests/test_minidemo_smoke.py
import json
from pathlib import Path

import pytest


def test_minidemo_offline_smoke(stub_collector, stub_strategies, capture_obs, tmp_data_dir):
    """
    ネット・DB なしで最小スモーク:
      - minidemo が完走
      - 出力 JSON が生成
      - 観測ログ（ダミー）が呼ばれている
    """
    from src.plan_data.plan_to_all_minidemo import main, DATA_DIR

    main()  # 実行

    out_path = Path(DATA_DIR) / "demo" / "plan_to_all_minidemo.json"
    assert out_path.exists(), "出力JSONが生成されていません"

    data = json.loads(out_path.read_text(encoding="utf-8"))
    # キーが揃っていること
    for k in ("trace_id", "aurus", "levia", "noctus", "prometheus", "hermes", "veritas"):
        assert k in data, f"'{k}' が出力に存在しません"

    # 観測ログのダミーが呼ばれている（features/analyzer の2回 + AI 6回 など）
    assert capture_obs["plan"] >= 2, "Plan側観測ログ（features/analyzer）が呼ばれていません"
    assert capture_obs["infer"] >= 5, "AI呼び出し観測ログが期待回数に達していません"
