# codex/agents/proxy/tools/git.py
from __future__ import annotations

import shlex
import subprocess
from typing import Dict, Any, List


class GitTool:
    """
    安全サブセットの git 操作。
    - apply_patch(check_only=True/False): -p1 を基本に、失敗時は -p2, -p0 を自動フォールバック
    - restore_worktree(): 追跡ファイル変更を破棄 + 未追跡のうち keep_dirs は残す
    """
    name = "git"

    def __init__(self, cwd: str, keep_dirs: List[str] | None = None):
        self.cwd = cwd
        self.keep_dirs = keep_dirs or ["codex_reports/"]

    def _run(self, cmd: str) -> subprocess.CompletedProcess:
        return subprocess.run(shlex.split(cmd), cwd=self.cwd, capture_output=True, text=True)

    def run(self, **kwargs) -> Dict[str, Any]:
        act = kwargs.get("action")

        if act == "apply_patch":
            path = kwargs["path"]
            check = bool(kwargs.get("check_only", False))

            # a/a/<file> のようなヘッダに対応するため p-strip をフォールバック
            p_strips = [1, 2, 0]  # 通常は -p1、二重 a/ の場合は -p2、最後に -p0 を試す
            last_err = ""
            for p in p_strips:
                cmd = f"git apply -p{p} {'--check' if check else ''} {shlex.quote(path)}".strip()
                cp = self._run(cmd)
                if cp.returncode == 0:
                    return {"ok": True, "pstrip": p}
                last_err = (cp.stderr or cp.stdout).strip()

            return {"ok": False, "error": last_err or "git apply failed"}

        if act == "restore_worktree":
            # 追跡ファイルのローカル変更を破棄
            cp = self._run("git restore -SW .")
            if cp.returncode != 0:
                return {"ok": False, "error": (cp.stderr or cp.stdout).strip()}

            # 未追跡は keep_dirs を除外してクリーン
            exclude_args = ""
            for d in self.keep_dirs:
                dd = d if d.endswith("/") else d + "/"
                exclude_args += f" -e {dd} -e {dd}**"
            cp = self._run(f"git clean -fd{exclude_args}")
            if cp.returncode != 0:
                return {"ok": False, "error": (cp.stderr or cp.stdout).strip()}
            return {"ok": True}

        return {"ok": False, "error": f"unknown git action: {act}"}
