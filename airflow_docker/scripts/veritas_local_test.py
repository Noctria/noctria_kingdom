#!/usr/bin/env python3
# coding: utf-8

"""
Veritas Local Test Script
📍 Soroban上でモデルが正しく動作するか確認するためのローカル実行用スクリプト
"""

import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# ✅ モデルディレクトリ（環境変数またはデフォルト）
MODEL_DIR = os.getenv("MODEL_DIR", "/noctria_kingdom/airflow_docker/models/nous-hermes-2")

# ✅ プロンプト（必要に応じてカスタマイズ）
PROMPT = "USDJPYについて、来週のFX戦略を日本語で5つ提案してください。"

def generate_fx_strategy(prompt: str) -> str:
    if not os.path.exists(MODEL_DIR):
        raise FileNotFoundError(f"❌ モデルディレクトリが存在しません: {MODEL_DIR}")

    print(f"📦 モデル読み込み中: {MODEL_DIR}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, local_files_only=True)

    inputs = tokenizer(prompt, return_tensors="pt").to("cuda" if torch.cuda.is_available() else "cpu")
    model.to(inputs["input_ids"].device)

    print("🧠 推論中...")
    with torch.no_grad():
        outputs = model.generate(inputs["input_ids"], max_new_tokens=300)

    result = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return result


if __name__ == "__main__":
    print("👑 Veritas Local Test: モデルが正常に動作するか確認します。")
    try:
        response = generate_fx_strategy(PROMPT)
        print("✅ モデル応答:")
        print("=" * 50)
        print(response)
        print("=" * 50)
    except Exception as e:
        print(f"🚨 エラーが発生しました: {e}")
