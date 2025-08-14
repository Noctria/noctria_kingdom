# noctria_gui/routes/pdca_routes.py
#!/usr/bin/env python3
# coding: utf-8

"""
📊 /pdca-dashboard - PDCAダッシュボードの画面表示ルート
- クエリパラメータからフィルタを受け取り、テンプレートに渡す
- いまはダミーデータ、将来は DB / ログを集計して表示
- テンプレートディレクトリは path_config 不在でも安全にフォールバック

補足:
- このファイルは /pdca-dashboard の最小ビューを提供します。
  既存の /pdca/summary（統計/CSV/API/再評価トリガ等）が別ルーターにある場合は共存可能です。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Request, Query, Body, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# ========================================
# 📁 プロジェクトパス解決（フォールバック込み）
# ========================================
_THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = _THIS_FILE.parents[2]  # <repo_root>

# ========================================
# 📁 テンプレートディレクトリ解決（安全フォールバック）
# ========================================
def _resolve_templates_dir() -> Path:
    """
    テンプレートディレクトリの解決を行う。
    - 優先: src.core.path_config.NOCTRIA_GUI_TEMPLATES_DIR
    - 次点: core.path_config.NOCTRIA_GUI_TEMPLATES_DIR（古いimport形）
    - 最後: このファイルの 2 つ上(noctria_gui/) 配下の templates/
    """
    # 1) src.core.path_config（推奨）
    try:
        from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR as _TPL  # type: ignore
        p = Path(str(_TPL))
        if p.exists():
            return p
    except Exception:
        pass

    # 2) core.path_config（互換）
    try:
        from core.path_config import NOCTRIA_GUI_TEMPLATES_DIR as _TPL  # type: ignore
        p = Path(str(_TPL))
        if p.exists():
            return p
    except Exception:
        pass

    # 3) フォールバック: <repo_root>/noctria_gui/templates
    return _THIS_FILE.parents[1] / "templates"


_TEMPLATES_DIR = _resolve_templates_dir()
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

# ========================================
# 📁 PDCAログディレクトリ解決（安全フォールバック）
# ========================================
def _resolve_pdca_dir() -> Path:
    """
    PDCAサマリーが読むログの標準出力先を解決。
    - 優先: src.core.path_config.PDCA_LOG_DIR
    - 最後: <repo_root>/data/pdca_logs/veritas_orders
    """
    try:
        from src.core.path_config import PDCA_LOG_DIR as _P  # type: ignore
        p = Path(str(_P))
        p.mkdir(parents=True, exist_ok=True)
        return p
    except Exception:
        p = PROJECT_ROOT / "data" / "pdca_logs" / "veritas_orders"
        p.mkdir(parents=True, exist_ok=True)
        return p


_PDCA_DIR = _resolve_pdca_dir()

# （任意）ポリシースナップショットを取れれば添付したい
def _get_policy_snapshot() -> Dict[str, Any]:
    try:
        from src.core.policy_engine import get_snapshot  # type: ignore
        return dict(get_snapshot())
    except Exception:
        return {}

# ========================================
# ⚙️ ルーター設定
# ========================================
router = APIRouter(
    prefix="/pdca-dashboard",
    tags=["PDCA"]
)

# ========================================
# 🔎 フィルタ抽出ユーティリティ
# ========================================
def _parse_date(value: Optional[str]) -> Optional[str]:
    """YYYY-MM-DD の簡易検証。形式不正は None を返す。"""
    if not value:
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        return None


def _extract_filters(request: Request) -> Dict[str, Any]:
    qp = request.query_params
    filters: Dict[str, Any] = {
        "strategy": (qp.get("strategy") or "").strip(),
        # 拡張用
        "symbol": (qp.get("symbol") or "").strip(),
        "date_from": _parse_date(qp.get("date_from")),
        "date_to": _parse_date(qp.get("date_to")),
        # 数値系（UI入力の生文字列を保持しつつテンプレへ渡す）
        "winrate_diff_min": qp.get("winrate_diff_min"),
        "maxdd_diff_max": qp.get("maxdd_diff_max"),
        "search": qp.get("search"),
    }
    return filters

# ========================================
# 🔍 ダッシュボード表示ルート
# ========================================
@router.get("/", response_class=HTMLResponse)
async def show_pdca_dashboard(request: Request):
    """
    PDCAダッシュボードのメインビュー。
    クエリパラメータからフィルターを取得し、テンプレートに渡す。
    """
    tpl = _TEMPLATES_DIR / "pdca_dashboard.html"
    if not tpl.exists():
        # テンプレート未配置時の分かりやすいエラー
        return HTMLResponse(
            content=(
                "<h3>pdca_dashboard.html が見つかりません。</h3>"
                f"<p>探索ディレクトリ: {_TEMPLATES_DIR}</p>"
                "<p>noctria_gui/templates/pdca_dashboard.html を配置してください。</p>"
            ),
            status_code=500,
        )

    filters = _extract_filters(request)

    # 📦 PDCAデータ取得（現時点ではダミー）
    # 将来: data/pdca_logs/ 配下CSV/JSON or DBからの集計結果をここへ
    pdca_data: List[Dict[str, Any]] = []

    return templates.TemplateResponse(
        "pdca_dashboard.html",
        {
            "request": request,
            "filters": filters,
            "pdca_logs": pdca_data,
        },
    )

# ========================================
# 🩺 ヘルスチェック/軽量データAPI
# ========================================
@router.get("/health", response_class=JSONResponse)
async def pdca_dashboard_health():
    return JSONResponse(
        {
            "ok": True,
            "templates_dir": str(_TEMPLATES_DIR),
            "template_exists": (_TEMPLATES_DIR / "pdca_dashboard.html").exists(),
            "pdca_dir": str(_PDCA_DIR),
            "message": "pdca-dashboard router is ready",
        }
    )

# =============================================================================
# 📈 直近ログの軽量API（このルーターの中で使えるように安全実装）
# =============================================================================
def _read_logs_dataframe():
    """
    data/pdca_logs/veritas_orders/rechecks_*.csv を読み込んで連結。
    - pandas が無ければ空DFを返す。
    - ファイルが多い場合に備え、更新日時の新しい順に最大 60 ファイルまで。
    """
    try:
        import pandas as pd  # type: ignore
    except Exception:
        class _Dummy:
            @property
            def empty(self): return True
            def __getattr__(self, _): return self
            def copy(self): return self
            def sort_values(self, *_, **__): return self
            def head(self, *_): return self
            def to_dict(self, *_, **__): return {}
            def __getitem__(self, _): return self
            def astype(self, *_ , **__): return self
        return _Dummy()

    files = sorted(_PDCA_DIR.glob("rechecks_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    files = files[:60]  # 上限
    if not files:
        return pd.DataFrame()

    frames = []
    for fp in files:
        try:
            df = pd.read_csv(fp)
            df["__source_file"] = str(fp.name)
            # evaluated_at があれば日付として扱えるように（失敗してもOK）
            if "evaluated_at" in df.columns:
                try:
                    df["evaluated_at"] = pd.to_datetime(df["evaluated_at"], errors="coerce")
                except Exception:
                    pass
            frames.append(df)
        except Exception:
            # 壊れたCSVはスキップ
            continue

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, ignore_index=True)
    return out


@router.get("/api/recent", response_model=Dict[str, Any])
def api_recent(limit: int = Query(20, ge=1, le=100)):
    """
    直近の評価を N 件だけ返す（表表示用の軽量API）
    """
    df = _read_logs_dataframe()
    try:
        empty = df.empty  # pandas が無い場合のダミーにも対応
    except Exception:
        empty = True

    if empty:
        return {"rows": []}

    cols = [
        "evaluated_at", "strategy", "tag",
        "winrate_old", "winrate_new", "winrate_diff",
        "maxdd_old", "maxdd_new", "maxdd_diff",
        "trades_old", "trades_new", "notes",
    ]
    # 欠損列を埋める
    for c in cols:
        if c not in getattr(df, "columns", []):
            try:
                df[c] = None
            except Exception:
                pass

    try:
        dff = df.sort_values("evaluated_at", ascending=False).head(limit).copy()
        dff["evaluated_at"] = dff["evaluated_at"].astype(str)
        rows = dff[cols].to_dict(orient="records")
    except Exception:
        rows = []

    return {"rows": rows}


@router.get("/api/strategy_detail", response_model=Dict[str, Any])
def api_strategy_detail(
    strategy: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=500)
):
    """
    指定戦略の履歴詳細（最新 limit 件）
    """
    df = _read_logs_dataframe()
    try:
        empty = df.empty
    except Exception:
        empty = True

    if empty:
        return {"strategy": strategy, "rows": []}

    try:
        dff = df[df["strategy"].astype(str) == strategy].copy()
    except Exception:
        dff = None

    if dff is None or getattr(dff, "empty", True):
        return {"strategy": strategy, "rows": []}

    cols = [
        "evaluated_at", "strategy", "tag",
        "winrate_old", "winrate_new", "winrate_diff",
        "maxdd_old", "maxdd_new", "maxdd_diff",
        "trades_old", "trades_new", "notes", "__source_file",
    ]
    for c in cols:
        if c not in getattr(dff, "columns", []):
            try:
                dff[c] = None
            except Exception:
                pass

    try:
        dff = dff.sort_values("evaluated_at", descending=False)  # 保険: 古→新に揃えたい時は ascending=True
    except Exception:
        pass
    try:
        dff = dff.sort_values("evaluated_at", ascending=False).head(limit)
        dff["evaluated_at"] = dff["evaluated_at"].astype(str)
        rows = dff[cols].to_dict(orient="records")
    except Exception:
        rows = []

    return {"strategy": strategy, "rows": rows}

# =============================================================================
# ✅ Act(採用) API — 決裁台帳連携（decision_id 自動発行 / イベント記録）
# =============================================================================
class ActBody(BaseModel):
    strategy: str
    reason: str | None = None
    decision_id: str | None = None
    dry_run: bool = False


@router.post("/act", response_model=Dict[str, Any])
def pdca_act(body: ActBody = Body(...)):
    """
    戦略を正式採用（veritas_generated -> strategies/adopted）
    - decision_id 未指定時: 決裁発行(kind=act, issued_by=ui) -> accepted -> started -> completed/failed
    - Git 利用可能なら commit + tag
    - ログ: data/pdca_logs/veritas_orders/adoptions.csv
    """
    # 1) act_service 準備
    try:
        from src.core.act_service import adopt_strategy  # lazy import
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"act_service unavailable: {e}")

    # 2) Decision ledger 連携
    decision_id = body.decision_id
    try:
        from src.core.decision_registry import create_decision, append_event  # type: ignore
        if not decision_id:
            d = create_decision(
                kind="act",
                issued_by="ui",
                intent={"strategy": body.strategy, "reason": body.reason},
                policy_snapshot=_get_policy_snapshot(),
            )
            decision_id = d.decision_id
        append_event(decision_id, "accepted", {"endpoint": "/pdca-dashboard/act"})
        append_event(decision_id, "started", {"strategy": body.strategy, "dry_run": body.dry_run})
        _use_ledger = True
    except Exception:
        # 台帳モジュールが無くても採用処理は継続
        _use_ledger = False

    # 3) 採用処理
    try:
        res = adopt_strategy(
            body.strategy,
            reason=body.reason or "",
            decision_id=decision_id,
            dry_run=body.dry_run,
        )
        status = 200 if res.ok else 400

        # 完了イベント
        if _use_ledger:
            try:
                from src.core.decision_registry import append_event  # re-import safe
                phase = "completed" if res.ok else "failed"
                append_event(decision_id or "-", phase, {
                    "committed": res.committed,
                    "git_tag": res.tag,
                    "output_path": str(res.output_path) if res.output_path else None,
                    "message": res.message,
                })
            except Exception:
                pass

        return JSONResponse(
            status_code=status,
            content={
                "ok": res.ok,
                "message": res.message,
                "strategy": res.strategy,
                "committed": res.committed,
                "git_tag": res.tag,
                "output_path": str(res.output_path) if res.output_path else None,
                "details": res.details,
                "decision_id": decision_id,  # 応答に含める
            },
        )
    except Exception as e:
        # 異常時も台帳へ failed を記録
        if _use_ledger:
            try:
                from src.core.decision_registry import append_event
                append_event(decision_id or "-", "failed", {"error": str(e)})
            except Exception:
                pass
        raise
