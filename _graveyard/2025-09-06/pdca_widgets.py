# noctria_gui/routes/pdca_widgets.py
# -*- coding: utf-8 -*-
"""
PDCA ウィジェット群
- GET  /pdca/api/recent-adoptions        : JSON（直近採用タグ×Decision 突き合わせ）
- GET  /pdca/widgets/recent-adoptions    : HTMLフラグメント（レイアウト無しのカード群）
  - 他テンプレから `{% include %}` せずに <iframe> や hx-get（htmx等）で差し込める

依存（あれば利用し、無ければ自前でgitコマンド実行）:
- src/core/git_utils.GitHelper (list_tags を推奨)
- src/core/decision_registry.tail_ledger
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

# 依存は存在しなくても動くように
try:
    from src.core.git_utils import GitHelper  # type: ignore
except Exception:
    GitHelper = None  # type: ignore

try:
    from src.core.decision_registry import tail_ledger  # type: ignore
except Exception:
    tail_ledger = None  # type: ignore

router = APIRouter(prefix="/pdca", tags=["PDCA", "Widgets"])

# <repo_root> 推定（…/noctria_gui/routes/pdca_widgets.py → parents[2] = <repo_root>）
PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------
# Jinja fragment renderer
# ---------------------------
def _render_fragment(request: Request, template: str, **ctx: Any) -> HTMLResponse:
    # app.state.jinja_env があればそれを優先（共通フィルタ利用のため）
    env = getattr(getattr(request, "app", None), "state", None)
    env = getattr(env, "jinja_env", None)
    if env is not None:
        html = env.get_template(template).render(request=request, **ctx)
        return HTMLResponse(html)

    # フォールバック（開発時など）
    from fastapi.templating import Jinja2Templates

    tpl_dir = PROJECT_ROOT / "noctria_gui" / "templates"
    templates = Jinja2Templates(directory=str(tpl_dir))
    return templates.TemplateResponse(template, {"request": request, **ctx})


# ---------------------------
# Decision Registry → tag index
# ---------------------------
def _build_index_by_tag(max_scan: int = 2000) -> Dict[str, Dict[str, str]]:
    """
    Decision Registry を走査して tag -> latest(decision_id, ts_utc, phase)
    extra_json 内の adopt_result.tag または top-level tag を拾う。
    """
    idx: Dict[str, Dict[str, str]] = {}
    if tail_ledger is None:
        return idx

    try:
        rows = tail_ledger(n=max_scan)  # List[dict-like]
    except Exception:
        rows = []

    for r in rows:
        try:
            extra = json.loads(r.get("extra_json") or "{}")
        except Exception:
            extra = {}

        # adopt_result.tag 優先、無ければ extra.tag
        tag = (extra.get("adopt_result") or {}).get("tag") or extra.get("tag")
        if not tag:
            continue

        ts = r.get("ts_utc") or ""
        cur = idx.get(tag)
        if cur is None or ts > (cur.get("ts_utc") or ""):
            idx[tag] = {
                "decision_id": r.get("decision_id") or "",
                "ts_utc": ts,
                "phase": r.get("phase") or "",
            }
    return idx


# ---------------------------
# Git tags 取得（GitHelper優先、無ければgitコマンド）
# ---------------------------
def _normalize_pattern(p: Optional[str]) -> str:
    """
    'veritas-' のような前方一致っぽい指定にはワイルドカードを補う。
    既に *, ?, [ を含むならそのまま使う。
    """
    if not p:
        return "*"
    if any(ch in p for ch in "*?["):
        return p
    # 末尾 * を足して前方一致に
    return p + "*"


def _run_git(cmd: List[str], cwd: Optional[Path] = None) -> str:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or os.getenv("GIT_REPO_DIR") or PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git failed: {' '.join(cmd)}\n{proc.stdout}")
    return proc.stdout


def _list_tags_via_git(pattern: str, limit: int) -> List[Dict[str, Any]]:
    """
    git コマンドでタグを列挙。各タグの指すコミットの %cI, %H, %s を付与して降順。
    """
    try:
        raw = _run_git(["git", "tag", "--list", pattern, "--sort=-creatordate"])
    except Exception:
        raw = _run_git(["git", "tag", "--list", pattern])

    names = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if not names:
        return []

    # 多めに取り出して後でコミット日時で降順に
    candidates = names[: max(limit * 2, limit)]
    out: List[Dict[str, Any]] = []
    for name in candidates:
        try:
            log = _run_git(["git", "log", "-1", "--format=%cI%n%H%n%s", name])
            lines = log.splitlines()
            if len(lines) >= 3:
                out.append(
                    {
                        "name": name,
                        "date": lines[0],  # ISO8601
                        "sha": lines[1],
                        "subject": lines[2],
                        "annotated": False,  # 軽量/注釈はここでは区別しない（必要なら後日拡張）
                    }
                )
        except Exception:
            # 不正参照などはスキップ
            continue
    out.sort(key=lambda r: r["date"], reverse=True)
    return out[:limit]


def _collect(pattern: Optional[str], limit: int) -> List[Dict[str, Any]]:
    """
    Gitタグ（pattern, limit）× Decision Registry index を突き合わせた配列を返す。
    """
    patt = _normalize_pattern(pattern)
    tags: List[Dict[str, Any]] = []

    if GitHelper is not None and hasattr(GitHelper, "list_tags"):
        # GitHelper 実装がある場合はそちらを優先
        try:
            gh = GitHelper()
            tags = gh.list_tags(pattern=patt, limit=limit)  # 期待: [{name,date,sha,subject?,annotated?}, ...]
        except Exception:
            tags = []
    else:
        # フォールバック: 直接 git コマンドで列挙
        try:
            tags = _list_tags_via_git(patt, limit)
        except Exception:
            tags = []

    # Decision index を構築
    idx = _build_index_by_tag()

    # 出力に decision 情報を重畳
    out: List[Dict[str, Any]] = []
    for t in tags:
        name = t.get("name", "")
        out.append(
            {
                "tag": name,
                "date": t.get("date", ""),
                "sha": t.get("sha", ""),
                "annotated": bool(t.get("annotated", False)),
                "subject": t.get("subject", ""),
                "decision": idx.get(name) or {},  # {decision_id, ts_utc, phase}
            }
        )
    return out


# ---------------------------
# Routes
# ---------------------------
@router.get("/api/recent-adoptions")
async def api_recent_adoptions(
    pattern: Optional[str] = Query("veritas-"),
    limit: int = Query(12, ge=1, le=100),
):
    """
    直近採用（採用＝タグ付けを便宜上そう呼ぶ）の一覧を JSON で返す。
    Git タグの取得に失敗した場合も形は保ち、items=[] を返す。
    """
    data = _collect(pattern, limit)
    return JSONResponse({"pattern": _normalize_pattern(pattern), "limit": limit, "items": data})


@router.get("/widgets/recent-adoptions", response_class=HTMLResponse)
async def widget_recent_adoptions(
    request: Request,
    pattern: Optional[str] = Query("veritas-"),
    limit: int = Query(12, ge=1, le=100),
    title: Optional[str] = Query("🧩 直近採用タグ"),
    cols: int = Query(3, ge=1, le=6, description="カードの横並び数（簡易CSSグリッド）"),
):
    """
    直近採用タグのカード群をフラグメントHTMLで返す。
    呼び出し側は <iframe> もしくは htmx などでこの HTML を差し込む。
    """
    items = _collect(pattern, limit)
    return _render_fragment(
        request,
        "widgets/recent_adoptions_fragment.html",
        title=title,
        items=items,
        pattern=_normalize_pattern(pattern),
        limit=limit,
        cols=cols,
    )
