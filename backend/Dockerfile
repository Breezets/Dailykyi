FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（gcc 用于部分依赖编译，curl 用于 healthcheck）
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# 先安装 Python 依赖，利用缓存层
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/

# 确保数据与日志目录存在
RUN mkdir -p /app/data /app/logs

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
