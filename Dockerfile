# ベースイメージとして先に作成した my_temp_image を利用
FROM my_temp_image:latest

# 環境変数設定
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8

# 必要な引数
ARG PYTHON_VERSION=python3.11
ARG TENSORFLOW_PACKAGE=tensorflow-cpu==2.15.0

# 各種セットアップスクリプトのコピー
COPY setup.sources.sh /setup.sources.sh
COPY setup.packages.sh /setup.packages.sh
COPY cpu.packages.txt /cpu.packages.txt
COPY setup.python.sh /setup.python.sh
COPY cpu.requirements.txt /cpu.requirements.txt
COPY bashrc /etc/bash.bashrc

# システムパッケージのインストール
RUN /setup.sources.sh && \
    /setup.packages.sh /cpu.packages.txt

# Python環境セットアップと必要パッケージのインストール
RUN /setup.python.sh $PYTHON_VERSION /cpu.requirements.txt && \
    pip install --no-cache-dir ${TENSORFLOW_PACKAGE}

# bashrc 権限調整
RUN chmod a+rwx /etc/bash.bashrc

# デフォルトで bash を起動
CMD ["/bin/bash"]
