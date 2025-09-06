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
import pytest


@pytest.fixture
def capture_alerts(monkeypatch, capsys):
    """
    Alerts を stdout / logging の両面からキャプチャするフィクスチャ。

    - NOCTRIA_OBS_MODE=stdout を強制
    - ルートロガーに WARNING+ のハンドラを装着（logging出力も拾う）
    - stdout/ログをマージし、重複除去した「行配列」を list ライクに提供
    - __getitem__ を実装しているので capture_alerts[-1] などの添字が使える
    """
    # 1) stdout観測を強制
    monkeypatch.setenv("NOCTRIA_OBS_MODE", "stdout")

    # 2) loggingキャプチャ用ハンドラ
    class _ListHandler(logging.Handler):
        def __init__(self, sink: t.List[str]):
            super().__init__(level=logging.WARNING)
            self._sink = sink

        def emit(self, record: logging.LogRecord) -> None:
            try:
                msg = self.format(record)
            except Exception:
                msg = record.getMessage()
            if msg:
                self._sink.append(str(msg))

    class Capture:
        def __init__(self):
            self._lines: t.List[str] = []
            self._handler = _ListHandler(self._lines)
            self._handler.setFormatter(
                logging.Formatter("%(levelname)s:%(name)s:%(message)s")
            )
            self._root_logger = logging.getLogger()  # ルートに付ける（局所loggerでも拾える）
            self._prev_level: int | None = None
            self._attached = False

        def _attach(self):
            if not self._attached:
                self._root_logger.addHandler(self._handler)
                # 低すぎると拾えないので WARNING 以上にそろえる
                self._prev_level = self._root_logger.level
                if (
                    self._root_logger.level > logging.WARNING
                    or self._root_logger.level == logging.NOTSET
                ):
                    self._root_logger.setLevel(logging.WARNING)
                self._attached = True

        def _detach(self):
            if self._attached:
                try:
                    self._root_logger.removeHandler(self._handler)
                    if self._prev_level is not None:
                        self._root_logger.setLevel(self._prev_level)
                finally:
                    self._attached = False

        def flush(self) -> t.List[str]:
            """stdout を flush し、ログとマージして重複除去した行配列を返す"""
            out = capsys.readouterr().out
            if out:
                for ln in out.splitlines():
                    ln = ln.rstrip()
                    if ln:
                        self._lines.append(ln)
            # 重複除去（順序保持）
            seen: set[str] = set()
            uniq: list[str] = []
            for ln in self._lines:
                if ln not in seen:
                    uniq.append(ln)
                    seen.add(ln)
            self._lines = uniq
            return list(self._lines)

        # 便利API --------------------------------------------------------------
        def contains(self, substr: str) -> bool:
            return any(substr in ln for ln in self.flush())

        # list-like: 反復/長さ/添字 --------------------------------------------
        def __iter__(self):
            return iter(self.flush())

        def __len__(self):
            return len(self.flush())

        def __getitem__(self, idx: int | slice):
            data = self.flush()
            return data[idx]

        def __call__(self) -> t.List[str]:
            return self.flush()

        # コンテキスト管理 -----------------------------------------------------
        def __enter__(self):
            # 前残りを捨ててクリーン開始
            capsys.readouterr()
            self._lines.clear()
            self._attach()
            return self

        def __exit__(self, exc_type, exc, tb):
            try:
                self.flush()
            finally:
                self._detach()
            # 例外はpytestにそのまま流す
            return False

    cap = Capture()
    # with を使わないスタイルでも即時有効化
    cap._attach()
    try:
        yield cap
    finally:
        cap._detach()
