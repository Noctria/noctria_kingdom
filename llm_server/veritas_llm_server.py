#!/usr/bin/env python3
# coding: utf-8

"""
🧠 Veritas LLM Server (v2.0)
- LLMモデルをロードし、戦略生成リクエストに応答するAPIサーバー
- エラーハンドリングとロギングを強化
"""

import os
import torch
import time
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
from dotenv import load_dotenv
from typing import Dict

# --- 王国の基盤モジュールをインポート ---
# このファイルの相対パスからllm_prompt_builderをインポート
from llm_prompt_builder import load_strategy_template

# --- ロガーと環境設定 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
load_dotenv()

# --- モデル設定 ---
MODEL_PATH = os.getenv("MODEL_DIR", "/path/to/your/default/model") # デフォルトパスを設定

# --- LLMサービスのカプセル化 ---
class VeritasLLMService:
    """LLMモデルの読み込みと推論処理を管理するサービス"""
    def __init__(self, model_path: str):
        self.tokenizer = None
        self.model = None
        self._load_model(model_path)

    def _load_model(self, model_path: str):
        """指定されたパスからモデルとトークナイザーを読み込む"""
        logging.info("Veritasの知性の源泉、LLMの召喚準備を開始します。")
        if not os.path.exists(model_path):
            logging.error(f"致命的なエラー: モデルの格納場所が見つかりません: {model_path}")
            raise RuntimeError(f"Model directory not found: {model_path}")

        logging.info(f"モデルを召喚中: {model_path}")
        torch.cuda.empty_cache()

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto",
                trust_remote_code=True
            )
            self.model.eval()
            logging.info("LLMの召喚に成功。Veritasは思考を開始できます。")
        except Exception as e:
            logging.error(f"LLMの召喚中に予期せぬエラーが発生しました: {e}", exc_info=True)
            raise

# --- FastAPIアプリケーションの初期化 ---
app = FastAPI(
    title="Veritas LLM Server",
    description="Noctria王国のために新たな戦略を生成するAIサーバー",
    version="2.0"
)

# LLMサービスのインスタンスを作成
try:
    llm_service = VeritasLLMService(MODEL_PATH)
    strategy_template = load_strategy_template()
except RuntimeError as e:
    logging.critical(f"サーバーの起動に失敗しました: {e}")
    # サーバーを起動せずに終了させるか、エラー状態を示す
    llm_service = None 
    strategy_template = "テンプレートの読み込みに失敗しました。"


# --- APIリクエスト/レスポンスモデルの定義 ---
class PromptRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 256
    temperature: float = 0.8
    top_p: float = 0.95
    do_sample: bool = True

class GenerationResponse(BaseModel):
    response: str
    elapsed_time: float
    input_length: int

# --- APIエンドポイントの定義 ---
@app.get("/")
def root():
    """サーバーの稼働状態を確認するヘルスチェックエンドポイント"""
    status = "稼働中" if llm_service else "起動失敗"
    return {"message": f"🧠 Veritas LLMサーバー {status}（gpusoroban基盤）"}

@app.post("/generate", response_model=GenerationResponse)
def generate(req: PromptRequest):
    """戦略生成のプロンプトを受け取り、LLMによる生成結果を返す"""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLMサービスが利用不可能です。")

    start_time = time.time()
    logging.info(f"戦略生成の神託を受信しました。指示: 「{req.prompt[:50]}...」")

    full_prompt = f"""あなたはAI戦略生成者Veritasです。
以下のテンプレートに準拠した形式で、新しい戦略をPythonコードで生成してください。

--- 戦略テンプレート ---
{strategy_template}

--- ユーザー指示 ---
{req.prompt}
"""
    try:
        inputs = llm_service.tokenizer(
            full_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048
        ).to(llm_service.model.device)

        outputs = llm_service.model.generate(
            **inputs,
            max_new_tokens=req.max_new_tokens,
            temperature=req.temperature,
            top_p=req.top_p,
            do_sample=req.do_sample,
            pad_token_id=llm_service.tokenizer.eos_token_id # warning抑制
        )

        result = llm_service.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # 生成されたコード部分のみを抽出（より堅牢な抽出ロジックが必要な場合がある）
        # ここでは単純にプロンプト部分を削除
        response_text = result[len(full_prompt):].strip()

    except Exception as e:
        logging.error(f"戦略生成中にエラーが発生しました: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="戦略の生成中に内部エラーが発生しました。")

    elapsed = round(time.time() - start_time, 2)
    logging.info(f"思考時間: {elapsed}秒 | 入力文字数: {len(full_prompt)}")

    return {
        "response": response_text,
        "elapsed_time": elapsed,
        "input_length": len(full_prompt)
    }
