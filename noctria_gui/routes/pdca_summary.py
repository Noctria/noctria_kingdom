#!/usr/bin/env python3
# coding: utf-8

"""
📊 PDCA Summary Route (v2.0)
- PDCA再評価の統計サマリ画面
- 再評価結果ログを集計し、改善率や採用数を表示
"""

import logging
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from typing import Optional

# --- 王国の基盤モジュールをインポート ---
# ✅ 修正: path_config.pyのリファクタリングに合わせて、正しい変数名をインポート
from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, PDCA_LOG_DIR
from src.core.pdca_log_parser import load_and_aggregate_pdca_logs

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

router = APIRouter(prefix="/pdca", tags=["pdca-summary"])
# ✅ 修正: 正しい変数名を使用
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

@router.get("/summary", response_class=HTMLResponse)
async def show_pdca_summary(
    request: Request,
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    mode: str = Query(default="strategy"),
    limit: int = Query(default=20)
):
    """
    GET /pdca/summary - PDCAサイクルの結果を分析し、サマリー画面を表示する
    """
    logging.info(f"PDCAサマリーの閲覧要求を受理しました。モード: {mode}, 期間: {from_date} ~ {to_date}")

    # 🔍 日付フィルター用のdatetimeオブジェクトに変換
    from_dt, to_dt = None, None
    try:
        if from_date: from_dt = datetime.fromisoformat(from_date)
        if to_date: to_dt = datetime.fromisoformat(to_date)
    except ValueError as e:
        logging.warning(f"不正な日付形式が指定されました: {e}")
        # 不正な場合は無視して全期間を対象とする

    # 📥 ログファイルを読み込んで統計を生成
    try:
        result = load_and_aggregate_pdca_logs(
            log_dir=PDCA_LOG_DIR,
            mode=mode,
            limit=limit,
            from_date=from_dt,
            to_date=to_dt
        )
        logging.info("PDCAログの集計が完了しました。")
    except Exception as e:
        logging.error(f"PDCAログの集計中にエラーが発生しました: {e}", exc_info=True)
        # エラー発生時は、テンプレートが壊れないように空のデータを渡す
        result = {
            "stats": {},
            "chart": {"labels": [], "data": [], "dd_data": []}
        }

    # 📤 テンプレートへ渡す
    context = {
        "request": request,
        "summary": result.get("stats", {}),
        "chart": result.get("chart", {}),
        "filter": {
            "from": from_date,
            "to": to_date
        },
        "mode": mode,
        "limit": limit,
        # ✅ 修正: フラッシュメッセージ用のキーを追加（エラーがない場合はNone）
        "recheck_success": None,
        "recheck_fail": None,
    }
    return templates.TemplateResponse("pdca_summary.html", context)

