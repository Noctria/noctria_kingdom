# -------------------------------------------------------------------
# File: src/core/git_utils.py
# -------------------------------------------------------------------
# -*- coding: utf-8 -*-
"""
Git 操作用の簡易ヘルパ

機能:
- add_commit_push(paths, message): 変更を追加→コミット→リベース→プッシュ（非fast-forward時は自動リトライ）
- create_tag_and_push(prefix="veritas", annotation=""): タグ作成→プッシュ
- list_tags(pattern=None, limit=200): 作成日時の新しい順でタグ一覧を取得
- get_tag_detail(tag): 単一タグの詳細（sha / date / message / annotated）

環境変数:
- GIT_REPO_DIR: リポジトリのルート（未指定なら CWD）
- GIT_REMOTE : 既定 "origin"
- GIT_BRANCH : 既定 "main"
- GIT_USER_NAME / GIT_USER_EMAIL : 指定時は `git config` を上書き設定
"""

from __future__ import annotations

import os
import subprocess
from typing import List, Optional, Dict


def _run(cmd: List[str], cwd: Optional[str] = None, check: bool = True) -> str:
    """サブプロセスを実行し、stdout を返す。check=True なら非0終了時に例外。"""
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"cmd failed: {' '.join(cmd)}\n{proc.stdout}")
    return proc.stdout


class GitHelper:
    def __init__(self, repo_dir: Optional[str] = None):
        self.repo_dir = repo_dir or os.getenv("GIT_REPO_DIR") or os.getcwd()
        self.remote = os.getenv("GIT_REMOTE", "origin")
        self.branch = os.getenv("GIT_BRANCH", "main")

        # 任意のユーザー設定（指定時のみ反映）
        user = os.getenv("GIT_USER_NAME")
        email = os.getenv("GIT_USER_EMAIL")
        if user:
            _run(["git", "config", "user.name", user], cwd=self.repo_dir, check=False)
        if email:
            _run(["git", "config", "user.email", email], cwd=self.repo_dir, check=False)

        # リポジトリ検証（最小限）
        _run(["git", "rev-parse", "--git-dir"], cwd=self.repo_dir)

    # ------------------------------------------------------------------
    # 基本ユーティリティ
    # ------------------------------------------------------------------
    def fetch(self) -> None:
        _run(["git", "fetch", self.remote, "--tags"], cwd=self.repo_dir, check=False)

    def pull_rebase(self) -> None:
        _run(["git", "pull", "--rebase", self.remote, self.branch], cwd=self.repo_dir, check=False)

    def push_with_retry(self) -> None:
        """
        非fast-forwardなどで push が拒否された場合は fetch+rebase して 1 回だけ再試行。
        それでも失敗したら例外を投げる。
        """
        out = _run(["git", "push", self.remote, self.branch], cwd=self.repo_dir, check=False)
        if "rejected" in out or "non-fast-forward" in out:
            # 取り込み → 再push
            self.fetch()
            self.pull_rebase()
            _run(["git", "push", self.remote, self.branch], cwd=self.repo_dir, check=True)

    # ------------------------------------------------------------------
    # 変更コミット＆プッシュ
    # ------------------------------------------------------------------
    def add_commit_push(self, paths: List[str], message: str) -> None:
        """paths を add → commit（変更なしでもOK）→ rebase → push（必要に応じてリトライ）"""
        if not paths:
            return
        _run(["git", "add"] + paths, cwd=self.repo_dir)
        # 変更がない場合もあるので commit は check=False
        _run(["git", "commit", "-m", message], cwd=self.repo_dir, check=False)
        self.pull_rebase()
        self.push_with_retry()

    # ------------------------------------------------------------------
    # タグ作成＆プッシュ
    # ------------------------------------------------------------------
    def create_tag_and_push(self, prefix: str = "veritas", annotation: str = "") -> str:
        """
        タグ名: {prefix}-YYYYMMDD-HHMMSS（UTC）
        注釈付きタグ(-a)で作成し、push。annotation が空なら lightweight。
        """
        import datetime

        tag = f"{prefix}-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        if annotation:
            _run(["git", "tag", "-a", tag, "-m", annotation], cwd=self.repo_dir)
        else:
            _run(["git", "tag", tag], cwd=self.repo_dir)
        # タグ単体を push（軽量/注釈付きどちらでもOK）
        _run(["git", "push", self.remote, tag], cwd=self.repo_dir)
        return tag

    # ------------------------------------------------------------------
    # タグ列挙・詳細
    # ------------------------------------------------------------------
    def list_tags(self, pattern: Optional[str] = None, limit: int = 200) -> List[Dict[str, str]]:
        """
        refs/tags を作成日時の新しい順に取得。
        返却: [{"name": str, "date": iso8601, "sha": short, "annotated": "true"/"false"}]
        """
        # creatordate は軽量/注釈付きの双方で作成日時を表現してくれる
        fmt = "%(refname:short)|%(creatordate:iso8601)|%(objectname:short)|%(taggername)"
        out = _run(
            ["git", "for-each-ref", "--sort=-creatordate", f"--format={fmt}", "refs/tags"],
            cwd=self.repo_dir,
            check=False,
        ).strip()
        if not out:
            return []
        tags: List[Dict[str, str]] = []
        for line in out.splitlines():
            if "|" not in line:
                continue
            name, date, sha, tagger = (part.strip() for part in line.split("|", 4))
            if pattern and pattern not in name:
                continue
            annotated = "true" if tagger else "false"
            tags.append({"name": name, "date": date, "sha": sha, "annotated": annotated})
            if len(tags) >= max(1, limit):
                break
        return tags

    def get_tag_detail(self, tag: str) -> Dict[str, str]:
        """
        タグ1件の詳細（message/commit/date/annotated）
        - message は `git tag -n99 --list` の結果を返す（注釈なしの場合は空）
        """
        # 注釈の有無
        tagger = _run(
            ["git", "for-each-ref", f"--format=%(taggername)", f"refs/tags/{tag}"],
            cwd=self.repo_dir,
            check=False,
        ).strip()
        annotated = "true" if tagger else "false"

        # メッセージ（注釈なしなら空）
        msg = _run(["git", "tag", "-n99", "--list", tag], cwd=self.repo_dir, check=False)

        sha = _run(["git", "rev-list", "-n", "1", tag], cwd=self.repo_dir, check=False).strip()
        # 作成日時（コミット/タグの author 日付）
        date = _run(["git", "log", "-1", "--format=%aI", tag], cwd=self.repo_dir, check=False).strip()

        return {"name": tag, "sha": sha, "date": date, "message": msg, "annotated": annotated}
