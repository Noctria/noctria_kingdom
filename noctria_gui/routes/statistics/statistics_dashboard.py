# [NOCTRIA_CORE_REQUIRED]
#!/usr/bin/env python3
# coding: utf-8

"""
📊 /statistics - 戦略統計関連の全URLを処理する統合ルーター
- HUDダッシュボード表示 (/dashboard)
- フィルタ・ソート機能
- CSVエクスポート機能 (/export)
- 戦略比較機能 (/strategy_compare)
- 予測可視化: forecast.json をダッシュボードに同梱（/forecast/raw で生JSONも提供）
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, TOOLS_DIR
from noctria_gui.services import statistics_service

# プレフィックスは外部で付与される想定
router = APIRouter(tags=["Statistics"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# 予測JSONの既定パス（環境変数で上書き可）
FORECAST_JSON_PATH = Path(os.getenv("NOCTRIA_FORECAST_JSON", "data/oracle/forecast.json")).resolve()


def _load_forecast_json() -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    forecast.json を読み込み、(data, meta) を返す。
    data は dict または None。meta は path/mtime/warning を含む。
    """
    meta: Dict[str, Any] = {"path": str(FORECAST_JSON_PATH), "mtime": None, "warning": None}
    if not FORECAST_JSON_PATH.exists():
        meta["warning"] = "forecast.json が見つかりません。PrometheusOracle 実行後に生成されます。"
        return None, meta

    try:
        mtime = datetime.fromtimestamp(FORECAST_JSON_PATH.stat().st_mtime)
        meta["mtime"] = mtime.isoformat(timespec="seconds")
        with FORECAST_JSON_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # 最小限の正当性点検（必須ではないが、壊れたJSONの早期検知）
        if not isinstance(data, dict):
            meta["warning"] = "forecast.json の形式が想定外です（dict ではありません）。"
        return data if isinstance(data, dict) else None, meta
    except Exception as e:
        logging.warning(f"Failed to load forecast.json: {e}", exc_info=True)
        meta["warning"] = f"forecast.json の読み込みに失敗: {e}"
        return None, meta


@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
async def show_statistics_dashboard(request: Request):
    """
    📈 HUDスタイル統計ダッシュボードと戦略一覧を表示（フィルタ付き）
    追加: forecast.json を読み込み、テンプレに 'forecast' / 'forecast_meta' として渡す。
    """
    strategy = request.query_params.get("strategy", "").strip() or None
    symbol = request.query_params.get("symbol", "").strip() or None
    start_date = request.query_params.get("start_date", "").strip() or None
    end_date = request.query_params.get("end_date", "").strip() or None

    try:
        # サービスからデータを取得
        all_logs = statistics_service.load_all_logs()
        stats = statistics_service.get_strategy_statistics()

        # フィルタリングとソート
        filtered_logs = statistics_service.filter_logs(
            logs=all_logs,
            strategy=strategy,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )
        sorted_logs = statistics_service.sort_logs(
            logs=filtered_logs, sort_key="win_rate", descending=True
        )

        # 予測の読み込み（無くても落とさない）
        forecast, forecast_meta = _load_forecast_json()

    except Exception as e:
        logging.error(f"Failed to process statistics data: {e}", exc_info=True)
        # エラー発生時も最低限の表示ができるように空のデータを渡す
        return templates.TemplateResponse(
            "statistics_dashboard.html",
            {
                "request": request,
                "stats": {},
                "statistics": [],
                "strategies": [],
                "symbols": [],
                "filters": {},
                "forecast": None,
                "forecast_meta": {
                    "path": str(FORECAST_JSON_PATH),
                    "mtime": None,
                    "warning": str(e),
                },
                "error": "統計データの処理中にエラーが発生しました。",
            },
        )

    return templates.TemplateResponse(
        "statistics_dashboard.html",
        {
            "request": request,
            "stats": stats,
            "statistics": sorted_logs,
            "strategies": statistics_service.get_available_strategies(all_logs),
            "symbols": statistics_service.get_available_symbols(all_logs),
            "filters": {
                "strategy": strategy or "",
                "symbol": symbol or "",
                "start_date": start_date or "",
                "end_date": end_date or "",
            },
            # 追加: 予測（テンプレで任意に可視化可能）
            "forecast": forecast,  # 例: {"horizon":[...], "pred":[...], "conf_int":[...]} 等の想定
            "forecast_meta": forecast_meta,  # {"path": "...", "mtime": "...", "warning": "..."}
        },
    )


@router.get("/forecast/raw", response_class=JSONResponse)
async def get_forecast_raw():
    """
    🌤 予測JSONの生データを返す API（ダッシュボード未対応でも確認できるように）
    """
    data, meta = _load_forecast_json()
    if data is None:
        # ファイルが無い/壊れている
        return JSONResponse({"ok": False, "data": None, "meta": meta}, status_code=404)
    return JSONResponse({"ok": True, "data": data, "meta": meta})


@router.get("/export")
async def export_statistics_csv():
    """
    📤 統計スコア一覧をCSVでエクスポート
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = TOOLS_DIR / f"strategy_statistics_{timestamp}.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)  # 追加: 出力先を自動作成

    try:
        logs = statistics_service.load_all_logs()
        if not logs:
            raise ValueError("出力する統計ログが存在しません。")
        statistics_service.export_statistics_to_csv(logs, output_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSVエクスポートに失敗しました: {e}")

    return FileResponse(path=output_path, filename=output_path.name, media_type="text/csv")


@router.get("/strategy_compare", response_class=HTMLResponse)
async def strategy_compare(request: Request):
    """
    ⚔️ 戦略比較ダッシュボードを表示
    """
    strategy_1 = request.query_params.get("strategy_1", "").strip() or None
    strategy_2 = request.query_params.get("strategy_2", "").strip() or None

    # 利用可能な戦略リストを取得してテンプレートに渡す
    all_logs = statistics_service.load_all_logs()
    available_strategies = statistics_service.get_available_strategies(all_logs)

    context: Dict[str, Any] = {
        "request": request,
        "strategies": available_strategies,
        "strategy_1": strategy_1,
        "strategy_2": strategy_2,
    }

    if strategy_1 and strategy_2:
        if strategy_1 == strategy_2:
            context["error"] = "異なる戦略を選択してください。"
        else:
            try:
                comparison_results = statistics_service.compare_strategies(
                    all_logs, strategy_1, strategy_2
                )
                context["comparison_results"] = comparison_results
            except Exception as e:
                context["error"] = f"戦略比較の処理中にエラーが発生しました: {e}"

    return templates.TemplateResponse("strategy_compare.html", context)
