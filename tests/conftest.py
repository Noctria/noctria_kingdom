# tests/conftest.py
from __future__ import annotations

# --- Import path bootstrap ---------------------------------------------------
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
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
    Alerts を stdout / logging の両面からキャプチャするフィクスチャ。
    - NOCTRIA_OBS_MODE=stdout を強制
    - ルート & noctria.observability のログを INFO+ で捕捉
    - stdout 行は JSON なら dict 化して格納
    - __iter__/len/() で配列アクセス
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
            self._handler.setFormatter(logging.Formatter("%(message)s"))
            self._root_logger = logging.getLogger()
            self._obs_logger = logging.getLogger("noctria.observability")
            self._prev_level: int | None = None
            self._attached = False

        def _attach(self):
            if self._attached:
                return
            self._root_logger.addHandler(self._handler)
            self._obs_logger.addHandler(self._handler)
            self._prev_level = self._root_logger.level
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
                if self._prev_level is not None:
                    self._root_logger.setLevel(self._prev_level)
            finally:
                self._attached = False

        def flush(self) -> t.List[t.Union[str, dict]]:
            out = capsys.readouterr().out
            if out:
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

            # 重複除去（dictはJSON文字列化してキー化）
            seen: set[str] = set()
            uniq: list[t.Union[str, dict]] = []
            for ln in self._lines:
                key = _json.dumps(ln, ensure_ascii=False, sort_keys=True) if isinstance(ln, dict) else ln
                if key not in seen:
                    uniq.append(ln)
                    seen.add(key)
            self._lines = uniq
            return list(self._lines)

        # 便利API
        def contains(self, substr: str) -> bool:
            return any((substr in ln) if isinstance(ln, str) else (substr in _json.dumps(ln, ensure_ascii=False))
                       for ln in self.flush())

        # イテレータ/len/呼び出し可能
        def __iter__(self):
            return iter(self.flush())

        def __len__(self):
            return len(self.flush())

        def __call__(self) -> t.List[t.Union[str, dict]]:
            return self.flush()

        # コンテキスト
        def __enter__(self):
            capsys.readouterr()
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
    cap._attach()
    try:
        yield cap
    finally:
        cap._detach()
