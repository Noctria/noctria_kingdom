# tests/conftest.py
from __future__ import annotations

# --- Import path bootstrap (keep existing behavior) -------------------------
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # リポジトリルート
SRC = ROOT / "src"                          # src/ レイアウトも考慮

for p in map(str, {ROOT, SRC}):
    if p not in sys.path:
        sys.path.insert(0, p)

# --- Fixtures ---------------------------------------------------------------
import logging
import typing as t
import json as _json
import pytest


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
            if self._root_logger.level in (logging.NOTSET, logging.WARNING + 10, logging.ERROR, logging.CRITICAL):
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
            return any((substr in ln) if isinstance(ln, str) else (substr in _json.dumps(ln, ensure_ascii=False))
                       for ln in self.flush())

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
    cap._attach()   # with を使わないスタイルでも有効化
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
    # デフォルト（= -m 指定なし or 既定の式）時だけ skip を付与
    if not selected_expr or selected_expr.strip() == 'not heavy and not gpu and not external':
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
