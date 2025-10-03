# src/core/envload.py
# [NOCTRIA_CORE_REQUIRED]
from __future__ import annotations

from dotenv import find_dotenv, load_dotenv


def load_noctria_env() -> None:
    """
    どのカレントディレクトリからでも、リポジトリ直下の .env を読み、
    ついで .env.local / .env.secret / noctria_gui/.env で上書きする。
    """
    root = find_dotenv(".env", usecwd=True, raise_error_if_not_found=False)
    if root:
        load_dotenv(root)
    for extra in (".env.local", ".env.secret", "noctria_gui/.env"):
        p = find_dotenv(extra, usecwd=True, raise_error_if_not_found=False)
        if p:
            load_dotenv(p, override=True)
