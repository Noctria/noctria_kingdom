from __future__ import annotations
from pathlib import Path
from typing import Dict, Any

class FSTool:
    name = "fs"
    def __init__(self, root: Path):
        self.root = root

    def _abs(self, rel: str) -> Path:
        p = (self.root / rel).resolve()
        if not str(p).startswith(str(self.root.resolve())):
            raise ValueError("path escapes project root")
        return p

    def run(self, **kwargs) -> Dict[str, Any]:
        act = kwargs.get("action")
        if act == "read_text":
            p = self._abs(kwargs["path"])
            if not p.exists(): return {"ok": False, "error": "not found"}
            return {"ok": True, "text": p.read_text(encoding="utf-8")}
        return {"ok": False, "error": f"unknown fs action: {act}"}
