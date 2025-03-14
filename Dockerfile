# 使用Python 3.8作为基础镜像
FROM python:3.8-slim

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY requirements.txt .
COPY src/ ./src/
COPY data/ ./data/
COPY smart-trade.py .

# 安装依赖
RUN pip install -r requirements.txt

# 设置环境变量
ENV PYTHONPATH=/app

# 暴露Streamlit默认端口
EXPOSE 8501

# 启动应用
CMD ["streamlit", "run", "smart-trade.py", "--server.port=8501", "--server.address=0.0.0.0"]