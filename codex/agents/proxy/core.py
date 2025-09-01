from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Protocol, Optional, Tuple

class Tool(Protocol):
    name: str
    def describe(self) -> str: ...
    def run(self, **kwargs) -> Dict[str, Any]: ...

@dataclass
class Policy:
    # 例: 書き込み禁止パス/拡張子、最大差分サイズ、実行制限秒
    deny_globs: List[str] = field(default_factory=lambda: ["**/.git/**", "**/node_modules/**"])
    max_patch_bytes: int = 256_000
    def allow_path(self, path: str) -> bool:
        # 必要に応じてfnmatchで拒否
        from fnmatch import fnmatch
        for g in self.deny_globs:
            if fnmatch(path, g):
                return False
        return True

@dataclass
class Memory:
    kv: Dict[str, Any] = field(default_factory=dict)
    def get(self, k, default=None): return self.kv.get(k, default)
    def set(self, k, v): self.kv[k] = v

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
        if tool_name not in self.tools:
            return {"ok": False, "error": f"tool '{tool_name}' not found"}
        return self.tools[tool_name].run(**kwargs)

    def run_task(self, task: Task) -> Dict[str, Any]:
        if task.kind == "apply-generated-patches":
            # patches_index.md を読み、.patch を順に dry-run→apply→pytest
            return self._apply_patches_flow(task.payload)
        return {"ok": False, "error": f"unknown task: {task.kind}"}

    def _apply_patches_flow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # 1) パッチ列挙
        idx = self.use("fs", action="read_text", path="codex_reports/patches_index.md")
        if not idx.get("ok"): return idx
        # 2) ファイル一覧抽出（markdownテーブルの1列目リンクを拾うのが簡単）
        import re
        patches = re.findall(r"\|\s*\[([^\]]+)\]\(patches/[^)]+\)", idx["text"])
        results: List[Tuple[str, str]] = []
        for name in patches:
            patch_path = f"codex_reports/patches/{name}"
            # 3) dry-run
            r = self.use("git", action="apply_patch", path=patch_path, check_only=True)
            if not r.get("ok"):
                results.append((name, f"check_failed:{r.get('error')}"))
                continue
            # 4) apply
            r = self.use("git", action="apply_patch", path=patch_path, check_only=False)
            if not r.get("ok"):
                results.append((name, f"apply_failed:{r.get('error')}"))
                continue
            # 5) pytest
            tr = self.use("pytest", args=["-q"])
            status = "passed" if tr.get("ok") and tr.get("failed", 0) == 0 else f"failed:{tr.get('failed')}"
            results.append((name, status))
            # 6) 失敗したら巻き戻し（安全策）
            if "failed" in status:
                self.use("git", action="restore_worktree")
        return {"ok": True, "results": results}
