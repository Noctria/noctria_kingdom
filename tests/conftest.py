from __future__ import annotations

import json as _json
import logging
import sys
import typing as t
from pathlib import Path

import pytest

# tests/conftest.py

# --- Import path bootstrap (keep existing behavior) -------------------------

ROOT = Path(__file__).resolve().parents[1]  # リポジトリルート
SRC = ROOT / "src"  # src/ レイアウトも考慮

for p in map(str, {ROOT, SRC}):
    if p not in sys.path:
        sys.path.insert(0, p)

# --- sanitize sys.path: remove other runner clones --------------------------
# actions-runner の別クローンが sys.path に混入していると
# 「import file mismatch」が発生するため、現在の作業ツリー以外を除外する。
OTHER_CLONE_HINTS = ("actions-runner/_work/noctria_kingdom/noctria_kingdom",)
for entry in list(sys.path):
    try:
        resolved = str(Path(entry).resolve())
    except Exception:
        continue
    # 現在の作業ツリー配下は保持
    if resolved.startswith(str(ROOT.resolve())):
        continue
    # ランナー配下の別クローンは除外
    if any(h in resolved for h in OTHER_CLONE_HINTS):
        sys.path.remove(entry)

# 現在の作業ツリーを最優先に（SRC を前に）
for q in map(str, {ROOT, SRC}):
    if q in sys.path:
        sys.path.remove(q)
for q in map(str, [SRC, ROOT]):
    sys.path.insert(0, q)

# --- Fixtures ---------------------------------------------------------------


@pytest.fixture
def capture_alerts(monkeypatch, capsys):
    """
    Alerts を stdout / logging の両面からキャプチャ。
    - NOCTRIA_OBS_MODE=stdout を強制
    - ルート & noctria.observability のログを捕捉
    - JSON 1行なら dict にパースして格納（tests 側で a.get('kind') が使える）
    - list 風API（len(), iter, __getitem__）を提供
    """
    monkeypatch.setenv("NOCTRIA_OBS_MODE", "stdout")

    class _ListHandler(logging.Handler):
        def __init__(self, sink: t.List[t.Union[str, dict]]):
            super().__init__(level=logging.INFO)
            self._sink = sink

        def emit(self, record: logging.LogRecord) -> None:
            try:
                msg = self.format(record)
            except Exception:
                msg = record.getMessage()
            if not msg:
                return
            # JSONならdictへ
            try:
                obj = _json.loads(msg)
                if isinstance(obj, dict):
                    self._sink.append(obj)
                    return
            except Exception:
                pass
            self._sink.append(str(msg))

    class Capture:
        def __init__(self):
            self._lines: t.List[t.Union[str, dict]] = []
            self._handler = _ListHandler(self._lines)
            self._handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
            self._root_logger = logging.getLogger()  # ルート
            self._obs_logger = logging.getLogger("noctria.observability")  # 直接
            self._prev_root_level: int | None = None
            self._attached = False

        def _attach(self):
            if self._attached:
                return
            self._root_logger.addHandler(self._handler)
            self._obs_logger.addHandler(self._handler)
            self._prev_root_level = self._root_logger.level
            # INFO以上を拾う
            if self._root_logger.level in (
                logging.NOTSET,
                logging.WARNING + 10,
                logging.ERROR,
                logging.CRITICAL,
            ):
                self._root_logger.setLevel(logging.INFO)
            self._obs_logger.propagate = True
            self._attached = True

        def _detach(self):
            if not self._attached:
                return
            try:
                self._root_logger.removeHandler(self._handler)
                self._obs_logger.removeHandler(self._handler)
                if self._prev_root_level is not None:
                    self._root_logger.setLevel(self._prev_root_level)
            finally:
                self._attached = False

        def flush(self) -> t.List[t.Union[str, dict]]:
            """stdout を flush し、ログとマージして重複除去した行配列を返す"""
            out = capsys.readouterr().out
            if out:
                for ln in out.splitlines():
                    ln = ln.rstrip()
                    if not ln:
                        continue
                    # JSONならdictへ
                    try:
                        obj = _json.loads(ln)
                        if isinstance(obj, dict):
                            self._lines.append(obj)
                            continue
                    except Exception:
                        pass
                    self._lines.append(ln)
            # 重複除去（順序保持）
            seen: set[str] = set()
            uniq: list[t.Union[str, dict]] = []
            for ln in self._lines:
                key = _json.dumps(ln, ensure_ascii=False) if isinstance(ln, dict) else ln
                if key not in seen:
                    uniq.append(ln)
                    seen.add(key)
            self._lines = uniq
            return list(self._lines)

        # 便利API
        def contains(self, substr: str) -> bool:
            return any(
                (
                    (substr in ln)
                    if isinstance(ln, str)
                    else (substr in _json.dumps(ln, ensure_ascii=False))
                )
                for ln in self.flush()
            )

        # list風
        def __len__(self):
            return len(self.flush())

        def __iter__(self):
            return iter(self.flush())

        def __getitem__(self, idx: int):
            return self.flush()[idx]

        def __call__(self) -> t.List[t.Union[str, dict]]:
            return self.flush()

        # コンテキスト管理
        def __enter__(self):
            capsys.readouterr()  # 前残りを捨てる
            self._lines.clear()
            self._attach()
            return self

        def __exit__(self, exc_type, exc, tb):
            try:
                self.flush()
            finally:
                self._detach()
            return False

    cap = Capture()
    cap._attach()  # with を使わないスタイルでも有効化
    try:
        yield cap
    finally:
        cap._detach()


# --- Marker-based default skipping (heavy/gpu/external) ---------------------
# 目的:
# - デフォルト実行では heavy/gpu/external を明示的に skip 表示にする
# - ユーザが -m を指定した場合はその指定を尊重（本フックは無効）
#
# 連携:
# - pytest.ini の addopts で `-m "not heavy and not gpu and not external"` を既定設定
# - 重テストには @pytest.mark.heavy / gpu / external を付与
def pytest_collection_modifyitems(config, items):
    selected_expr = config.getoption("-m")
    if not selected_expr or selected_expr.strip() == "not heavy and not gpu and not external":
        skip_heavy = pytest.mark.skip(reason="excluded by default: marker=heavy")
        skip_gpu = pytest.mark.skip(reason="excluded by default: marker=gpu")
        skip_external = pytest.mark.skip(reason="excluded by default: marker=external")
        for item in items:
            if "heavy" in item.keywords:
                item.add_marker(skip_heavy)
            if "gpu" in item.keywords:
                item.add_marker(skip_gpu)
            if "external" in item.keywords:
                item.add_marker(skip_external)


# --- appended: minimal stubs for integration/smoke tests ---
import pytest as _pytest

# stub_collector: .collect() を持つ最小ダミー
try:
    stub_collector  # type: ignore[name-defined]
except NameError:

    @_pytest.fixture
    def stub_collector():
        class _StubCollector:
            def collect(self, *args, **kwargs):
                return {
                    "ok": True,
                    "rows": 0,
                    "missing_ratio": 0.0,
                    "data_lag_min": 0.0,
                }

        return _StubCollector()


# stub_strategies: .get(name)-> strategy(decide()->{"orders":[],"meta":{"risk_adjusted":0.0}})
try:
    stub_strategies  # type: ignore[name-defined]
except NameError:

    @_pytest.fixture
    def stub_strategies():
        class _Strategy:
            def decide(self, *args, **kwargs):
                return {"orders": [], "meta": {"risk_adjusted": 0.0}}

        class _Registry:
            def get(self, name: str):
                return _Strategy()

        return _Registry()


# tmp_data_dir: tmp_path のエイリアス
try:
    tmp_data_dir  # type: ignore[name-defined]
except NameError:

    @_pytest.fixture
    def tmp_data_dir(tmp_path):
        return tmp_path


# --- end appended stubs ------------------------------------------------------

# --- appended: alias fixture capture_obs -> capture_alerts --------------------
try:
    capture_obs  # type: ignore[name-defined]
except NameError:
    import pytest as _pytest

    @_pytest.fixture
    def capture_obs(capture_alerts):
        # reuse the capture_alerts fixture for observability capture
        return capture_alerts


# --- end alias ----------------------------------------------------------------
# --- appended: autouse stub for yfinance (offline smoke) ---
import sys as _sys
import types as _types

import pandas as _pd
import pytest as _pytest


@_pytest.fixture(autouse=True)
def _stub_yfinance_autouse():
    """yfinance が未インストールのときだけ最小スタブを注入。"""
    try:
        import yfinance  # noqa: F401

        return
    except Exception:
        pass

    mod = _types.ModuleType("yfinance")

    def _make_df():
        now = _pd.Timestamp.utcnow()
        if now.tzinfo is None:
            now = now.tz_localize("UTC")
        return _pd.DataFrame(
            {"Open": [1.0], "High": [1.0], "Low": [1.0], "Close": [1.0], "Volume": [0]},
            index=_pd.DatetimeIndex([now], name="Date"),
        )

    def download(tickers, period="1d", interval="1d", **kwargs):
        return _make_df()

    class Ticker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, period="1d", interval="1d", **kwargs):
            return _make_df()

    mod.download = download
    mod.Ticker = Ticker
    _sys.modules["yfinance"] = mod


# --- end yfinance stub -------------------------------------------------------
# --- appended: autouse stub for scipy.stats.norm (offline smoke) ---
import math as _math

import pytest as _pytest


@_pytest.fixture(autouse=True)
def _stub_scipy_stats_norm_autouse():
    """scipy が未インストールの時だけ、scipy.stats.norm を最小実装でスタブする。"""
    try:
        # If real scipy exists, do nothing
        import scipy  # noqa: F401
        from scipy.stats import norm  # noqa: F401

        return
    except Exception:
        pass

    class _Norm:
        def cdf(self, x):
            x = float(x)
            # standard normal CDF via erf
            return 0.5 * (1.0 + _math.erf(x / _math.sqrt(2.0)))

        def ppf(self, q):
            # invert CDF with bisection; robust enough for smoke usage
            q = float(q)
            if not (0.0 < q < 1.0):
                raise ValueError("q must be in (0,1)")
            lo, hi = -10.0, 10.0
            for _ in range(80):
                mid = 0.5 * (lo + hi)
                if self.cdf(mid) < q:
                    lo = mid
                else:
                    hi = mid
            return 0.5 * (lo + hi)

    _scipy = _types.ModuleType("scipy")
    _stats = _types.ModuleType("scipy.stats")
    _stats.norm = _Norm()
    _scipy.stats = _stats  # type: ignore[attr-defined]

    _sys.modules["scipy"] = _scipy
    _sys.modules["scipy.stats"] = _stats


# --- end scipy stub ----------------------------------------------------------
# --- appended: autouse stub for statsmodels.tsa.holtwinters (offline smoke) ---
import numpy as _np
import pytest as _pytest


@_pytest.fixture(autouse=True)
def _stub_statsmodels_holtwinters_autouse():
    """statsmodels が無い環境用に ExponentialSmoothing を最小実装でスタブ。"
    実物がある場合は何もしない。"""
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing  # noqa: F401

        return
    except Exception:
        pass

    class _Fitted:
        def __init__(self, n=0):
            self.fittedvalues = _np.zeros(n, dtype=float)

        def forecast(self, steps=1):
            return _np.zeros(int(steps), dtype=float)

    class ExponentialSmoothing:  # minimal signature
        def __init__(self, endog, *args, **kwargs):
            self._n = len(endog) if hasattr(endog, "__len__") else 0

        def fit(self, *args, **kwargs):
            return _Fitted(self._n)

    _statsmodels = _types.ModuleType("statsmodels")
    _tsa = _types.ModuleType("statsmodels.tsa")
    _holt = _types.ModuleType("statsmodels.tsa.holtwinters")
    _holt.ExponentialSmoothing = ExponentialSmoothing

    _statsmodels.tsa = _tsa  # type: ignore[attr-defined]
    _sys.modules["statsmodels"] = _statsmodels
    _sys.modules["statsmodels.tsa"] = _tsa
    _sys.modules["statsmodels.tsa.holtwinters"] = _holt


# --- end statsmodels stub ----------------------------------------------------
