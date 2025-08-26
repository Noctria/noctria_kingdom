# src/plan_data/__init__.py
"""
Noctria Kingdom — plan_data package

目的:
- package import を軽量に保つ（ここで重い依存/DB/外部I/Oを起こさない）
- それでも便利に使えるように、一部の関数は遅延 import (__getattr__) で公開

使い方の推奨:
- 基本は必要箇所でサブモジュールを明示 import してください:
    from plan_data.trace import new_trace_id
    from plan_data.observability import log_plan_run
- トップレベルから直接取りたい場合も、遅延 import が働きます:
    from plan_data import new_trace_id   # OK（実体は plan_data.trace で定義）
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

__all__ = [
    # lazily exposed symbols (see __getattr__)
    "new_trace_id",
    "get_trace_id",
    "set_trace_id",
    "bind_trace_id",
    # メタ
    "__version__",
]

__version__ = "1.0.0"


# --- Lazy attribute loader ----------------------------------------------------
# ここで重い依存を持つモジュールを直接 import しない。
# アクセスされた時にだけ、該当サブモジュールからシンボルを取り出す。
_lazy_exports = {
    # plan_data.trace.* をトップレベルから使いたい需要が多いため公開
    "new_trace_id": ("plan_data.trace", "new_trace_id"),
    "get_trace_id": ("plan_data.trace", "get_trace_id"),
    "set_trace_id": ("plan_data.trace", "set_trace_id"),
    "bind_trace_id": ("plan_data.trace", "bind_trace_id"),
}


def __getattr__(name: str):
    target = _lazy_exports.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    mod_name, sym = target
    # NOTE: src. 接頭辞不要（sys.path に src 追加済み前提）。
    # CLI 等では src.core.path_config.ensure_import_path() を先に呼んでください。
    mod = importlib.import_module(mod_name)
    return getattr(mod, sym)


def __dir__():
    # 遅延公開分も dir() に見えるように
    return sorted(list(globals().keys()) + list(_lazy_exports.keys()))


# --- Type checkers support ----------------------------------------------------
# mypy/pyright には実体を見せる（実行時には遅延 import が使われる）
if TYPE_CHECKING:
    from plan_data.trace import (  # noqa: F401
        new_trace_id,
        get_trace_id,
        set_trace_id,
        bind_trace_id,
    )
