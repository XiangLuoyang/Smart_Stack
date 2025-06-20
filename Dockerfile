# 使用Miniconda3作为基础镜像
FROM continuumio/miniconda3:latest

# 配置apt国内源 (借鉴自 Dockerfile.ta-test)
RUN echo "deb https://mirrors.aliyun.com/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.aliyun.com/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# 安装系统依赖 (补充了 ca-certificates, automake, libtool)
RUN apt-get update && apt-get install -y \
    wget \
    pkg-config \
    libhdf5-dev \
    build-essential \
    hdf5-tools \
    curl \
    ca-certificates \
    automake \
    libtool \
    && rm -rf /var/lib/apt/lists/*

# 配置conda国内源
RUN conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/ && \
    conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/ && \
    conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/ && \
    conda config --set show_channel_urls yes

# 创建并激活Python环境
RUN conda create -n smart_stack python=3.10 -y && \
    conda init bash && \
    echo "conda activate smart_stack" >> ~/.bashrc

# 安装 Mamba 到 base 环境以加速后续的包安装
RUN conda install -n base -c conda-forge mamba -y

# 设置工作目录
WORKDIR /app

# 安装TA-Lib C库
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    # 更新config.guess和config.sub以支持ARM64架构
    mkdir -p config && \
    cd config && \
    wget http://git.savannah.gnu.org/cgit/config.git/plain/config.guess && \
    wget http://git.savannah.gnu.org/cgit/config.git/plain/config.sub && \
    cd .. && \
    chmod +x config/config.guess config/config.sub && \
    cp config/config.guess . && \
    cp config/config.sub . && \
    ./configure --prefix=/usr/local && \
    make && \
    make install && \
    ldconfig && \
    # 添加 ldconfig 命令
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# 设置TA-Lib环境变量
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
ENV PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
ENV CFLAGS="-I/usr/local/include"
ENV LDFLAGS="-L/usr/local/lib"

# 复制项目文件
COPY requirements.txt .
COPY src/ ./src/
COPY data/ ./data/
COPY smart-trade.py .
COPY envconf .

# 使用conda安装主要依赖
SHELL ["/bin/bash", "-c"]

# 配置 pip 国内源 (例如清华大学源)
RUN source /opt/conda/etc/profile.d/conda.sh && \
    conda activate smart_stack && \
    pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

RUN source /opt/conda/etc/profile.d/conda.sh && \
    conda activate smart_stack && \
    mamba install -c conda-forge -y pandas numpy scipy matplotlib seaborn pytz requests

RUN source /opt/conda/etc/profile.d/conda.sh && \
    conda activate smart_stack && \
    mamba install -c anaconda -y tensorflow

RUN source /opt/conda/etc/profile.d/conda.sh && \
    conda activate smart_stack && \
    mamba install -c conda-forge -y scikit-learn plotly ta-lib

RUN source /opt/conda/etc/profile.d/conda.sh && \
    conda activate smart_stack && \
    pip install --no-cache-dir -r requirements.txt

# 设置环境变量
ENV PYTHONPATH=/app

# 暴露Streamlit默认端口
EXPOSE 8501

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8501 || exit 1

# 启动应用
CMD ["/bin/bash", "-c", "source /opt/conda/etc/profile.d/conda.sh && conda activate smart_stack && streamlit run smart-trade.py --server.port=8501 --server.address=0.0.0.0"]