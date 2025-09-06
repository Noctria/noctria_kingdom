# codex/agents/proxy/core.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Protocol, Optional, Tuple


class Tool(Protocol):
    name: str

    def describe(self) -> str:
        ...

    def run(self, **kwargs) -> Dict[str, Any]:
        ...


@dataclass
class Policy:
    """
    代理AIの行動ガード。必要に応じて強化していく想定。
    """
    deny_globs: List[str] = field(default_factory=lambda: ["**/.git/**", "**/node_modules/**"])
    max_patch_bytes: int = 256_000

    def allow_path(self, path: str) -> bool:
        from fnmatch import fnmatch
        for g in self.deny_globs:
            if fnmatch(path, g):
                return False
        return True


@dataclass
class Memory:
    kv: Dict[str, Any] = field(default_factory=dict)

    def get(self, k, default=None):
        return self.kv.get(k, default)

    def set(self, k, v):
        self.kv[k] = v


@dataclass
class Task:
    kind: str
    payload: Dict[str, Any]


@dataclass
class Agent:
    tools: Dict[str, Tool]
    policy: Policy
    memory: Memory = field(default_factory=Memory)

    def use(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        tool = self.tools.get(tool_name)
        if tool is None:
            return {"ok": False, "error": f"tool '{tool_name}' not found"}
        return tool.run(**kwargs)

    def run_task(self, task: Task) -> Dict[str, Any]:
        if task.kind == "apply-generated-patches":
            return self._apply_patches_flow(task.payload)
        return {"ok": False, "error": f"unknown task: {task.kind}"}

    # --- 内部フロー ---

    def _apply_patches_flow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        patches_index.md を読み、記載の .patch を順に:
          1) git apply --check (dry-run)
          2) git apply
          3) pytest 実行（rc==5 は no-tests として成功扱い）
          失敗時は作業ツリーをロールバック。
        """
        # 1) 索引の読み込み
        idx = self.use("fs", action="read_text", path="codex_reports/patches_index.md")
        if not idx.get("ok"):
            return {"ok": False, "error": f"cannot read patches_index.md: {idx.get('error')}"}

        text = idx.get("text", "")
        patches = self._extract_patch_names_from_index(text)
        if not patches:
            return {"ok": True, "results": []}

        results: List[Tuple[str, str]] = []
        for name in patches:
            patch_path = f"codex_reports/patches/{name}"

            # 2) dry-run
            r = self.use("git", action="apply_patch", path=patch_path, check_only=True)
            if not r.get("ok"):
                results.append((name, f"check_failed:{r.get('error')}"))
                continue

            # 3) apply
            r = self.use("git", action="apply_patch", path=patch_path, check_only=False)
            if not r.get("ok"):
                results.append((name, f"apply_failed:{r.get('error')}"))
                continue

            # 4) pytest
            tr = self.use("pytest", args=["-q"])
            rc = int(tr.get("returncode", 0) or 0)
            failed = int(tr.get("failed", 0) or 0)
            ok = bool(tr.get("ok", False))

            if rc == 5 and failed == 0:
                status = "no-tests"  # テスト未収集は成功扱い（適用を保持）
            elif ok and failed == 0:
                status = "passed"
            else:
                status = f"failed:{failed}"

            results.append((name, status))

            # 5) 失敗時のみロールバック（安全側）
            if status.startswith("failed:"):
                self.use("git", action="restore_worktree")

        return {"ok": True, "results": results}

    @staticmethod
    def _extract_patch_names_from_index(md_text: str) -> List[str]:
        """
        patches_index.md のテーブル（| [FILENAME](patches/...) | ... |）から
        左列リンクの “FILENAME” を抽出して返す。
        """
        import re
        names = re.findall(r"\|\s*\[([^\]]+)\]\(patches/[^)]+\)", md_text)
        # 重複を避けるため順序維持で一意化
        seen = set()
        uniq: List[str] = []
        for n in names:
            if n not in seen:
                seen.add(n)
                uniq.append(n)
        return uniq
