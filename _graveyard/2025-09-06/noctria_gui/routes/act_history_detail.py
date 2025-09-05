#!/usr/bin/env python3
# coding: utf-8

"""
📄 Veritas Adoption Log Detail Route (v2.0)
- 特定の戦略採用ログの詳細情報を表示する
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# --- 王国の基盤モジュールをインポート ---
# ✅ 修正: path_config.pyのリファクタリングに合わせて、正しいパスと変数名をインポート
from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR
from noctria_gui.services import act_log_service

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

# ✅ 修正: ルーターのprefixを/act-historyに統一
router = APIRouter(prefix="/act-history", tags=["act-history-detail"])
# ✅ 修正: 正しい変数名を使用
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


# ✅ 修正: URLをよりRESTfulな形式に変更 (/detail?strategy_name=... -> /detail/{log_id})
@router.get("/detail/{log_id}", response_class=HTMLResponse)
async def show_act_history_detail(request: Request, log_id: str):
    """
    📜 指定されたIDの採用ログ詳細を表示する
    """
    logging.info(f"採用ログ詳細の閲覧要求を受理しました。対象ID: {log_id}")
    try:
        # サービス層を通じて、IDでログを取得
        log = act_log_service.get_log_by_id(log_id)
        
        if not log:
            logging.warning(f"指定された採用ログが見つかりませんでした: {log_id}")
            raise HTTPException(status_code=404, detail=f"ID '{log_id}' の採用記録は見つかりませんでした。")

        # テンプレートに渡す前にデータを正規化
        normalized_log = act_log_service.normalize_score(log)
        
        return templates.TemplateResponse("act_history_detail.html", {
            "request": request,
            "log": normalized_log
        })

    except HTTPException:
        # 404エラーはそのまま再送出
        raise
    except Exception as e:
        logging.error(f"ログ詳細の取得中に予期せぬエラーが発生しました: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="ログ詳細の表示中に内部エラーが発生しました。")

