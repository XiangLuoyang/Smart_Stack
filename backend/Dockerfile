# Smart Stack 后端镜像:FastAPI + uvicorn
# 容器内目录布局与宿主机保持一致,以便 config.py 的 parents[3] 解析正确:
#   /app/backend/        <- 应用代码
#   /app/data/           <- SQLite + 自选列表(挂载卷持久化)
FROM python:3.12-slim AS base

# 国内镜像加速(可选,网络好可删)
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 系统依赖:TA-Lib C 库 + 编译工具
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget build-essential ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN cd /tmp \
    && wget -q http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz \
    && tar -xzf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib \
    && ./configure --prefix=/usr/local \
    && make -j"$(nproc)" \
    && make install \
    && ldconfig \
    && cd / && rm -rf /tmp/ta-lib*

ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

WORKDIR /app/backend

# 先装依赖(利用 Docker 层缓存)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝应用代码
COPY backend/ ./

# 复用项目根的 legacy 分析模块(signal_service 会 import src.models.prediction,
# llm_bridge 会 import src.llm_analysis;两处都有 try/except 优雅降级)。
COPY src/ /app/src/

# 可选:启用 LSTM 信号(默认关闭以保持镜像精简;取消注释即开启)。
# 缺省状态下 LSTM 信号降级为统计方法,LLM 报告照常工作。
# RUN pip install --no-cache-dir tensorflow

ENV PYTHONPATH=/app/backend:/app \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

# 生产模式:关闭 --reload,监听所有网卡
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
