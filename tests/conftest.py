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
    Alerts を stdout / logging の両面からキャプチャするフィクスチャ。
      - NOCTRIA_OBS_MODE=stdout を強制
      - ルート & noctria.observability ロガーの INFO 以上を捕捉
      - stdout に出た 1行JSON を dict にデコードして格納（tests側で a.get("kind") が使える）

    使い方（どちらでもOK）:
        def test_xxx(capture_alerts):
            with capture_alerts as cap:
                ... 被テスト処理 ...
                assert cap.contains("QUALITY.")

            ... 被テスト処理 ...
            kinds = [a.get("kind") for a in capture_alerts if isinstance(a, dict)]
            assert any(k and k.startswith("NOCTUS") for k in kinds)
    """
    # 1) stdout 観測を強制
    monkeypatch.setenv("NOCTRIA_OBS_MODE", "stdout")

    # 2) logging キャプチャ用ハンドラ
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
            # JSON なら dict で格納（テストで .get("kind") を直接使える）
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
            # メッセージのみ（JSON行をそのまま受け取る）
            self._handler.setFormatter(logging.Formatter("%(message)s"))
            self._root_logger = logging.getLogger()                 # ルート
            self._obs_logger = logging.getLogger("noctria.observability")  # 直接
            self._prev_level: int | None = None
            self._attached = False

        def _attach(self):
            if not self._attached:
                self._root_logger.addHandler(self._handler)
                self._obs_logger.addHandler(self._handler)
                # INFO 以上を拾う（emit_alert が INFO/WARNING どちらでも対応）
                self._prev_level = self._root_logger.level
                if self._root_logger.level in (logging.NOTSET, logging.ERROR, logging.CRITICAL):
                    self._root_logger.setLevel(logging.INFO)
                # 子→親へも流す
                self._obs_logger.propagate = True
                self._attached = True

        def _detach(self):
            if self._attached:
                try:
                    self._root_logger.removeHandler(self._handler)
                    self._obs_logger.removeHandler(self._handler)
                    if self._prev_level is not None:
                        self._root_logger.setLevel(self._prev_level)
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
                    # stdout 行も JSON なら dict で格納
                    try:
                        obj = _json.loads(ln)
                        if isinstance(obj, dict):
                            self._lines.append(obj)
                            continue
                    except Exception:
                        pass
                    self._lines.append(ln)
            # 重複除去（順序保持）。dict は JSON 文字列化してキー化
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
            # 文字列には部分一致、dict は値のどこかに含まれるかを簡易チェック
            for ln in self.flush():
                if isinstance(ln, str) and substr in ln:
                    return True
                if isinstance(ln, dict):
                    try:
                        if substr in _json.dumps(ln, ensure_ascii=False):
                            return True
                    except Exception:
                        pass
            return False

        # イテレータ/len/呼び出し可能（lines取得）
        def __iter__(self):
            return iter(self.flush())

        def __len__(self):
            return len(self.flush())

        def __call__(self) -> t.List[t.Union[str, dict]]:
            return self.flush()

        # コンテキスト管理
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
