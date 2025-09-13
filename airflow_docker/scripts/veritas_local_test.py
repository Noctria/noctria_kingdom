#!/usr/bin/env python3
# coding: utf-8

"""
Veritas Local Test Script
📍 Soroban上でモデルが正しく動作するか確認するためのローカル実行用スクリプト

改訂点:
- torch がインストールされていない場合は「スキップ」として exit(0) で終了
- GPU が無い環境でも安全に実行できるように改善
"""

import os
import sys

# --- torch import を安全化 ---------------------------------------------------
try:
    import torch
except ImportError:
    print("⚠️ PyTorch が見つからないため、重テストをスキップします。")
    sys.exit(0)

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

    device = "cuda" if torch.cuda.is_available() else "cpu"
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    model.to(device)

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
    except SystemExit as e:
        # torch が無くてスキップ終了した場合も正常終了扱い
        if e.code == 0:
            pass
        else:
            print(f"🚨 システム終了コード: {e.code}")
            sys.exit(e.code)
    except Exception as e:
        print(f"🚨 エラーが発生しました: {e}")
        sys.exit(1)
