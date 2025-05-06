# 使用Python 3.8作为基础镜像
FROM python:3.8-slim

# 配置apt国内源
RUN echo "deb https://mirrors.aliyun.com/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.aliyun.com/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.aliyun.com/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    pkg-config \
    libhdf5-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY requirements.txt .
COPY src/ ./src/
COPY data/ ./data/
COPY smart-trade.py .

# 配置pip镜像源并安装依赖
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install -r requirements.txt

# 设置环境变量
ENV PYTHONPATH=/app

# 暴露Streamlit默认端口
EXPOSE 8501

# 启动应用
CMD ["streamlit", "run", "smart-trade.py", "--server.port=8501", "--server.address=0.0.0.0"]