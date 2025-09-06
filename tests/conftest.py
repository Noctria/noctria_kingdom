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
    Alerts を stdout / logging の両面からキャプチャする万能フィクスチャ。

    仕様:
      - NOCTRIA_OBS_MODE=stdout を強制（観測系がstdout向けに動く想定）
      - ルートロガー & noctria.observability に INFO+ のハンドラを装着してログも回収
      - stdout とログをマージし、JSON行は dict にパースして保持
      - list ライクAPI: 反復/len/添字アクセス（負の添字もOK）
    """
    # 1) stdout観測を強制
    monkeypatch.setenv("NOCTRIA_OBS_MODE", "stdout")

    # 2) loggingキャプチャ用ハンドラ（INFO以上）
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
            # JSON なら dict として保存（.get が使える）
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
            self._handler.setFormatter(logging.Formatter("%(message)s"))

            # ルート & 観測系ロガーの両方に付ける
            self._root_logger = logging.getLogger()
            self._obs_logger = logging.getLogger("noctria.observability")

            self._prev_root_level: int | None = None
            self._prev_obs_level: int | None = None
            self._attached = False

        def _attach(self):
            if self._attached:
                return
            self._root_logger.addHandler(self._handler)
            self._obs_logger.addHandler(self._handler)

            # INFO 以上を確実に拾う
            self._prev_root_level = self._root_logger.level
            if self._root_logger.level in (logging.NOTSET, logging.WARNING + 10, logging.ERROR, logging.CRITICAL):
                self._root_logger.setLevel(logging.INFO)

            self._prev_obs_level = self._obs_logger.level
            if self._obs_logger.level in (logging.NOTSET, logging.WARNING + 10, logging.ERROR, logging.CRITICAL):
                self._obs_logger.setLevel(logging.INFO)

            # 親へ伝播も許可
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
                if self._prev_obs_level is not None:
                    self._obs_logger.setLevel(self._prev_obs_level)
            finally:
                self._attached = False

        def _ingest_stdout(self):
            out = capsys.readouterr().out
            if not out:
                return
            for ln in out.splitlines():
                ln = ln.rstrip()
                if not ln:
                    continue
                # JSONならdict化
                try:
                    obj = _json.loads(ln)
                    if isinstance(obj, dict):
                        self._lines.append(obj)
                        continue
                except Exception:
                    pass
                self._lines.append(ln)

        def flush(self) -> t.List[t.Union[str, dict]]:
            """stdout を flush し、ログとマージして重複除去した配列を返す"""
            self._ingest_stdout()

            # 重複除去（順序保持）
            seen: set[str] = set()
            uniq: list[t.Union[str, dict]] = []
            for ln in self._lines:
                key = _json.dumps(ln, ensure_ascii=False, sort_keys=True) if isinstance(ln, dict) else str(ln)
                if key not in seen:
                    uniq.append(ln)
                    seen.add(key)
            self._lines = uniq
            return list(self._lines)

        # 便利API --------------------------------------------------------------
        def contains(self, substr: str) -> bool:
            return any(isinstance(x, str) and substr in x for x in self.flush())

        # list-like: 反復/長さ/添字（負の添字OK）
        def __iter__(self):
            return iter(self.flush())

        def __len__(self):
            return len(self.flush())

        def __getitem__(self, idx: int | slice):
            data = self.flush()
            return data[idx]

        def __call__(self) -> t.List[t.Union[str, dict]]:
            return self.flush()

        # コンテキスト管理 -----------------------------------------------------
        def __enter__(self):
            capsys.readouterr()  # 前残りクリア
            self._lines.clear()
            self._attach()
            return self

        def __exit__(self, exc_type, exc, tb):
            try:
                self.flush()
            finally:
                self._detach()
            return False  # 例外はpytestへ

    cap = Capture()
    cap._attach()  # with を使わないスタイルでも即時有効化
    try:
        yield cap
    finally:
        cap._detach()
