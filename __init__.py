# プロジェクトルート /mnt/d/noctria_kingdom で
touch src/strategies/__init__.py
touch src/strategies/veritas_generated/__init__.py

# そのシェルだけPYTHONPATHを通す（モジュール実行用）
export PYTHONPATH="$PWD/src:$PYTHONPATH"

# 単体実行テスト（さっきのダミー最小構成が入っている前提）
python -m strategies.veritas_generated.Aurus_Singularis
