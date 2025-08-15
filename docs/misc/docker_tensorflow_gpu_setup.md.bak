
# DockerでTensorFlow GPU環境をセットアップする手順書

## 1. ホスト環境の前提条件

- NVIDIA GPU（ドライバインストール済）
- NVIDIA Docker（nvidia-container-toolkit）インストール済
- Dockerが動作していること

## 2. Docker イメージを使用して TensorFlow GPU をセットアップする手順

### 2-1. NVIDIA Docker ランタイムの確認

```bash
docker info | grep -i runtime
```

`nvidia` が含まれていることを確認する。

### 2-2. CUDA・cuDNN対応の TensorFlow GPU イメージで動作確認

以下のコマンドで、ホストGPUをDockerコンテナ内で認識できるか確認する。

```bash
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

GPU情報が表示されれば成功。

### 2-3. TensorFlow GPUコンテナの起動・確認

```bash
docker run --rm --gpus all tensorflow/tensorflow:2.15.0-gpu python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

コンテナ内で `['/physical_device:GPU:0']` などが表示されればGPUが認識されている。

### 2-4. TensorFlow GPUコンテナの対話的なシェル起動（必要に応じて）

```bash
docker run --gpus all -it --rm tensorflow/tensorflow:2.15.0-gpu /bin/bash
```

コンテナ内で以下を実行して確認する。

```bash
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

## 3. その他の注意点

- WSL上での直接インストールは依存関係が複雑になるため、今後はDocker利用を推奨。
- TensorFlowのバージョンアップに応じてDockerイメージも更新可能。
- Dockerfileによるカスタム環境構築も可能（例: cuDNNバージョン固定など）。

---

以上を手順書としてまとめておきます。ご自由に活用ください！
<!-- AUTODOC:BEGIN mode=git_log path_globs=docs/misc/*.md title="Misc 文書更新履歴（最近30）" limit=30 since=2025-08-01 -->
### Misc 文書更新履歴（最近30）

_変更は見つかりませんでした。_
<!-- AUTODOC:END -->
