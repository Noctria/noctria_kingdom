# tests/conftest.py
import os
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

# ------- PythonPath をプロジェクトルートに通す -------
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def sample_df():
    """ネットアクセス不要の最小サンプル。必須カラムのみ。"""
    today = datetime.utcnow().date()
    dates = [pd.Timestamp(today - timedelta(days=i)) for i in range(14)][::-1]
    df = pd.DataFrame(
        {
            "date": dates,
            "usdjpy_close": [150 + i * 0.1 for i in range(14)],
            "sp500_close": [5000 + i for i in range(14)],
            "vix_close": [15 + (i % 3) for i in range(14)],
            "news_count": [10 + (i % 5) for i in range(14)],
            "news_positive": [5 + (i % 3) for i in range(14)],
            "news_negative": [3 + (i % 2) for i in range(14)],
            "cpiaucsl_value": [300 + (i % 2) for i in range(14)],
            "unrate_value": [4.0 + (i % 2) * 0.1 for i in range(14)],
            "fedfunds_value": [5.0 for _ in range(14)],
        }
    )
    return df


@pytest.fixture()
def stub_collector(monkeypatch, sample_df):
    """PlanDataCollector.collect_all をスタブしてネットを切る。"""
    import src.plan_data.collector as collector_mod

    def _fake_collect_all(self, lookback_days=60):
        return sample_df.copy()

    monkeypatch.setattr(collector_mod.PlanDataCollector, "collect_all", _fake_collect_all)


@pytest.fixture()
def stub_strategies(monkeypatch):
    """
    各 Strategy の重い処理をスタブ。返却フォーマットは実装互換。
    """
    from src.strategies import aurus_singularis as mod_aurus
    from src.strategies import levia_tempest as mod_levia
    from src.strategies import noctus_sentinella as mod_noctus
    from src.strategies import prometheus_oracle as mod_prom
    from src.strategies import hermes_cognitor as mod_hermes
    from src.veritas import veritas_machina as mod_veritas
    import pandas as pd

    def _aurus_propose(self, feature_dict, **kw):
        return {"symbol": "USDJPY", "direction": "LONG", "qty": 0.1, "confidence": 0.6, "reasons": ["stub"], "meta": {}}

    def _levia_propose(self, feature_dict, **kw):
        return {"symbol": "USDJPY", "direction": "SHORT", "qty": 0.05, "confidence": 0.55, "reasons": ["stub"], "meta": {}}

    def _noctus_calc(self, feature_dict, **kw):
        return {"lot": 0.03, "risk_ok": True, "reason": "stub"}

    def _prom_predict(self, df, n_days=5, **kw):
        # 予測結果は小さな DataFrame を返す
        return pd.DataFrame({"date": pd.date_range("2025-01-01", periods=n_days), "usdjpy_pred": [150.1] * n_days})

    def _hermes_propose(self, payload, **kw):
        return {"summary": "stub explanation", "labels": payload.get("labels", [])}

    def _veritas_propose(self, **kw):
        return {"strategies": [{"name": "stub-strategy", "params": {"x": 1}}]}

    monkeypatch.setattr(mod_aurus.AurusSingularis, "propose", _aurus_propose, raising=True)
    monkeypatch.setattr(mod_levia.LeviaTempest, "propose", _levia_propose, raising=True)
    monkeypatch.setattr(mod_noctus.NoctusSentinella, "calculate_lot_and_risk", _noctus_calc, raising=True)
    monkeypatch.setattr(mod_prom.PrometheusOracle, "predict_future", _prom_predict, raising=True)
    monkeypatch.setattr(mod_hermes.HermesCognitorStrategy, "propose", _hermes_propose, raising=True)
    monkeypatch.setattr(mod_veritas.VeritasMachina, "propose", _veritas_propose, raising=True)


@pytest.fixture()
def capture_obs(monkeypatch):
    """
    観測ログを DB に書かずにカウントだけ取る。
    - plan_to_all_minidemo._call_with_obs 内の log_infer_call を差し替え
    - features / analyzer の log_plan_run も差し替え
    """
    calls = {"infer": 0, "plan": 0}

    def _fake_log_infer(conn_str, model, ver, dur_ms, success, feature_staleness_min, trace_id):
        calls["infer"] += 1

    def _fake_log_plan(conn_str, phase, rows, dur_sec, missing_ratio, error_rate, trace_id):
        calls["plan"] += 1

    # 各モジュールで直接インポートされている関数を個別に差し替え
    monkeypatch.setattr("src.plan_data.plan_to_all_minidemo.log_infer_call", _fake_log_infer, raising=False)
    monkeypatch.setattr("src.plan_data.features.log_plan_run", _fake_log_plan, raising=False)
    monkeypatch.setattr("src.plan_data.analyzer.log_plan_run", _fake_log_plan, raising=False)

    return calls


@pytest.fixture()
def tmp_data_dir(monkeypatch, tmp_path):
    """DATA_DIR を一時ディレクトリに差し替え。"""
    import src.plan_data.plan_to_all_minidemo as demo_mod
    monkeypatch.setattr(demo_mod, "DATA_DIR", tmp_path, raising=True)
    return tmp_path


def env_has_obs_dsn():
    dsn = os.getenv("NOCTRIA_OBS_PG_DSN")
    return bool(dsn) and dsn.startswith("postgresql://")


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: requires NOCTRIA_OBS_PG_DSN and running Postgres")
