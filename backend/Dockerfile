FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（gcc 用于部分依赖编译，curl 用于 healthcheck，bash 用于一键升级）
#
# 关于 docker-compose-plugin：
#   新安装 Debian/Ubuntu/Docker 时，docker CLI 自带 `docker compose` 子命令；
#   若使用的发行版仓库里没有 docker-compose-plugin 包也没关系，
#   我们会优先使用宿主机上通过 /var/run/docker.sock 暴露的 docker compose，
#   容器内 apt 的 docker-compose-plugin 仅为兜底，缺失不影响主要功能。
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev curl bash docker.io \
    && ( apt-get install -y --no-install-recommends docker-compose-plugin || true ) \
    && rm -rf /var/lib/apt/lists/*

# 先安装 Python 依赖，利用缓存层
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY backend/app/ ./app/
# 复制项目根 scripts（用于容器内也能直接执行升级脚本）
COPY scripts/ ./scripts/
# 复制 docker-compose 模板（升级时可使用 compose 工具）
COPY docker-compose.yml ./docker-compose.yml

# 确保数据与日志目录存在，以及 /host（可选：绑宿主机项目根，便于真正的宿主机 docker compose 执行）存在
RUN mkdir -p /app/data /app/logs /host

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
