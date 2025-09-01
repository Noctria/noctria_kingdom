from __future__ import annotations
import subprocess, shlex
from typing import Dict, Any

class GitTool:
    name = "git"
    def __init__(self, cwd: str):
        self.cwd = cwd

    def _run(self, cmd: str) -> subprocess.CompletedProcess:
        return subprocess.run(shlex.split(cmd), cwd=self.cwd, capture_output=True, text=True)

    def run(self, **kwargs) -> Dict[str, Any]:
        act = kwargs.get("action")
        if act == "apply_patch":
            path = kwargs["path"]; check = kwargs.get("check_only", False)
            cmd = f"git apply {'--check' if check else ''} {shlex.quote(path)}".strip()
            cp = self._run(cmd)
            if cp.returncode != 0:
                return {"ok": False, "error": cp.stderr.strip()}
            return {"ok": True}
        if act == "restore_worktree":
            # 変更捨ててクリーンに戻す（安全側）
            for cmd in ["git restore -SW .", "git clean -fd"]:
                cp = self._run(cmd)
                if cp.returncode != 0:
                    return {"ok": False, "error": cp.stderr.strip()}
            return {"ok": True}
        return {"ok": False, "error": f"unknown git action: {act}"}
